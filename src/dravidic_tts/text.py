"""Conservative cleanup and diagnostics for pasted multilingual text."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

MALAYALAM_PREBASE_SIGNS = frozenset("െേൈ")
MALAYALAM_VIRAMA = "്"
MALAYALAM_PLACEHOLDER_REPAIRS = {
    "രാ?തി": "രാത്രി",
    "ഇ?ത": "ഇത്ര",
}


@dataclass(frozen=True, slots=True)
class TextIssue:
    code: str
    message: str
    count: int


@dataclass(frozen=True, slots=True)
class TextReview:
    original: str
    repaired: str
    changed: bool
    issues: tuple[TextIssue, ...]


def review_text(text: str) -> TextReview:
    """Repair deterministic Unicode-order damage and report ambiguous loss.

    Some PDF, OCR, and legacy-font copy operations put Malayalam's visual
    pre-base vowel signs before their consonant in the underlying Unicode
    string. Moving such a sign after the following consonant or conjunct is a
    mechanical repair. A question mark between Malayalam characters may stand
    for a lost glyph, but its intended value cannot be inferred safely.
    """

    repaired, reordered_count = _repair_malayalam_prebase_signs(text)
    issues: list[TextIssue] = []
    if reordered_count:
        issues.append(
            TextIssue(
                code="malayalam-prebase-order",
                message=(
                    "Reordered Malayalam vowel signs damaged during copy/paste."
                ),
                count=reordered_count,
            )
        )

    repaired, restored_count, fallback_count = _repair_malayalam_placeholders(
        repaired
    )
    if restored_count:
        issues.append(
            TextIssue(
                code="restored-malayalam-glyph",
                message=(
                    "Restored Malayalam letters represented as question marks "
                    "by the copied source."
                ),
                count=restored_count,
            )
        )
    if fallback_count:
        issues.append(
            TextIssue(
                code="removed-unknown-placeholder",
                message=(
                    "Removed unknown placeholders so they are not spoken aloud."
                ),
                count=fallback_count,
            )
        )

    return TextReview(
        original=text,
        repaired=repaired,
        changed=repaired != text,
        issues=tuple(issues),
    )


def _repair_malayalam_prebase_signs(text: str) -> tuple[str, int]:
    output: list[str] = []
    index = 0
    repair_count = 0

    while index < len(text):
        character = text[index]
        next_index = index + 1
        previous = text[index - 1] if index else ""
        if (
            character not in MALAYALAM_PREBASE_SIGNS
            or next_index >= len(text)
            or _is_malayalam_consonant(previous)
            or not _is_malayalam_consonant(text[next_index])
        ):
            output.append(character)
            index += 1
            continue

        cluster_end = next_index + 1
        while (
            cluster_end + 1 < len(text)
            and text[cluster_end] == MALAYALAM_VIRAMA
            and _is_malayalam_consonant(text[cluster_end + 1])
        ):
            cluster_end += 2

        output.extend(text[next_index:cluster_end])
        output.append(character)
        index = cluster_end
        repair_count += 1

    return unicodedata.normalize("NFC", "".join(output)), repair_count


def _is_malayalam_consonant(character: str) -> bool:
    if not character:
        return False
    codepoint = ord(character)
    return 0x0D15 <= codepoint <= 0x0D3A or 0x0D7A <= codepoint <= 0x0D7F


def _repair_malayalam_placeholders(text: str) -> tuple[str, int, int]:
    restored_count = 0
    for damaged, restored in MALAYALAM_PLACEHOLDER_REPAIRS.items():
        occurrences = text.count(damaged)
        if occurrences:
            text = text.replace(damaged, restored)
            restored_count += occurrences

    output: list[str] = []
    fallback_count = 0
    for index, character in enumerate(text):
        if character != "?":
            output.append(character)
            continue
        before = text[index - 1] if index else ""
        after = text[index + 1] if index + 1 < len(text) else ""
        if _is_malayalam_character(before) or _is_malayalam_character(after):
            fallback_count += 1
            continue
        output.append(character)
    return "".join(output), restored_count, fallback_count


def _is_malayalam_character(character: str) -> bool:
    return bool(character) and 0x0D00 <= ord(character) <= 0x0D7F
