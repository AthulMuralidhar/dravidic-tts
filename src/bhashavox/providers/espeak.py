"""CPU-friendly eSpeak NG provider."""

from __future__ import annotations

import shutil
import subprocess

from bhashavox.language import Language
from bhashavox.providers.base import (
    ProviderUnavailable,
    ProviderVoice,
    SpeechProvider,
)


class EspeakProvider(SpeechProvider):
    name = "espeak"
    _voice_by_language: dict[Language, str] = {
        "en": "en",
        "ta": "ta",
        "ml": "ml",
    }

    def __init__(self, executable: str = "espeak-ng") -> None:
        self.executable = executable

    @property
    def ready(self) -> bool:
        return shutil.which(self.executable) is not None

    @property
    def voices(self) -> tuple[ProviderVoice, ...]:
        return (
            ProviderVoice("en", "English", "en"),
            ProviderVoice("ta", "Tamil", "ta"),
            ProviderVoice("ml", "Malayalam", "ml"),
        )

    def synthesize(
        self,
        text: str,
        language: Language,
        voice: str | None,
        speed: float,
    ) -> bytes:
        if not self.ready:
            raise ProviderUnavailable(
                "eSpeak NG is not installed; use Docker or install espeak-ng"
            )
        selected_voice = voice or self._voice_by_language[language]
        allowed_voices = {item.id for item in self.voices}
        if selected_voice not in allowed_voices:
            raise ValueError(f"voice {selected_voice!r} is not available")

        words_per_minute = round(175 * speed)
        command = [
            self.executable,
            "--stdin",
            "--stdout",
            "-v",
            selected_voice,
            "-s",
            str(words_per_minute),
        ]
        try:
            result = subprocess.run(
                command,
                input=text.encode("utf-8"),
                capture_output=True,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderUnavailable("eSpeak NG synthesis failed") from exc
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise ProviderUnavailable(detail or "eSpeak NG synthesis failed")
        return result.stdout

