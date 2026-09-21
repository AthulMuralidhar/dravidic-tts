"""WAV utilities used to combine provider output."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass


class IncompatibleAudioError(ValueError):
    """Raised when WAV chunks cannot be joined without resampling."""


@dataclass(frozen=True, slots=True)
class WavChunk:
    channels: int
    sample_width: int
    frame_rate: int
    compression_type: str
    frames: bytes


def read_wav(data: bytes) -> WavChunk:
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            return WavChunk(
                channels=source.getnchannels(),
                sample_width=source.getsampwidth(),
                frame_rate=source.getframerate(),
                compression_type=source.getcomptype(),
                frames=source.readframes(source.getnframes()),
            )
    except (EOFError, wave.Error) as exc:
        raise IncompatibleAudioError("provider returned an invalid WAV file") from exc


def join_wav(chunks: list[bytes], silence_ms: int = 90) -> bytes:
    if not chunks:
        raise ValueError("at least one WAV chunk is required")
    if len(chunks) == 1:
        read_wav(chunks[0])
        return chunks[0]

    decoded = [read_wav(chunk) for chunk in chunks]
    template = decoded[0]
    for chunk in decoded[1:]:
        if (
            chunk.channels,
            chunk.sample_width,
            chunk.frame_rate,
            chunk.compression_type,
        ) != (
            template.channels,
            template.sample_width,
            template.frame_rate,
            template.compression_type,
        ):
            raise IncompatibleAudioError(
                "provider returned WAV chunks with different audio parameters"
            )

    silent_frames = round(template.frame_rate * silence_ms / 1000)
    silence = b"\x00" * silent_frames * template.channels * template.sample_width

    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(template.channels)
        target.setsampwidth(template.sample_width)
        target.setframerate(template.frame_rate)
        target.setcomptype(template.compression_type, "not compressed")
        for index, chunk in enumerate(decoded):
            if index:
                target.writeframesraw(silence)
            target.writeframesraw(chunk.frames)
    return output.getvalue()

