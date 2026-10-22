from pathlib import Path

import pytest

from dravidic_tts.providers.tone import ToneProvider
from dravidic_tts.service import SpeechService

TEXT = ("A complete sentence with enough text to split into several chunks. " * 12)


class InterruptedProvider(ToneProvider):
    def __init__(self, fail_at: int | None = None) -> None:
        self.calls = 0
        self.fail_at = fail_at

    def synthesize(self, text, language, voice, speed):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("simulated worker interruption")
        return super().synthesize(text, language, voice, speed)


def test_restart_reuses_completed_chunks_after_interruption(tmp_path: Path) -> None:
    interrupted = InterruptedProvider(fail_at=2)
    with pytest.raises(RuntimeError, match="interruption"):
        SpeechService(interrupted).synthesize(
            TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
        )
    assert len(list(tmp_path.rglob("chunk-*.wav"))) == 1

    restarted = InterruptedProvider()
    result = SpeechService(restarted).synthesize(
        TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
    )
    assert restarted.calls == result.segment_count - 1
    assert result.audio == SpeechService(ToneProvider()).synthesize(
        TEXT, "en", None, 1.0
    ).audio

    # A fresh service can reconstruct the final part without any synthesis.
    cached_only = InterruptedProvider(fail_at=1)
    assert SpeechService(cached_only).synthesize(
        TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
    ).audio == result.audio
    assert cached_only.calls == 0


def test_truncated_checkpoint_is_regenerated(tmp_path: Path) -> None:
    service = SpeechService(InterruptedProvider())
    result = service.synthesize(TEXT, "en", None, 1.0, checkpoint_directory=tmp_path)
    checkpoint = next(tmp_path.rglob("chunk-*.wav"))
    checkpoint.write_bytes(checkpoint.read_bytes()[:-100])
    restarted = InterruptedProvider()
    assert SpeechService(restarted).synthesize(
        TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
    ).audio == result.audio
    assert restarted.calls == 1


@pytest.mark.parametrize("change", ["text", "voice", "speed", "model"])
def test_changed_generation_settings_use_separate_checkpoints(
    tmp_path: Path, change: str
) -> None:
    SpeechService(ToneProvider()).synthesize(
        TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
    )
    provider = InterruptedProvider()
    if change == "model":
        provider.model_id = "another-model"
    result = SpeechService(provider).synthesize(
        TEXT + " Changed." if change == "text" else TEXT,
        "en",
        "another-voice" if change == "voice" else None,
        0.8 if change == "speed" else 1.0,
        checkpoint_directory=tmp_path,
    )
    assert provider.calls == result.segment_count


def test_force_rebuilds_all_checkpoints(tmp_path: Path) -> None:
    SpeechService(ToneProvider()).synthesize(
        TEXT, "en", None, 1.0, checkpoint_directory=tmp_path
    )
    provider = InterruptedProvider()
    result = SpeechService(provider).synthesize(
        TEXT, "en", None, 1.0,
        checkpoint_directory=tmp_path, reuse_checkpoints=False,
    )
    assert provider.calls == result.segment_count
