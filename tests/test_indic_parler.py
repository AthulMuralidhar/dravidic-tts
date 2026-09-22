from dravidic_tts.providers.indic_parler import IndicParlerProvider, _description


def test_exposes_recommended_voices_for_all_product_languages() -> None:
    voices = IndicParlerProvider().voices

    assert {(voice.id, voice.language) for voice in voices} == {
        ("en-mary", "en"),
        ("en-thoma", "en"),
        ("ta-jaya", "ta"),
        ("ta-kavitha", "ta"),
        ("ml-anjali", "ml"),
        ("ml-harish", "ml"),
    }


def test_description_translates_speed_to_model_instruction() -> None:
    assert "slow pace" in _description("Anjali", 0.8)
    assert "moderate pace" in _description("Anjali", 1.0)
    assert "fast pace" in _description("Anjali", 1.2)
