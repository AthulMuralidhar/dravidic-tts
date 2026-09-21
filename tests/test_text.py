from bhashavox.text import review_text


def test_repairs_misordered_malayalam_prebase_vowels() -> None:
    review = review_text("േവഗം െകാണ്ട് േരഖ")

    assert review.repaired == "വേഗം കൊണ്ട് രേഖ"
    assert review.changed is True
    assert review.issues[0].code == "malayalam-prebase-order"
    assert review.issues[0].count == 3


def test_preserves_correct_malayalam() -> None:
    review = review_text("വേഗം കൊണ്ട് രേഖ")

    assert review.repaired == review.original
    assert review.changed is False
    assert review.issues == ()


def test_automatically_restores_known_missing_malayalam_glyphs() -> None:
    review = review_text("രാ?തി ഇ?തയും")

    assert review.repaired == "രാത്രി ഇത്രയും"
    assert review.changed is True
    assert review.issues[0].code == "restored-malayalam-glyph"
    assert review.issues[0].count == 2


def test_removes_unknown_malayalam_placeholder_instead_of_speaking_it() -> None:
    review = review_text("അ?ജ്ഞാതം")

    assert review.repaired == "അജ്ഞാതം"
    assert review.changed is True
    assert review.issues[0].code == "removed-unknown-placeholder"
