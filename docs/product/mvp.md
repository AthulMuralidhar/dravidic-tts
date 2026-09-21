# MVP definition

## Primary user story

As a user, I can paste English, Tamil, Malayalam, or mixed native-script text,
generate speech locally, listen in the browser, and download the WAV file.

## Included in the first runnable slice

- A large Unicode-safe paste area.
- Auto-detection of Latin, Tamil, and Malayalam script.
- Explicit English, Tamil, or Malayalam override.
- Script-aware segmentation for mixed input.
- A CPU-friendly eSpeak NG speech provider.
- Browser playback and WAV download.
- A capabilities endpoint so the UI reflects the configured provider.
- A health endpoint for local Docker and future hosting.
- Request limits and useful validation messages.
- Containerized startup with Docker Compose.
- Unit/API tests that run without speech models or a GPU.

## Deferred deliberately

- Tanglish/Manglish transliteration (after a preview/edit interaction is
  designed and IndicXlit is evaluated).
- Voice cloning or uploaded reference audio.
- Accounts, saved history, billing, and analytics.
- Public anonymous deployment protections.
- Background queues and distributed workers.
- MP3/Opus output.
- A bundled Indic Parler-TTS image before hardware benchmarks.

## Initial API contract

### `GET /api/v1/health`

Returns service status, version, and configured provider readiness.

### `GET /api/v1/capabilities`

Returns supported languages, voices, formats, input limit, and whether mixed
native scripts are supported by the orchestration layer.

### `POST /api/v1/speech`

JSON request:

```json
{
  "text": "Hello. வணக்கம். നമസ്കാരം.",
  "language": "auto",
  "voice": null,
  "speed": 1.0,
  "format": "wav"
}
```

Successful response: `audio/wav` with a download filename. Validation errors
use standard JSON problem details and never echo more text than necessary.

## MVP acceptance checks

1. `docker compose up --build` starts a healthy service.
2. The UI loads at `http://localhost:8000`.
3. Each of the three native scripts produces playable WAV output.
4. A mixed-script example produces one combined output.
5. Blank or oversized text receives a clear error.
6. Automated tests pass without a network connection or model download.

