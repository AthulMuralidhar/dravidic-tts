import io
import time
import wave

from fastapi.testclient import TestClient

from bhashavox.config import Settings
from bhashavox.main import create_app
from bhashavox.providers.espeak import EspeakProvider
from bhashavox.providers.tone import ToneProvider


def make_client(max_characters: int = 100) -> TestClient:
    app = create_app(
        settings=Settings(provider="tone", max_characters=max_characters),
        provider=ToneProvider(),
    )
    return TestClient(app)


def test_health_and_capabilities() -> None:
    with make_client() as client:
        health = client.get("/api/v1/health")
        capabilities = client.get("/api/v1/capabilities")

    assert health.json()["status"] == "ok"
    assert health.json()["provider"] == "tone"
    assert capabilities.json()["languages"] == ["en", "ta", "ml"]
    assert capabilities.json()["supports_mixed_native_scripts"] is True


def test_health_is_unavailable_when_provider_is_not_ready() -> None:
    app = create_app(
        settings=Settings(provider="espeak"),
        provider=EspeakProvider(executable="definitely-not-installed"),
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_browser_ui_is_served() -> None:
    with make_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "BhashaVox" in response.text
    assert "தமிழ்" in response.text
    assert "മലയാളം" in response.text
    assert "tones, not spoken" in response.text


def test_speech_returns_combined_wav() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/speech",
            json={"text": "Hello வணக்கம் നമസ്കാരം", "language": "auto"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["x-bhashavox-segments"] == "3"
    with wave.open(io.BytesIO(response.content), "rb") as audio:
        assert audio.getnframes() > 0


def test_background_speech_job_survives_separate_status_requests() -> None:
    with make_client() as client:
        created = client.post(
            "/api/v1/speech/jobs",
            json={"text": "രാ?തി", "language": "ml"},
        )

        assert created.status_code == 202
        job = created.json()
        assert job["status"] in {"queued", "running", "completed"}
        assert job["text_corrected"] is True

        deadline = time.monotonic() + 2
        while job["status"] not in {"completed", "failed"}:
            assert time.monotonic() < deadline
            time.sleep(0.01)
            job = client.get(f"/api/v1/speech/jobs/{job['id']}").json()

        assert job["status"] == "completed"
        assert job["chunks_completed"] == 1
        assert job["chunks_total"] == 1
        assert job["audio_url"] == f"/api/v1/speech/jobs/{job['id']}/audio"
        audio = client.get(job["audio_url"])

    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/wav")
    assert audio.headers["x-bhashavox-text-corrected"] == "true"
    with wave.open(io.BytesIO(audio.content), "rb") as generated:
        assert generated.getnframes() > 0


def test_background_speech_job_reports_missing_and_incomplete_audio() -> None:
    with make_client() as client:
        missing = client.get("/api/v1/speech/jobs/not-a-job")
        missing_audio = client.get("/api/v1/speech/jobs/not-a-job/audio")

    assert missing.status_code == 404
    assert missing_audio.status_code == 404


def test_text_review_returns_safe_repairs_and_ambiguous_warnings() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/text/review",
            json={"text": "േവഗം രാ?തി"},
        )

    assert response.status_code == 200
    assert response.json()["repaired"] == "വേഗം രാത്രി"
    assert response.json()["changed"] is True
    assert [issue["code"] for issue in response.json()["issues"]] == [
        "malayalam-prebase-order",
        "restored-malayalam-glyph",
    ]


def test_speech_corrects_safe_copy_paste_damage_before_audio() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/speech",
            json={"text": "േവഗം", "language": "ml"},
        )

    assert response.status_code == 200
    assert response.headers["x-bhashavox-text-corrected"] == "true"


def test_speech_automatically_restores_missing_malayalam_glyphs() -> None:
    with make_client() as client:
        response = client.post(
            "/api/v1/speech",
            json={"text": "രാ?തി", "language": "ml"},
        )

    assert response.status_code == 200
    assert response.headers["x-bhashavox-text-corrected"] == "true"


def test_rejects_blank_and_oversized_text() -> None:
    with make_client(max_characters=5) as client:
        blank = client.post("/api/v1/speech", json={"text": "   "})
        oversized = client.post("/api/v1/speech", json={"text": "sixsix"})

    assert blank.status_code == 422
    assert oversized.status_code == 413
