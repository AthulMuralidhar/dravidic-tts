"""Restart-safe PDF OCR and long-form speech batch generation."""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import subprocess
import tempfile
import unicodedata
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dravidic_tts.config import Settings
from dravidic_tts.language import TextSegment, chunk_segments
from dravidic_tts.providers.factory import create_provider
from dravidic_tts.service import SpeechService
from dravidic_tts.text import review_text

_REMOVABLE_LINE = re.compile(
    r"(?:kambistories\.com|kambikuttan\.net|malayalam\s+kambi\s+kathakal|"
    r"nishayude\s+ponnumon|author\s*:)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class BatchPart:
    index: int
    page_start: int
    page_end: int
    text: str

    @property
    def stem(self) -> str:
        return (
            f"part-{self.index:04d}-pages-"
            f"{self.page_start:03d}-{self.page_end:03d}"
        )


def embedded_text_needs_ocr(text: str) -> bool:
    """Detect empty or badly mapped PDF text that must be recovered by OCR."""

    if len(text.strip()) < 40:
        return True
    broken = sum(
        text.count(marker) for marker in ("\x00", "\ufffd", "\ufffe", "\uffff")
    )
    return broken / max(len(text), 1) > 0.001


def clean_page_text(text: str) -> str:
    """Remove known repeated furniture and normalize OCR output for speech."""

    text = unicodedata.normalize("NFC", text.replace("\x00", " "))
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.isdigit() or _REMOVABLE_LINE.search(line):
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs).strip()


def build_parts(
    pages: list[tuple[int, str]],
    max_characters: int,
) -> list[BatchPart]:
    """Group page text into bounded, page-labelled macro audio parts."""

    if max_characters < 240:
        raise ValueError("part size must be at least 240 characters")

    grouped: list[tuple[list[int], list[str]]] = []
    current_pages: list[int] = []
    current_text: list[str] = []
    current_length = 0

    def flush() -> None:
        nonlocal current_pages, current_text, current_length
        if current_text:
            grouped.append((current_pages, current_text))
        current_pages = []
        current_text = []
        current_length = 0

    for page_number, page_text in pages:
        pieces = [
            item.text
            for item in chunk_segments(
                [TextSegment(page_text, "ml")],
                max_characters=max_characters,
            )
        ]
        for piece in pieces:
            separator_length = 2 if current_text else 0
            if current_text and (
                current_length + separator_length + len(piece) > max_characters
            ):
                flush()
            current_pages.append(page_number)
            current_text.append(piece)
            current_length += separator_length + len(piece)
    flush()

    return [
        BatchPart(
            index=index,
            page_start=min(page_numbers),
            page_end=max(page_numbers),
            text="\n\n".join(texts),
        )
        for index, (page_numbers, texts) in enumerate(grouped, start=1)
    ]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, path)


def _source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _slug(value: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return candidate or "document"


def _ocr_page(pdf: Any, page_index: int, dpi: int) -> str:
    page = pdf[page_index]
    bitmap = page.render(scale=dpi / 72)
    image = bitmap.to_pil().convert("L")
    document = io.BytesIO()
    image.save(document, format="PNG", optimize=True)
    try:
        result = subprocess.run(
            [
                "tesseract",
                "stdin",
                "stdout",
                "-l",
                "mal+eng",
                "--psm",
                "3",
            ],
            input=document.getvalue(),
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Tesseract is not installed in this runtime") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"Tesseract failed on page {page_index + 1}: {detail}"
        ) from exc
    return result.stdout.decode("utf-8", errors="replace")


def extract_pages(
    pdf_path: Path,
    pages_directory: Path,
    *,
    dpi: int = 300,
    max_pages: int | None = None,
    force: bool = False,
) -> tuple[list[tuple[int, str]], dict[str, int]]:
    """Extract usable page text, falling back to Malayalam/English OCR."""

    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf_path))
    total_pages = min(len(document), max_pages or len(document))
    pages: list[tuple[int, str]] = []
    methods = {"direct": 0, "ocr": 0, "cached": 0}

    for page_index in range(total_pages):
        page_number = page_index + 1
        page_path = pages_directory / f"page-{page_number:03d}.txt"
        if page_path.exists() and not force:
            cleaned = page_path.read_text(encoding="utf-8")
            methods["cached"] += 1
        else:
            page = document[page_index]
            text_page = page.get_textpage()
            extracted = text_page.get_text_range() or ""
            if embedded_text_needs_ocr(extracted):
                extracted = _ocr_page(document, page_index, dpi)
                methods["ocr"] += 1
            else:
                methods["direct"] += 1
            cleaned = review_text(clean_page_text(extracted)).repaired
            _atomic_write_text(page_path, cleaned)
        if cleaned.strip():
            pages.append((page_number, cleaned))
        print(
            f"Prepared page {page_number}/{total_pages} "
            f"({len(cleaned)} characters)",
            flush=True,
        )
    return pages, methods


def _wav_duration(audio: bytes) -> float:
    with wave.open(io.BytesIO(audio), "rb") as document:
        return document.getnframes() / document.getframerate()


def _part_record(part: BatchPart, output_directory: Path) -> dict[str, Any]:
    audio_path = output_directory / "audio" / f"{part.stem}.wav"
    text_path = output_directory / "text" / f"{part.stem}.txt"
    return {
        "index": part.index,
        "pages": [part.page_start, part.page_end],
        "characters": len(part.text),
        "text_url": f"text/{text_path.name}",
        "audio_url": f"audio/{audio_path.name}",
        "status": "completed" if audio_path.exists() else "pending",
    }


