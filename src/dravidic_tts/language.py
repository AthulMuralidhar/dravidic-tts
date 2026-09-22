"""Small, explainable native-script detection and segmentation."""

from __future__ import annotations

import unicodedata
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


def chunk_segments(
    segments: list[TextSegment],
    max_characters: int = 240,
) -> list[TextSegment]:
    """Split long script segments at readable boundaries for neural synthesis."""

    if max_characters < 1:
        raise ValueError("max_characters must be positive")

    chunks: list[TextSegment] = []
    for segment in segments:
        remaining = segment.text.strip()
        while len(remaining) > max_characters:
            window = remaining[: max_characters + 1]
            split_at = _preferred_split(window, max_characters)
            chunk = remaining[:split_at].strip()
            if chunk:
                chunks.append(TextSegment(chunk, segment.language))
            remaining = remaining[split_at:].strip()
        if remaining:
            chunks.append(TextSegment(remaining, segment.language))
    return chunks


def _preferred_split(window: str, limit: int) -> int:
    minimum = max(1, limit // 3)
    sentence_breaks = ".!?।\n"
    sentence_split = max(
        window.rfind(mark, minimum, limit + 1) for mark in sentence_breaks
    )
    if sentence_split >= minimum:
        return sentence_split + 1

    whitespace_split = max(
        (
            index
            for index in range(minimum, min(len(window), limit + 1))
            if window[index].isspace()
        ),
        default=-1,
    )
    if whitespace_split >= minimum:
        return whitespace_split

    split_at = min(limit, len(window))
    while split_at > 1 and unicodedata.category(window[split_at]).startswith("M"):
        split_at -= 1
    return split_at
