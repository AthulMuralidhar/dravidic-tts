"""FastAPI application entry point."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from bhashavox import __version__
from bhashavox.config import Settings
from bhashavox.jobs import SpeechJobManager, SpeechJobSnapshot
from bhashavox.models import (
    CapabilitiesResponse,
    HealthResponse,
    SpeechJobResponse,
    SpeechRequest,
    TextReviewIssue,
    TextReviewRequest,
    TextReviewResponse,
    Voice,
)
from bhashavox.providers.base import ProviderUnavailable, SpeechProvider
from bhashavox.providers.factory import create_provider
from bhashavox.service import SpeechService
from bhashavox.text import review_text


def create_app(
    settings: Settings | None = None,
    provider: SpeechProvider | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_provider = provider or create_provider(active_settings.provider)
    speech_service = SpeechService(active_provider)
    job_manager = SpeechJobManager(speech_service)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        job_manager.close()

    app = FastAPI(
        title="BhashaVox",
        version=__version__,
        description="Local-first English, Tamil, and Malayalam text to speech.",
        lifespan=lifespan,
    )
    static_directory = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_directory), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_directory / "index.html")

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health(response: Response) -> HealthResponse:
        ready = active_provider.ready
        if not ready:
            response.status_code = 503
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

    @app.post("/api/v1/text/review", response_model=TextReviewResponse)
    async def text_review(request: TextReviewRequest) -> TextReviewResponse:
        review = review_text(request.text)
        return TextReviewResponse(
            original=review.original,
            repaired=review.repaired,
            changed=review.changed,
            issues=[
                TextReviewIssue(
                    code=issue.code,
                    message=issue.message,
                    count=issue.count,
                )
                for issue in review.issues
            ],
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
        text_review = review_text(request.text)
        try:
            result = await run_in_threadpool(
                speech_service.synthesize,
                text_review.repaired,
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
                "X-BhashaVox-Text-Corrected": str(text_review.changed).lower(),
            },
        )

    def job_response(job: SpeechJobSnapshot) -> SpeechJobResponse:
        return SpeechJobResponse(
            id=job.id,
            status=job.status,
            text_corrected=job.text_corrected,
            chunks_completed=job.chunks_completed,
            chunks_total=job.chunks_total,
            segment_count=job.segment_count,
            audio_url=(
                f"/api/v1/speech/jobs/{job.id}/audio"
                if job.status == "completed"
                else None
            ),
            error=job.error,
        )

    @app.post(
        "/api/v1/speech/jobs",
        response_model=SpeechJobResponse,
        status_code=202,
    )
    async def create_speech_job(request: SpeechRequest) -> SpeechJobResponse:
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
        text_review = review_text(request.text)
        job = job_manager.submit(
            text_review.repaired,
            request.language,
            request.voice,
            request.speed,
            text_corrected=text_review.changed,
        )
        return job_response(job)

    @app.get(
        "/api/v1/speech/jobs/{job_id}",
        response_model=SpeechJobResponse,
    )
    async def get_speech_job(job_id: str) -> SpeechJobResponse:
        job = job_manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="speech job was not found")
        return job_response(job)

    @app.get("/api/v1/speech/jobs/{job_id}/audio")
    async def get_speech_job_audio(job_id: str) -> Response:
        job = job_manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="speech job was not found")
        if job.status != "completed" or job.audio is None:
            raise HTTPException(status_code=409, detail="speech job is not complete")
        return Response(
            content=job.audio,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="bhashavox.wav"',
                "X-BhashaVox-Segments": str(job.segment_count or 0),
                "X-BhashaVox-Text-Corrected": str(job.text_corrected).lower(),
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
