import json
from pathlib import Path

from scripts.serve_audio import batch_progress


def test_progress_counts_saved_chunks_and_ignores_temporary_files(tmp_path: Path):
    manifest = {
        "voice": "ml-anjali", "speed": 1.0,
        "parts": [
            {"index": 1, "status": "completed", "audio_url": "audio/part-0001.wav"},
            {"index": 2, "status": "generating", "audio_url": "audio/part-0002.wav"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checkpoints = tmp_path / "audio-chunks" / "part-0002" / "fingerprint"
    checkpoints.mkdir(parents=True)
    (checkpoints / "plan.json").write_text(json.dumps({
        "voice": "ml-anjali", "speed": 1.0, "segments": [{}, {}, {}],
    }), encoding="utf-8")
    (checkpoints / "chunk-0001.wav").touch()
    (checkpoints / "incomplete-tmp-file").touch()

    progress = batch_progress(tmp_path)
    assert progress["parts"][0]["status"] == "completed"
    assert progress["parts"][0]["chunks_total"] is None
    assert progress["parts"][1]["chunks_total"] == 3
    assert progress["parts"][1]["chunks_done"] == 1

    # Each request discovers newly persisted chunks without worker changes.
    (checkpoints / "chunk-0002.wav").touch()
    assert batch_progress(tmp_path)["parts"][1]["chunks_done"] == 2
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest

    # A checkpoint made for a different voice must not inflate this run's count.
    (checkpoints / "plan.json").write_text(json.dumps({
        "voice": "ml-harish", "speed": 1.0, "segments": [{}, {}, {}],
    }), encoding="utf-8")
    assert batch_progress(tmp_path)["parts"][1]["chunks_total"] is None
