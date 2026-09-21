"""FastAPI application entry point."""

from __future__ import annotations

import io

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from bhashavox import __version__
from bhashavox.config import Settings
from bhashavox.models import (
    CapabilitiesResponse,
    HealthResponse,
    SpeechRequest,
    Voice,
)
from bhashavox.providers.base import ProviderUnavailable, SpeechProvider
from bhashavox.providers.factory import create_provider
from bhashavox.service import SpeechService


def create_app(
    settings: Settings | None = None,
    provider: SpeechProvider | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_provider = provider or create_provider(active_settings.provider)
    speech_service = SpeechService(active_provider)

    app = FastAPI(
        title="BhashaVox",
        version=__version__,
        description="Local-first English, Tamil, and Malayalam text to speech.",
    )

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        ready = active_provider.ready
        return HealthResponse(
            status="ok" if ready else "degraded",
            version=__version__,
            provider=active_provider.name,
            provider_ready=ready,
        )

    @app.get("/api/v1/capabilities", response_model=CapabilitiesResponse)
    async def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            provider=active_provider.name,
            ready=active_provider.ready,
            languages=["en", "ta", "ml"],
            formats=["wav"],
            voices=[
                Voice(id=voice.id, label=voice.label, language=voice.language)
                for voice in active_provider.voices
            ],
            supports_mixed_native_scripts=True,
            max_characters=active_settings.max_characters,
        )

    @app.post("/api/v1/speech")
    async def speech(request: SpeechRequest) -> StreamingResponse:
        if len(request.text) > active_settings.max_characters:
            raise HTTPException(
                status_code=413,
                detail=(
                    "text exceeds the configured limit of "
                    f"{active_settings.max_characters} characters"
                ),
            )
        if not active_provider.ready:
            raise HTTPException(status_code=503, detail="speech provider is not ready")
        try:
            result = await run_in_threadpool(
                speech_service.synthesize,
                request.text,
                request.language,
                request.voice,
                request.speed,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ProviderUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return StreamingResponse(
            io.BytesIO(result.audio),
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="bhashavox.wav"',
                "X-BhashaVox-Segments": str(result.segment_count),
            },
        )

    return app


app = create_app()


def run() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "bhashavox.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()

