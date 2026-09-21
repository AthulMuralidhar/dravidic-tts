# Local operation and future deployment

## Recommended local path: Docker Compose

Prerequisites: Docker Desktop (Windows/macOS) or Docker Engine with Compose
(Linux).

```bash
docker compose up --build
```

Open <http://localhost:8000>. The container includes eSpeak NG and needs no
GPU, cloud account, model download, volume, or database.

Stop it with:

```bash
docker compose down
```

To expose another host port, copy `.env.example` to `.env` and change
`BHASHAVOX_BIND_PORT`.

## Local development without Docker

Python 3.11 or newer is required. eSpeak NG must be installed and available as
`espeak-ng` on `PATH` for actual speech.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:BHASHAVOX_TTS_PROVIDER = "espeak"
.\.venv\Scripts\python.exe -m uvicorn bhashavox.main:app --reload
```

For UI/API development when eSpeak NG is unavailable, use
`BHASHAVOX_TTS_PROVIDER=tone`. It generates test tones, not spoken words.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
node --check src/bhashavox/static/app.js
```

Health and API documentation:

- <http://localhost:8000/api/v1/health>
- <http://localhost:8000/docs>

## Container deployment later

BhashaVox is a stateless HTTP container. A basic container platform needs only:

1. build `Dockerfile` from the repository root;
2. expose container port `8000`;
3. use `/api/v1/health` as the health check;
4. set environment variables if defaults need changing.

The generated audio is streamed in the response and is not stored on disk.
Consequently, the starter service needs no persistent volume and can be
replaced or scaled horizontally. eSpeak synthesis is CPU-only; begin with one
worker and measure concurrent load before adding workers.

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
| `BHASHAVOX_TTS_PROVIDER` | `espeak` | Speech backend (`espeak`; `tone` is testing only) |
| `BHASHAVOX_MAX_CHARACTERS` | `5000` | Per-request Unicode character limit |
| `BHASHAVOX_HOST` | `0.0.0.0` | Bind address outside Compose |
| `BHASHAVOX_PORT` | `8000` | Service port outside Compose |
| `BHASHAVOX_BIND_PORT` | `8000` | Host-side port used by Compose |

## Current-machine note

On 2026-09-21 the Docker CLI and Compose plugin were present, but the Docker
engine was not running. The image definition and Compose configuration can be
validated statically; an end-to-end container smoke test requires starting
Docker Desktop first.

