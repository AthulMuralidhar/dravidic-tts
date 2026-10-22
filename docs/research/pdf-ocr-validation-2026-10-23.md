# Test PDF extraction and OCR validation

Research date: 2026-10-23

## Input inspected

The local test document `Nishayude_Ponnumon_Kambi_Novel.pdf` contains 83
letter-sized pages and is approximately 734 KB. The PDF reports AES encryption
with an empty-password-readable document and restrictive print/copy metadata.
Every page has an embedded text layer.

## Finding: the embedded text is unusable for speech

Direct extraction returns approximately 200,000 characters, but many Malayalam
letters are replaced by null characters and several vowel signs are stored in
visual rather than logical order. The rendered pages are visually legible,
which means the damage is in the PDF character mapping rather than the visible
page image.

Sending this embedded layer directly to text-to-speech would recreate the
earlier cryptic and unintelligible result. Automatic Unicode reordering cannot
recover glyphs that were replaced by null characters. This document therefore
requires OCR from rendered page images before speech synthesis.

## Processing decision

- Render each page at 300 DPI with PDFium.
- Run Tesseract using Malayalam plus English language data.
- Remove repeated site headers, footers, and isolated page numbers.
- Apply the existing automatic Malayalam repair stage after OCR.
- Group cleaned text into parts of roughly 4,000 characters without splitting
  a page unless a single page exceeds the limit.
- Write every completed WAV and an updated JSON manifest atomically so an
  interrupted overnight run can resume without regenerating completed parts.
- Generate a static HTML listening page and serve the output directory on the
  LAN while synthesis continues.

## Limitations to evaluate from the first run

Tesseract prevents the catastrophic missing-glyph problem but may still make
word-level Malayalam recognition errors. Speech tonality and pronunciation
remain properties of the Indic Parler-TTS model. The first completed parts
must be listened to before treating the entire book conversion as acceptable.
