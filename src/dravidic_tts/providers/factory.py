"""Provider selection from configuration."""

from __future__ import annotations

from dravidic_tts.providers.base import SpeechProvider
from dravidic_tts.providers.espeak import EspeakProvider
from dravidic_tts.providers.indic_parler import IndicParlerProvider
from dravidic_tts.providers.tone import ToneProvider


def create_provider(name: str) -> SpeechProvider:
    if name == "indic-parler":
        return IndicParlerProvider()
    if name == "espeak":
        return EspeakProvider()
    if name == "tone":
        return ToneProvider()
    raise ValueError(f"unknown TTS provider: {name}")
