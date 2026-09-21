"""Deterministic provider for tests and API development."""

from __future__ import annotations

import io
import math
import struct
import wave

from bhashavox.language import Language
from bhashavox.providers.base import ProviderVoice, SpeechProvider


class ToneProvider(SpeechProvider):
    name = "tone"
    _frequency: dict[Language, float] = {"en": 330.0, "ta": 440.0, "ml": 550.0}

    @property
    def ready(self) -> bool:
        return True

    @property
    def voices(self) -> tuple[ProviderVoice, ...]:
        return (
            ProviderVoice("en", "English test tone", "en"),
            ProviderVoice("ta", "Tamil test tone", "ta"),
            ProviderVoice("ml", "Malayalam test tone", "ml"),
        )

    def synthesize(
        self,
        text: str,
        language: Language,
        voice: str | None,
        speed: float,
    ) -> bytes:
        del voice
        sample_rate = 16_000
        duration = min(0.8, max(0.08, len(text) / 80 / speed))
        frame_count = round(sample_rate * duration)
        frequency = self._frequency[language]
        frames = bytearray()
        for frame in range(frame_count):
            envelope = min(1.0, frame / 160, (frame_count - frame) / 160)
            sample = round(
                5_000
                * envelope
                * math.sin(2 * math.pi * frequency * frame / sample_rate)
            )
            frames.extend(struct.pack("<h", sample))

        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(sample_rate)
            target.writeframes(frames)
        return output.getvalue()

