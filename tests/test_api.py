import io
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


def test_rejects_blank_and_oversized_text() -> None:
    with make_client(max_characters=5) as client:
        blank = client.post("/api/v1/speech", json={"text": "   "})
        oversized = client.post("/api/v1/speech", json={"text": "sixsix"})

    assert blank.status_code == 422
    assert oversized.status_code == 413
