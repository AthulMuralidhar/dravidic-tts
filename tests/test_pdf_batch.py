from dravidic_tts.pdf_batch import (
    build_parts,
    clean_page_text,
    embedded_text_needs_ocr,
)


def test_detects_broken_embedded_pdf_text() -> None:
    assert embedded_text_needs_ocr("മലയാളം\x00" * 20)
    assert embedded_text_needs_ocr("മലയാളം\ufffe" * 20)
    assert embedded_text_needs_ocr("short")
    assert not embedded_text_needs_ocr("മലയാളം വാചകം " * 20)


def test_clean_page_text_removes_known_furniture() -> None:
    text = """Nishayude Ponnumon | Author : Vinayan

    ഒന്നാം വരി\x00 ഇവിടെ
    രണ്ടാം വരി
    www.kambistories.com | Malayalam Kambi Kathakal
    42
    """

    assert clean_page_text(text) == "ഒന്നാം വരി ഇവിടെ രണ്ടാം വരി"


def test_build_parts_respects_limit_and_page_labels() -> None:
    pages = [
        (1, "ഒന്ന് " * 100),
        (2, "രണ്ട് " * 100),
        (3, "മൂന്ന് " * 100),
    ]

    parts = build_parts(pages, max_characters=700)

    assert len(parts) == 3
    assert all(len(part.text) <= 700 for part in parts)
    assert [(part.page_start, part.page_end) for part in parts] == [
        (1, 1),
        (2, 2),
        (3, 3),
    ]
