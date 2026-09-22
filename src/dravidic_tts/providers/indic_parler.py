"""High-quality AI4Bharat Indic Parler-TTS speech provider."""

from __future__ import annotations

import importlib.util
import io
import os
import threading
from typing import Any

from dravidic_tts.language import Language
from dravidic_tts.providers.base import (
    ProviderUnavailable,
    ProviderVoice,
    SpeechProvider,
)

DEFAULT_MODEL_ID = "ai4bharat/indic-parler-tts"

VOICE_NAMES = {
    "en-thoma": "Thoma",
    "en-mary": "Mary",
    "ta-jaya": "Jaya",
    "ta-kavitha": "Kavitha",
    "ml-anjali": "Anjali",
    "ml-harish": "Harish",
}

DEFAULT_VOICES: dict[Language, str] = {
    "en": "en-mary",
    "ta": "ta-jaya",
    "ml": "ml-anjali",
}


class IndicParlerProvider(SpeechProvider):
    name = "indic-parler"

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.getenv(
            "DRAVIDIC_TTS_PARLER_MODEL", DEFAULT_MODEL_ID
        )
        self._model: Any | None = None
        self._prompt_tokenizer: Any | None = None
        self._description_tokenizer: Any | None = None
        self._device = "cpu"
        self._load_lock = threading.Lock()
        self._generation_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return all(
            importlib.util.find_spec(module) is not None
            for module in ("torch", "parler_tts", "transformers", "soundfile")
        )

    @property
    def voices(self) -> tuple[ProviderVoice, ...]:
        return (
            ProviderVoice("en-mary", "Mary — English", "en"),
            ProviderVoice("en-thoma", "Thoma — English", "en"),
            ProviderVoice("ta-jaya", "Jaya — தமிழ்", "ta"),
            ProviderVoice("ta-kavitha", "Kavitha — தமிழ்", "ta"),
            ProviderVoice("ml-anjali", "Anjali — മലയാളം", "ml"),
            ProviderVoice("ml-harish", "Harish — മലയാളം", "ml"),
        )

    def synthesize(
        self,
        text: str,
        language: Language,
        voice: str | None,
        speed: float,
    ) -> bytes:
        if not self.ready:
            raise ProviderUnavailable(
                "Indic Parler-TTS dependencies are not installed. "
                "Run the neural Docker image."
            )
        self._load()
        voice_id = voice or DEFAULT_VOICES[language]
        speaker = VOICE_NAMES.get(voice_id)
        if speaker is None or not voice_id.startswith(f"{language}-"):
            raise ValueError(f"voice {voice_id!r} is not available for {language}")

        description = _description(speaker, speed)
        try:
            with self._generation_lock:
                return self._generate_wav(text, description)
        except (ValueError, RuntimeError) as exc:
            raise ProviderUnavailable(
                f"Indic Parler-TTS could not generate audio: {exc}"
            ) from exc

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            try:
                import torch
                from parler_tts import ParlerTTSForConditionalGeneration
                from transformers import AutoTokenizer

                self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
                dtype = torch.float16 if self._device != "cpu" else torch.float32
                model = ParlerTTSForConditionalGeneration.from_pretrained(
                    self.model_id,
                    attn_implementation="eager",
                    torch_dtype=dtype,
                ).to(self._device)
                self._prompt_tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                self._description_tokenizer = AutoTokenizer.from_pretrained(
                    model.config.text_encoder._name_or_path
                )
                self._model = model.eval()
            except Exception as exc:
                raise ProviderUnavailable(
                    "The neural model could not be loaded. Confirm model access "
                    "and run `docker compose --profile setup run --rm hf-login`."
                ) from exc

    def _generate_wav(self, text: str, description: str) -> bytes:
        import soundfile
        import torch

        description_inputs = self._description_tokenizer(
            description, return_tensors="pt"
        ).to(self._device)
        prompt_inputs = self._prompt_tokenizer(text, return_tensors="pt").to(
            self._device
        )
        with torch.inference_mode():
            generation = self._model.generate(
                input_ids=description_inputs.input_ids,
                attention_mask=description_inputs.attention_mask,
                prompt_input_ids=prompt_inputs.input_ids,
                prompt_attention_mask=prompt_inputs.attention_mask,
            )
        audio = generation.detach().cpu().float().numpy().squeeze()
        document = io.BytesIO()
        soundfile.write(
            document,
            audio,
            self._model.config.sampling_rate,
            format="WAV",
            subtype="PCM_16",
        )
        return document.getvalue()


def _description(speaker: str, speed: float) -> str:
    pace = "slow" if speed < 0.9 else "fast" if speed > 1.1 else "moderate"
    return (
        f"{speaker}'s voice speaks at a {pace} pace with a natural, expressive "
        "delivery. The recording is very high quality, clear, close-sounding, "
        "and has no background noise."
    )
