# BhashaVox

BhashaVox is a local-first, open-source web app that turns pasted text into
downloadable speech. The first-class languages are English, Tamil, and
Malayalam, including mixed-script documents.

The first runnable MVP is in place. Research, decisions, and session handoffs
are kept in [`docs/`](docs/) so the work remains easy to resume.

## Product direction

- Paste text in English, Tamil, Malayalam, or a mixture of the three.
- Preview the generated speech in the browser.
- Download a WAV file.
- Run locally with Docker.
- Keep the synthesis engine replaceable so a simple deployment can use a
  hosted provider later without changing the UI or API.

## Run locally

With Docker Desktop or Docker Engine running:

```bash
docker compose up --build
```

Then open <http://localhost:8000>. The starter image uses eSpeak NG, so it is
CPU-only and does not need model credentials or a GPU.

See [`docs/operations/local-and-deployment.md`](docs/operations/local-and-deployment.md)
for non-Docker development, configuration, verification, and deployment notes.

## Architecture and research

- [MVP definition](docs/product/mvp.md)
- [Local-first provider architecture](docs/adr/0001-local-first-provider-architecture.md)
- [TTS model and transliteration research](docs/research/tts-landscape.md)
- [Current session handoff](docs/session-notes/2026-09-21.md)

The initial provider is intentionally modest but dependable. AI4Bharat Indic
Parler-TTS is the planned high-quality provider after local CPU/GPU benchmarks.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
