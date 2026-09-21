"""Provider selection from configuration."""

from __future__ import annotations

from bhashavox.providers.base import SpeechProvider
from bhashavox.providers.espeak import EspeakProvider
from bhashavox.providers.indic_parler import IndicParlerProvider
from bhashavox.providers.tone import ToneProvider


def create_provider(name: str) -> SpeechProvider:
    if name == "indic-parler":
        return IndicParlerProvider()
    if name == "espeak":
        return EspeakProvider()
    if name == "tone":
        return ToneProvider()
    raise ValueError(f"unknown TTS provider: {name}")
