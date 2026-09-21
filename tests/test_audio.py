import io
import wave

import pytest

from bhashavox.audio import IncompatibleAudioError, join_wav
from bhashavox.providers.tone import ToneProvider


def test_join_wav_combines_chunks_and_silence() -> None:
    provider = ToneProvider()
    first = provider.synthesize("hello", "en", None, 1.0)
    second = provider.synthesize("வணக்கம்", "ta", None, 1.0)

    combined = join_wav([first, second], silence_ms=100)

    with wave.open(io.BytesIO(combined), "rb") as result:
        assert result.getnchannels() == 1
        assert result.getframerate() == 16_000
        assert result.getnframes() > 1_600


def test_join_wav_rejects_invalid_audio() -> None:
    with pytest.raises(IncompatibleAudioError):
        join_wav([b"not a wave"])

