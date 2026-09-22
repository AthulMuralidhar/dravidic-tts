# ADR 0001: Local-first provider architecture

- Status: Accepted
- Date: 2026-09-21

## Context

Dravidic TTS must run locally first, including on a machine where no NVIDIA GPU
has been detected. It must also be straightforward to deploy later. The best
quality candidate model is materially heavier than the web application, has
separate access conditions, and may need GPU acceleration in production.

Coupling HTTP handling directly to one model would make local startup fragile
and later deployment expensive to change.

## Decision

Build one stateless FastAPI service with a speech-provider interface.

The first implementation will include:

- an eSpeak NG provider that runs locally on CPU and makes the full product
  flow usable;
- a deterministic in-process test provider for tests;
- a future Indic Parler-TTS provider behind the same contract;
- configuration exclusively through environment variables;
- generated audio returned directly to the caller instead of persisted by
  default;
- a static web UI served by the same process for the MVP.

The container uses Python 3.11 because current ML/audio packages are more
likely to support it than the host's Python 3.13. The initial image is CPU-only
and small. A separate optional ML image/profile may add PyTorch and model
weights later.

## Local and deployed topology

```text
Browser
  -> Dravidic TTS HTTP service
       -> text validation and script-aware segmentation
       -> configured SpeechProvider
            -> eSpeak NG (local/CPU MVP)
            -> Indic Parler-TTS (quality profile, planned)
            -> hosted provider adapter (optional future deployment)
       <- WAV bytes streamed to browser
```

The same container contract works on a laptop, Docker Compose, or a container
host. A deployment can replace only `DRAVIDIC_TTS_PROVIDER` and provider
credentials/endpoints while keeping the public API and browser unchanged.

## Deployment constraints

- Bind to `0.0.0.0` inside the container.
- Provide `/api/v1/health` for container and platform health checks.
- Do not require local filesystem persistence for generated audio.
- Log to stdout/stderr.
- Keep secrets out of the image and repository.
- Pin application dependencies and use a reproducible Docker build.
- Put reverse-proxy TLS, authentication, quotas, and request-size policy at
  the platform edge when the app becomes public.

## Consequences

Positive:

- The complete user flow can run without a GPU or cloud account.
- Tests do not download model weights.
- A future hosted or GPU-backed provider does not require a UI rewrite.
- Stateless requests simplify deployment and scaling.

Trade-offs:

- eSpeak output is functional rather than natural.
- Mixed-language stitching may create audible voice changes.
- Long jobs will eventually need a queue or worker, but adding one before
  measuring real latency would add unnecessary operational complexity.
- Provider capabilities differ, so the API must advertise available voices
  and controls instead of promising that every engine supports everything.
