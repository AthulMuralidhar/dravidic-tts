from bhashavox.language import TextSegment, choose_segments, segment_by_script


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
