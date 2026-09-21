"""HTTP request and response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

LanguageChoice = Literal["auto", "en", "ta", "ml"]


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1)
    language: LanguageChoice = "auto"
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.6, le=1.6)
    format: Literal["wav"] = "wav"

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain something to speak")
        return value


class Voice(BaseModel):
    id: str
    label: str
    language: Literal["en", "ta", "ml"]


class CapabilitiesResponse(BaseModel):
    provider: str
    ready: bool
    languages: list[str]
    formats: list[str]
    voices: list[Voice]
    supports_mixed_native_scripts: bool
    max_characters: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    provider: str
    provider_ready: bool

