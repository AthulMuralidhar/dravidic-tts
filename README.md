# BhashaVox

BhashaVox is a local-first, open-source web app that turns pasted text into
downloadable speech. The first-class languages are English, Tamil, and
Malayalam, including mixed-script documents.

The project is at the beginning of its MVP. Research, decisions, and session
handoffs are kept in [`docs/`](docs/) so the work remains easy to resume.

## Product direction

- Paste text in English, Tamil, Malayalam, or a mixture of the three.
- Preview the generated speech in the browser.
- Download a WAV file.
- Run locally with Docker.
- Keep the synthesis engine replaceable so a simple deployment can use a
  hosted provider later without changing the UI or API.

## Status

Repository foundation created. See
[`docs/session-notes/2026-09-21.md`](docs/session-notes/2026-09-21.md) for the
current handoff.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
