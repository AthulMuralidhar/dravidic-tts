# ADR 0002: Rename the project to Dravidic TTS

- Status: accepted
- Date: 2026-09-23

## Context

The working name `BhashaVox` conflicts directly with an active commercial web
application at `bhashavox.com`. That product already offers overlapping
features including multilingual text-to-speech, document processing, Indian
language support, voice cloning, and downloadable audio. Continuing to use the
same name would create user confusion and avoidable naming risk.

Candidate searches were performed for `AksharaVox`, `t2v-south-india`,
`dravidic-tts`, and `dravidian-tts`. `t2v-south-india` was rejected because T2V
is commonly read as “text-to-video.” `Dravidian TTS` is descriptive but already
appears frequently as a category and within existing model identifiers.
`Dravidic` is a valid, less-common alternative adjective for the Dravidian
language family, and no obvious indexed exact-name collision was found for
`dravidic-tts` during this screen.

This is a practical open-source naming screen, not trademark or legal
clearance. Package, domain, organization, and trademark availability must be
rechecked before a public launch.

## Decision

Rename the project as follows:

- user-facing name: **Dravidic TTS**;
- Python distribution and container image: `dravidic-tts`;
- Python import package: `dravidic_tts`;
- configuration prefix: `DRAVIDIC_TTS_`;
- API response-header prefix: `X-Dravidic-TTS-`;
- browser storage prefix: `dravidic-tts`.

The existing repository directory is not renamed because it is managed by the
current Codex workspace. Historical session notes remain unchanged so the
project record accurately reflects the name used when those sessions occurred.

## Consequences

- Source modules, tests, Docker configuration, current documentation, UI copy,
  generated filenames, and environment variables must be renamed together.
- Existing `BHASHAVOX_*` environment variables will no longer be the preferred
  interface. Because the project is pre-release, a clean rename is favored over
  carrying permanent compatibility aliases.
- The Docker model-cache volume must be preserved so renaming the service does
  not force another multi-gigabyte model download.
- English remains a supported language even though the primary product focus is
  Tamil, Malayalam, and future Dravidian-language expansion.

## Evidence reviewed

- [Existing BhaShaVox website](https://www.bhashavox.com/)
- [Existing BhaShaVox speech-generation product](https://www.bhashavox.com/product/tts)
- [“Dravidic” listed as an alternative to “Dravidian”](https://www.collinsdictionary.com/dictionary/english/dravidian)
- [AI4Bharat Dravidian-language TTS research](https://ai4bharat.iitm.ac.in/areas/tts/)
