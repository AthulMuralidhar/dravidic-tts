import json
from pathlib import Path

import pytest

from dravidic_tts import pdf_batch


def test_batch_uses_a_fresh_process_per_part_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DRAVIDIC_TTS_PROVIDER", "tone")
    source = tmp_path / "book.pdf"
    source.write_bytes(b"stub PDF: extraction is supplied by this test")
    pages = [(1, "Hello world. " * 20), (2, "Good morning. " * 18)]
    monkeypatch.setattr(
        pdf_batch, "extract_pages",
        lambda *a, **kw: (pages, {"cached": 2}),
    )
    args = pdf_batch.build_parser().parse_args([
        str(source), "--output-root", str(tmp_path / "outputs"),
        "--language", "en", "--voice", "en-mary", "--part-characters", "300",
    ])
    output = pdf_batch.run_batch(args)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert len(manifest["parts"]) == 2
    pids = [part["memory_kib"]["pid"] for part in manifest["parts"]]
    assert pids[0] != pids[1]
    assert all(part["status"] == "completed" for part in manifest["parts"])
    assert list((output / "audio-chunks").rglob("chunk-*.wav"))

    def must_not_generate(*args, **kwargs):
        raise AssertionError("Completed parts must not be synthesized again")

    monkeypatch.setattr(pdf_batch, "_run_inference_process", must_not_generate)
    assert pdf_batch.run_batch(args) == output


def test_killed_child_retries_with_checkpoints_and_bounds_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = pdf_batch.BatchPart(1, 1, 1, "Hello.")
    record = {"text_url": "text/one.txt", "audio_url": "audio/one.wav"}
    manifest = {"status": "generating", "parts": [record]}
    args = pdf_batch.build_parser().parse_args(["unused.pdf", "--force"])
    attempts = []

    def killed(request_path, progress):
        request = json.loads(request_path.read_text())
        attempts.append(request["reuse_checkpoints"])
        raise RuntimeError("Inference process exited with code -9")

    monkeypatch.setattr(pdf_batch, "_run_inference_process", killed)
    monkeypatch.setattr(pdf_batch, "_save_manifest", lambda *a: None)
    monkeypatch.setattr(pdf_batch.time, "sleep", lambda *a: None)
    with pytest.raises(RuntimeError, match="-9"):
        pdf_batch._generate_isolated_part(
            part, record, tmp_path, manifest, args, "tone"
        )
    assert attempts == [False, True, True]
    assert record["status"] == "failed"
    assert manifest["status"] == "failed"
    assert record["attempt"] == 3


def test_recovered_child_publishes_result_after_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    part = pdf_batch.BatchPart(1, 1, 1, "Hello.")
    record = {"text_url": "text/one.txt", "audio_url": "audio/one.wav"}
    manifest = {"status": "generating", "parts": [record]}
    args = pdf_batch.build_parser().parse_args(["unused.pdf"])
    calls = []

    def retry_then_recover(request_path, progress):
        request = json.loads(request_path.read_text())
        calls.append(request)
        if len(calls) == 1:
            raise RuntimeError("Inference process exited with code -9")
        progress({"chunks_done": 1, "chunks_total": 1, "memory_kib": {"pid": 123}})
        return {"segments": 1, "duration_seconds": 0.5}

    monkeypatch.setattr(pdf_batch, "_run_inference_process", retry_then_recover)
    monkeypatch.setattr(pdf_batch, "_save_manifest", lambda *a: None)
    monkeypatch.setattr(pdf_batch.time, "sleep", lambda *a: None)
    pdf_batch._generate_isolated_part(part, record, tmp_path, manifest, args, "tone")
    assert len(calls) == 2
    assert "last_error" not in record
    assert record["segments"] == 1
    assert record["chunks_done"] == 1