def write_listening_page(output_directory: Path, manifest: dict[str, Any]) -> None:
    """Write a refreshable, phone-friendly page for completed audio parts."""

    completed = sum(part["status"] == "completed" for part in manifest["parts"])
    title = html.escape(manifest["title"])
    cards: list[str] = []
    for part in manifest["parts"]:
        page_start, page_end = part["pages"]
        label = (
            f"Page {page_start}"
            if page_start == page_end
            else f"Pages {page_start}-{page_end}"
        )
        if part["status"] == "completed":
            audio_url = html.escape(part["audio_url"])
            player = (
                f'<audio controls preload="none" src="{audio_url}">'
                "Your browser does not support audio.</audio>"
            )
        else:
            player = '<p class="pending">Generating...</p>'
        cards.append(
            "<article>"
            f"<h2>Part {part['index']:04d} - {label}</h2>"
            f"{player}"
            f'<a href="{html.escape(part["text_url"])}">Read extracted text</a>'
            "</article>"
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>{title} - audio parts</title>
  <style>
    :root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
    body {{
      max-width: 760px; margin: auto; padding: 24px;
      background: #121712; color: #eef4e8;
    }}
    header, article {{
      background: #1d261d; border: 1px solid #3d4c3b;
      border-radius: 16px; padding: 18px; margin-bottom: 16px;
    }}
    h1, h2 {{ margin-top: 0; }} h2 {{ font-size: 1rem; }}
    audio {{ display: block; width: 100%; margin: 12px 0; }}
    a {{ color: #a9e58e; }} .pending {{ color: #efc76d; }}
  </style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <p>{completed} of {len(manifest['parts'])} audio parts ready.
    This page refreshes every minute.</p>
  </header>
  {''.join(cards)}
</body>
</html>
"""
    _atomic_write_text(output_directory / "index.html", document)


def _save_manifest(output_directory: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = _utc_now()
    _atomic_write_text(
        output_directory / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    write_listening_page(output_directory, manifest)


def run_batch(args: argparse.Namespace) -> Path:
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF was not found: {pdf_path}")

    output_directory = Path(args.output_root).resolve() / _slug(pdf_path.stem)
    output_directory.mkdir(parents=True, exist_ok=True)
    digest = _source_digest(pdf_path)
    manifest_path = output_directory / "manifest.json"
    if manifest_path.exists() and not args.force:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("source_sha256") != digest:
            raise RuntimeError(
                "Output directory belongs to a different PDF; use --force or "
                "choose another output root."
            )

    pages, extraction_methods = extract_pages(
        pdf_path,
        output_directory / "pages",
        dpi=args.dpi,
        max_pages=args.max_pages,
        force=args.force,
    )
    parts = build_parts(pages, args.part_characters)
    for part in parts:
        _atomic_write_text(
            output_directory / "text" / f"{part.stem}.txt",
            part.text,
        )

    manifest: dict[str, Any] = {
        "title": pdf_path.stem.replace("_", " "),
        "source_file": pdf_path.name,
        "source_sha256": digest,
        "status": "prepared" if args.prepare_only else "generating",
        "language": args.language,
        "voice": args.voice,
        "speed": args.speed,
        "page_count": len(pages),
        "part_count": len(parts),
        "part_characters": args.part_characters,
        "extraction_methods": extraction_methods,
        "parts": [_part_record(part, output_directory) for part in parts],
        "created_at": _utc_now(),
    }
    _save_manifest(output_directory, manifest)
    if args.prepare_only:
        print(f"Prepared batch at {output_directory}", flush=True)
        return output_directory

    settings = Settings.from_env()
    provider = create_provider(settings.provider)
    if not provider.ready:
        raise RuntimeError(f"Speech provider {provider.name!r} is not ready")
    service = SpeechService(provider)

    for part, record in zip(parts, manifest["parts"], strict=True):
        audio_path = output_directory / record["audio_url"]
        if audio_path.exists() and not args.force:
            record["status"] = "completed"
            print(f"Skipping completed {part.stem}", flush=True)
            continue
        record["status"] = "generating"
        _save_manifest(output_directory, manifest)
        print(
            f"Generating {part.stem} ({len(part.text)} characters)",
            flush=True,
        )
        result = service.synthesize(
            part.text,
            args.language,
            args.voice,
            args.speed,
            checkpoint_directory=output_directory / "audio-chunks" / part.stem,
            reuse_checkpoints=not args.force,
            progress_callback=lambda done, total, stem=part.stem: print(
                f"{stem}: neural chunk {done}/{total}", flush=True
            ),
        )
        _atomic_write_bytes(audio_path, result.audio)
        record["status"] = "completed"
        record["segments"] = result.segment_count
        record["duration_seconds"] = round(_wav_duration(result.audio), 3)
        _save_manifest(output_directory, manifest)

    manifest["status"] = "completed"
    _save_manifest(output_directory, manifest)
    print(f"Completed batch at {output_directory}", flush=True)
    return output_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OCR a PDF and generate resumable WAV parts."
    )
    parser.add_argument("pdf")
    parser.add_argument("--output-root", default="outputs/pdf")
    parser.add_argument(
        "--language", choices=("auto", "en", "ta", "ml"), default="ml"
    )
    parser.add_argument("--voice", default="ml-anjali")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--part-characters", type=int, default=4000)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    run_batch(build_parser().parse_args())


if __name__ == "__main__":
    main()
