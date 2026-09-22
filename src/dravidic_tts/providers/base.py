"""Contract shared by every speech engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from dravidic_tts.language import Language


class ProviderUnavailable(RuntimeError):
    """Raised when a configured speech engine cannot serve a request."""


@dataclass(frozen=True, slots=True)
class ProviderVoice:
    id: str
    label: str
    language: Language


class SpeechProvider(ABC):
    name: str

    @property
    @abstractmethod
    def ready(self) -> bool:
        """Whether the provider is able to synthesize now."""

    @property
    @abstractmethod
    def voices(self) -> tuple[ProviderVoice, ...]:
        """Voices exposed by this provider."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: Language,
        voice: str | None,
        speed: float,
    ) -> bytes:
        """Return one PCM WAV document."""
