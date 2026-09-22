# MVP definition

## Primary user story

As a user, I can paste English, Tamil, Malayalam, or mixed native-script text,
generate speech locally, listen in the browser, and download the WAV file.

## Included in the first runnable slice

- A large Unicode-safe paste area.
- Auto-detection of Latin, Tamil, and Malayalam script.
- Explicit English, Tamil, or Malayalam override.
- Script-aware segmentation for mixed input.
- A CPU-only AI4Bharat Indic Parler-TTS speech provider with English, Tamil,
  and Malayalam voices.
- Browser playback and WAV download.
- Resumable background generation with queued/running/completed/failed states.
- Sentence-aware chunking and visible per-chunk progress for long text.
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
- Durable background queues and distributed workers; the local MVP queue is
  in memory and runs one neural job at a time.
- MP3/Opus output.
- Multi-replica deployment before durable job and audio storage exists.

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

The browser uses the reconnect-safe job contract instead:

- `POST /api/v1/speech/jobs` creates a job and immediately returns HTTP 202.
- `GET /api/v1/speech/jobs/{id}` returns state and chunk progress.
- `GET /api/v1/speech/jobs/{id}/audio` returns the completed WAV.

The direct speech endpoint remains available for short API clients.

## MVP acceptance checks

1. `docker compose up --build` starts a healthy service.
2. The UI loads at `http://localhost:8000`.
3. Each of the three native scripts produces playable WAV output.
4. A mixed-script example produces one combined output.
5. Blank or oversized text receives a clear error.
6. Automated tests pass without a network connection or model download.
