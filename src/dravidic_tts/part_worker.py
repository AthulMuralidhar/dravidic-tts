"""One short-lived inference process per PDF audio part."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dravidic_tts.pdf_batch import (
    _atomic_write_bytes,
    _atomic_write_text,
    _wav_duration,
)
from dravidic_tts.providers.factory import create_provider
from dravidic_tts.service import SpeechService


def memory_snapshot() -> dict[str, int]:
    snapshot = {"pid": os.getpid()}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            key, _, value = line.partition(":")
            if key in ("VmRSS", "VmHWM", "VmSwap"):
                snapshot[key] = int(value.strip().split()[0])
    except FileNotFoundError:
        pass
    return snapshot


def generate_part(request: dict[str, Any]) -> None:
    provider = create_provider(request["provider"])
    if not provider.ready:
        raise RuntimeError(f"Speech provider {provider.name!r} is not ready")

    def progress(done: int, total: int) -> None:
        snapshot = {
            "chunks_done": done, "chunks_total": total,
            "memory_kib": memory_snapshot(),
        }
        _atomic_write_text(Path(request["progress_path"]), json.dumps(snapshot))
        print(
            f"{request['stem']}: neural chunk {done}/{total} "
            f"memory_kib={snapshot['memory_kib']}", flush=True,
        )

    result = SpeechService(provider).synthesize(
        Path(request["text_path"]).read_text(encoding="utf-8"),
        request["language"], request["voice"], request["speed"],
        checkpoint_directory=Path(request["checkpoint_directory"]),
        reuse_checkpoints=request["reuse_checkpoints"],
        progress_callback=progress,
    )
    # The supervisor publishes completion only after the part and metadata exist.
    _atomic_write_bytes(Path(request["audio_path"]), result.audio)
    _atomic_write_text(Path(request["result_path"]), json.dumps({
        "segments": result.segment_count,
        "duration_seconds": round(_wav_duration(result.audio), 3),
        "memory_kib": memory_snapshot(),
    }))


def main() -> None:
    generate_part(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
