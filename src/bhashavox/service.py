"""Text-to-speech orchestration independent of HTTP and model vendors."""

from __future__ import annotations

from dataclasses import dataclass

from bhashavox.audio import join_wav
from bhashavox.language import LanguageChoice, choose_segments
from bhashavox.providers.base import SpeechProvider


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
    ) -> SpeechResult:
        segments = choose_segments(text, language)
        if not segments:
            raise ValueError("text does not contain speakable characters")
        chunks = [
            self.provider.synthesize(
                segment.text,
                segment.language,
                voice if language != "auto" else None,
                speed,
            )
            for segment in segments
        ]
        return SpeechResult(audio=join_wav(chunks), segment_count=len(segments))

