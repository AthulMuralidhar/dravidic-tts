"""Small, explainable native-script detection and segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "ta", "ml"]
LanguageChoice = Literal["auto", "en", "ta", "ml"]


@dataclass(frozen=True, slots=True)
class TextSegment:
    text: str
    language: Language


def character_language(character: str) -> Language | None:
    """Return a language for a script-bearing character.

    Neutral characters such as whitespace and punctuation return ``None`` and
    are attached to a neighboring segment by :func:`segment_by_script`.
    """

    codepoint = ord(character)
    if 0x0B80 <= codepoint <= 0x0BFF:
        return "ta"
    if 0x0D00 <= codepoint <= 0x0D7F:
        return "ml"
    if character.isascii() and character.isalnum():
        return "en"
    return None


def segment_by_script(text: str) -> list[TextSegment]:
    """Split text when its Unicode script changes.

    This deliberately detects script, not spoken language. Romanized Tamil or
    Malayalam therefore remains English/Latin until the user explicitly asks
    for a future transliteration feature.
    """

    segments: list[TextSegment] = []
    neutral_prefix = ""
    current_text = ""
    current_language: Language | None = None

    for character in text:
        language = character_language(character)
        if language is None:
            if current_language is None:
                neutral_prefix += character
            else:
                current_text += character
            continue

        if current_language is None:
            current_language = language
            current_text = neutral_prefix + character
            neutral_prefix = ""
            continue

        if language == current_language:
            current_text += character
            continue

        segments.append(TextSegment(current_text, current_language))
        current_language = language
        current_text = character

    if current_language is not None:
        segments.append(TextSegment(current_text + neutral_prefix, current_language))
    elif any(character.isalnum() for character in neutral_prefix):
        segments.append(TextSegment(neutral_prefix, "en"))

    return [segment for segment in segments if segment.text.strip()]


def choose_segments(text: str, language: LanguageChoice) -> list[TextSegment]:
    if language == "auto":
        return segment_by_script(text)
    return [TextSegment(text=text, language=language)]
