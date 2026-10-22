"""Atomic, validated disk checkpoints for individual speech chunks."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import wave
from pathlib import Path
from typing import Any


class SpeechCheckpoints:
    def __init__(self, directory: Path, plan: dict[str, Any]) -> None:
        serialized = json.dumps(plan, ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        self.directory = directory / fingerprint
        self.directory.mkdir(parents=True, exist_ok=True)
        self._write(self.directory / "plan.json", serialized.encode("utf-8"))

    @staticmethod
    def _validate(audio: bytes) -> None:
        with wave.open(io.BytesIO(audio), "rb") as document:
            frame_count = document.getnframes()
            expected = frame_count * document.getnchannels() * document.getsampwidth()
            if frame_count == 0 or len(document.readframes(frame_count)) != expected:
                raise ValueError("empty or truncated speech checkpoint")

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(data)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def load(self, index: int) -> bytes | None:
        path = self.directory / f"chunk-{index:04d}.wav"
        try:
            audio = path.read_bytes()
            self._validate(audio)
        except (FileNotFoundError, EOFError, wave.Error, ValueError):
            return None
        return audio

    def save(self, index: int, audio: bytes) -> None:
        self._validate(audio)
        self._write(self.directory / f"chunk-{index:04d}.wav", audio)
