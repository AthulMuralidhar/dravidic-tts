"""In-memory background speech jobs for resilient browser generation."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Literal
from uuid import uuid4

from dravidic_tts.language import LanguageChoice
from dravidic_tts.providers.base import ProviderUnavailable
from dravidic_tts.service import SpeechService

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class SpeechJobSnapshot:
    id: str
    status: JobStatus
    text_corrected: bool
    chunks_completed: int = 0
    chunks_total: int | None = None
    segment_count: int | None = None
    audio: bytes | None = None
    error: str | None = None


@dataclass(slots=True)
class _SpeechJob:
    id: str
    status: JobStatus
    text_corrected: bool
    chunks_completed: int = 0
    chunks_total: int | None = None
    segment_count: int | None = None
    audio: bytes | None = None
    error: str | None = None

    def snapshot(self) -> SpeechJobSnapshot:
        return SpeechJobSnapshot(
            id=self.id,
            status=self.status,
            text_corrected=self.text_corrected,
            chunks_completed=self.chunks_completed,
            chunks_total=self.chunks_total,
            segment_count=self.segment_count,
            audio=self.audio,
            error=self.error,
        )


class SpeechJobManager:
    """Run one model generation at a time and retain completed audio in memory."""

    def __init__(self, service: SpeechService, retained_jobs: int = 10) -> None:
        self._service = service
        self._retained_jobs = retained_jobs
        self._jobs: dict[str, _SpeechJob] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="dravidic-tts-speech",
        )

    def submit(
        self,
        text: str,
        language: LanguageChoice,
        voice: str | None,
        speed: float,
        *,
        text_corrected: bool,
    ) -> SpeechJobSnapshot:
        job = _SpeechJob(
            id=uuid4().hex,
            status="queued",
            text_corrected=text_corrected,
        )
        with self._lock:
            self._discard_old_jobs()
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id, text, language, voice, speed)
        return job.snapshot()

    def get(self, job_id: str) -> SpeechJobSnapshot | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.snapshot() if job else None

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(
        self,
        job_id: str,
        text: str,
        language: LanguageChoice,
        voice: str | None,
        speed: float,
    ) -> None:
        self._update(job_id, status="running")
        try:
            result = self._service.synthesize(
                text,
                language,
                voice,
                speed,
                progress_callback=lambda completed, total: self._update_progress(
                    job_id,
                    completed,
                    total,
                ),
            )
        except (ValueError, ProviderUnavailable) as exc:
            self._update(job_id, status="failed", error=str(exc))
        except Exception:
            logger.exception("Unexpected speech job failure", extra={"job_id": job_id})
            self._update(
                job_id,
                status="failed",
                error="Speech generation failed unexpectedly.",
            )
        else:
            self._update(
                job_id,
                status="completed",
                audio=result.audio,
                segment_count=result.segment_count,
            )

    def _update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        audio: bytes | None = None,
        segment_count: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.audio = audio
            job.segment_count = segment_count
            job.error = error

    def _update_progress(self, job_id: str, completed: int, total: int) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.chunks_completed = completed
            job.chunks_total = total

    def _discard_old_jobs(self) -> None:
        removable = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {"completed", "failed"}
        ]
        while len(self._jobs) >= self._retained_jobs and removable:
            del self._jobs[removable.pop(0)]
