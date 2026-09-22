# Local operation and future deployment

## Recommended local path: Docker Compose

Prerequisites: Docker Desktop (Windows/macOS) or Docker Engine with Compose
(Linux).

```bash
docker compose build dravidic-tts
docker compose --profile setup run --rm hf-login
docker compose up -d dravidic-tts
```

Accept the access conditions for `ai4bharat/indic-parler-tts` in the same
Hugging Face account before login. Enter a read token only in the local login
prompt; never put it in source files, Compose configuration, image build
arguments, or chat. Open <http://localhost:8000>. The first neural request
downloads the gated checkpoint into the persistent `hf-cache` Docker volume.
Later container rebuilds reuse that cache.

Stop it with:

```bash
docker compose down
```

To expose another host port, copy `.env.example` to `.env` and change
`DRAVIDIC_TTS_BIND_PORT`.

## Local development without Docker

Python 3.11 or newer is required. The host dependencies for Indic Parler are
intentionally managed by `Dockerfile.neural`. Direct host development uses the
smaller eSpeak or tone provider unless neural dependencies are installed
separately. eSpeak NG must be available as `espeak-ng` on `PATH` when selected.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:DRAVIDIC_TTS_PROVIDER = "espeak"
.\.venv\Scripts\python.exe -m uvicorn dravidic_tts.main:app --reload
```

For UI/API development when eSpeak NG is unavailable, use
`DRAVIDIC_TTS_PROVIDER=tone`. It generates test tones, not spoken words.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
node --check src/dravidic_tts/static/app.js
```

Health and API documentation:

- <http://localhost:8000/api/v1/health>
- <http://localhost:8000/docs>

## Container deployment later

Dravidic TTS currently retains speech-job state and completed audio in process
memory. A basic single-replica container platform needs:

1. build `Dockerfile` from the repository root;
2. expose container port `8000`;
3. use `/api/v1/health` as the health check;
4. provide the gated-model credential as a secret and mount a model cache;
5. set environment variables if defaults need changing.

The browser submits a background job, polls its status, and downloads the WAV
when complete. A refresh or brief network interruption is safe because the
browser remembers the active job ID. A container restart still loses in-memory
jobs and audio. Do not scale horizontally until job metadata and generated
files move to shared durable storage and requests are routed consistently.

Required production edge controls for a public deployment:

- HTTPS at the platform or reverse proxy;
- request-body and rate limits;
- authentication if the service is not intended to be public;
- container CPU/memory limits;
- access logs with pasted text excluded;
- an explicit retention policy if saved history is ever added.

Do not add Uvicorn workers blindly when a heavyweight in-process ML provider
is enabled: each worker may load its own copy of the model. A quality-model
deployment will likely use a small web container plus a separately sized
inference worker or endpoint, while retaining the same provider interface.

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `DRAVIDIC_TTS_PROVIDER` | Compose: `indic-parler` | Speech backend (`indic-parler`, `espeak`; `tone` is testing only) |
| `DRAVIDIC_TTS_MAX_CHARACTERS` | `5000` | Per-request Unicode character limit |
| `DRAVIDIC_TTS_HOST` | `0.0.0.0` | Bind address outside Compose |
| `DRAVIDIC_TTS_PORT` | `8000` | Service port outside Compose |
| `DRAVIDIC_TTS_BIND_PORT` | `8000` | Host-side port used by Compose |
| `DRAVIDIC_TTS_PARLER_MODEL` | `ai4bharat/indic-parler-tts` | Optional neural model ID override |

## Current-machine note

On 2026-09-22 the CPU-only neural image, gated checkpoint download, Malayalam
synthesis, resumable job API, LAN browser access, and persistent model cache
were verified on Docker Desktop. A warm short Malayalam request took 41.9
seconds. Long-form latency and listening quality remain under evaluation.
