import unicodedata

from dravidic_tts.language import (
    TextSegment,
    choose_segments,
    chunk_segments,
    segment_by_script,
)


def test_segments_english_tamil_and_malayalam() -> None:
    text = "Hello. வணக்கம். നമസ്കാരം."

    assert segment_by_script(text) == [
        TextSegment("Hello. ", "en"),
        TextSegment("வணக்கம். ", "ta"),
        TextSegment("നമസ്കാരം.", "ml"),
    ]


def test_explicit_language_preserves_whole_text() -> None:
    assert choose_segments("amma is here", "ta") == [
        TextSegment("amma is here", "ta")
    ]


def test_punctuation_only_is_not_speakable() -> None:
    assert segment_by_script(" ... ") == []


def test_long_segments_split_at_sentence_boundaries() -> None:
    segments = [TextSegment("First sentence. Second sentence.", "en")]

    assert chunk_segments(segments, max_characters=20) == [
        TextSegment("First sentence.", "en"),
        TextSegment("Second sentence.", "en"),
    ]


def test_long_words_do_not_leave_a_combining_mark_at_chunk_start() -> None:
    segments = [TextSegment("അമ്മയോടൊപ്പം", "ml")]

    chunks = chunk_segments(segments, max_characters=4)

    assert "".join(chunk.text for chunk in chunks) == "അമ്മയോടൊപ്പം"
    assert all(
        not unicodedata.category(chunk.text[0]).startswith("M") for chunk in chunks
    )
