"""Text-to-speech orchestration independent of HTTP and model vendors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dravidic_tts.audio import join_wav
from dravidic_tts.checkpoints import SpeechCheckpoints
from dravidic_tts.language import LanguageChoice, choose_segments, chunk_segments
from dravidic_tts.providers.base import SpeechProvider


@dataclass(frozen=True, slots=True)
class SpeechResult:
    audio: bytes
    segment_count: int


class SpeechService:
    def __init__(self, provider: SpeechProvider) -> None:
        self.provider = provider

    def synthesize(
        self,
        text: str,
        language: LanguageChoice,
        voice: str | None,
        speed: float,
        progress_callback: Callable[[int, int], None] | None = None,
        checkpoint_directory: Path | None = None,
        reuse_checkpoints: bool = True,
    ) -> SpeechResult:
        segments = chunk_segments(choose_segments(text, language))
        if not segments:
            raise ValueError("text does not contain speakable characters")
        checkpoints = None
        if checkpoint_directory is not None:
            checkpoints = SpeechCheckpoints(
                checkpoint_directory,
                {
                    "version": 1,
                    "provider": self.provider.name,
                    "model": getattr(self.provider, "model_id", None),
                    "voice": voice if language != "auto" else None,
                    "speed": speed,
                    "segments": [
                        {"text": segment.text, "language": segment.language}
                        for segment in segments
                    ],
                },
            )
        if progress_callback:
            progress_callback(0, len(segments))
        chunks: list[bytes] = []
        for index, segment in enumerate(segments, start=1):
            audio = (
                checkpoints.load(index)
                if checkpoints is not None and reuse_checkpoints
                else None
            )
            if audio is None:
                audio = self.provider.synthesize(
                    segment.text,
                    segment.language,
                    voice if language != "auto" else None,
                    speed,
                )
                if checkpoints is not None:
                    checkpoints.save(index, audio)
            chunks.append(audio)
            if progress_callback:
                progress_callback(index, len(segments))
        return SpeechResult(audio=join_wav(chunks), segment_count=len(segments))
