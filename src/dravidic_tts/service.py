"""Text-to-speech orchestration independent of HTTP and model vendors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dravidic_tts.audio import join_wav
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
    ) -> SpeechResult:
        segments = chunk_segments(choose_segments(text, language))
        if not segments:
            raise ValueError("text does not contain speakable characters")
        if progress_callback:
            progress_callback(0, len(segments))
        chunks: list[bytes] = []
        for index, segment in enumerate(segments, start=1):
            chunks.append(
                self.provider.synthesize(
                    segment.text,
                    segment.language,
                    voice if language != "auto" else None,
                    speed,
                )
            )
            if progress_callback:
                progress_callback(index, len(segments))
        return SpeechResult(audio=join_wav(chunks), segment_count=len(segments))
