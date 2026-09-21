"""Environment-driven service configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    provider: str = "espeak"
    max_characters: int = 5_000
    host: str = "0.0.0.0"
    port: int = 8000

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            provider=os.getenv("BHASHAVOX_TTS_PROVIDER", "espeak").strip().lower(),
            max_characters=_positive_int("BHASHAVOX_MAX_CHARACTERS", 5_000),
            host=os.getenv("BHASHAVOX_HOST", "0.0.0.0"),
            port=_positive_int("BHASHAVOX_PORT", 8000),
        )


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value

