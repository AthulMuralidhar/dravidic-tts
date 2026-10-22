"""Serve saved audio and live progress without touching the speech worker."""

from __future__ import annotations

import argparse
import io
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def batch_progress(directory: Path) -> dict[str, Any]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for part in manifest["parts"]:
        part["chunks_done"] = 0
        part["chunks_total"] = None
        stem = Path(part["audio_url"]).stem
        plans = sorted(
            (directory / "audio-chunks" / stem).glob("*/plan.json"),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for path in plans:
            plan = json.loads(path.read_text(encoding="utf-8"))
            if (
                plan.get("voice") != manifest["voice"]
                or plan.get("speed") != manifest["speed"]
            ):
                continue
            total = len(plan["segments"])
            part["chunks_total"] = total
            part["chunks_done"] = sum(
                (path.parent / f"chunk-{index:04d}.wav").is_file()
                for index in range(1, total + 1)
            )
            break
    return manifest


class AudioHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir() and not urlsplit(self.path).path.endswith("/"):
            return super().send_head()
        directory = path if path.is_dir() else path.parent
        root = Path(self.directory).resolve()
        if not directory.resolve().is_relative_to(root):
            self.send_error(403)
            return None
        manifest = directory / "manifest.json"
        if manifest.is_file():
            try:
                if path.name == "progress.json":
                    content = json.dumps(batch_progress(directory)).encode("utf-8")
                    return self._response(content, "application/json")
                if path.is_dir() or path.name == "index.html":
                    content = Path(__file__).with_name("pdf-listening.html").read_bytes()
                    return self._response(content, "text/html; charset=utf-8")
            except (OSError, ValueError, KeyError):
                self.send_error(503, "Progress temporarily unavailable")
                return None
        return super().send_head()

    def _response(self, content: bytes, content_type: str) -> io.BytesIO:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return io.BytesIO(content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="outputs")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    handler = partial(AudioHandler, directory=args.directory)
    with ThreadingHTTPServer(("0.0.0.0", args.port), handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
