# PDF-to-audio research and delivery plan

Research date: 2026-09-22

## Feasibility

Converting an entire PDF to speech is feasible, but “PDF” covers three
different inputs:

1. A digitally generated PDF with extractable Unicode text.
2. A scan containing only page images.
3. A hybrid scan with an existing, sometimes inaccurate OCR text layer.

The first type can use direct extraction. The second requires page rendering
and OCR. The third should compare the embedded text with OCR quality signals
instead of blindly trusting either source. All paths must pass through the
existing BhashaVox Unicode repair, language segmentation, chunking, and speech
job pipeline.

## Recommended open-source components

### Direct text extraction: pypdf

Use `pypdf` first for digitally generated PDFs. It is pure Python,
BSD-3-Clause licensed, and supports page-level text and metadata extraction.
Its documentation explicitly says it is not OCR software and cannot extract
text from page images. It also explains that PDFs lack a semantic document
layer, so paragraphs, columns, headers, footers, tables, and reading order are
not unambiguous.

The extractor must apply resource limits. The pypdf documentation reports that
parsing a roughly 300 MB uncompressed content stream has required about 10 GB
RAM in an observed case. Its current security defaults limit several decoded
filter outputs, but BhashaVox should still enforce upload size, page count,
per-page processing time, and extracted-content limits.

### Scanned-page rendering: pypdfium2

Tesseract cannot read PDF input directly, so scanned pages first need rendering
to images. Prefer `pypdfium2` over PyMuPDF for this project: pypdfium2 is
offered under Apache-2.0/BSD-3-Clause terms, while its bundled PDFium and
dependencies require their notices to be distributed. License files from wheel
builds must be retained in packaged distributions.

### OCR: Tesseract

Tesseract is Apache-2.0 licensed and provides trained data for English (`eng`),
Tamil (`tam`), and Malayalam (`mal`). Run it out of process on rendered page
images so failures and timeouts are isolated. OCR should be selective rather
than universal: direct extraction retains font/encoding information and avoids
OCR confusions on clean digital PDFs.

## Proposed local pipeline

```text
PDF upload
  -> validate signature, size, page count, and encryption state
  -> create durable document job
  -> inspect each page
     -> extract Unicode text when usable
     -> otherwise render page and OCR with eng+tam+mal
  -> remove repeated headers/footers and repair line-break hyphenation
  -> run automatic Unicode/copy-paste repair
  -> preserve original, extracted, and repaired text per page
  -> segment by language and split at sentence boundaries
  -> queue speech chunks with page/chapter progress
  -> persist each completed audio chunk
  -> assemble chapter audio and expose downloads
```

The extracted/repaired text preview is diagnostic, not a required correction
step. The service remains responsible for automatic repair before audio.

## Product behavior

- The user uploads one PDF and chooses Auto, English, Tamil, or Malayalam.
- The UI first reports pages discovered, extraction method, and warnings.
- Progress separates extraction/OCR from speech generation.
- Page/chapter progress survives refresh, Wi-Fi loss, and container restart.
- Failed pages can be retried without regenerating successful pages.
- Repeated headers, footers, and page numbers are suppressed when confidently
  detected; uncertain removals are recorded as warnings.
- Password-protected PDFs are rejected in the first version with a clear error.
- User-provided documents and generated audio remain local by default.

## Storage and output decisions

The current in-memory speech-job store is insufficient for book-sized work.
Before PDF synthesis, add SQLite job metadata plus a mounted workspace for the
uploaded PDF, page text, audio chunks, and final outputs. Use random internal
IDs rather than filenames for paths and define an explicit local retention or
delete action.

Classic WAV is suitable for chunks but becomes inefficient and has practical
size limits for whole books. The first slice should offer per-chapter WAV files
and a ZIP. A later audiobook export can add M4B or another compressed format
after codec and distribution licensing are reviewed.

## Delivery stages

1. **Extraction preview:** upload a bounded, digitally generated PDF; extract
   page text with pypdf; run automatic repair; show page counts and warnings.
2. **Durable document jobs:** persist job state and extracted text so restarts
   do not lose multi-hour work.
3. **Speech by page/chapter:** reuse the current single-worker neural queue,
   persist every completed chunk, and assemble chapter WAV downloads.
4. **Scanned PDFs:** render low-text pages with pypdfium2 and OCR them using
   Tesseract `eng+tam+mal` with per-page timeouts.
5. **Audiobook packaging:** add chapter metadata and a compressed audiobook
   format after the codec choice is reviewed.

The current CPU neural backend is the main throughput blocker. PDF ingestion can
be built now, but a book will not be practical until AMD-compatible local
acceleration, a faster/quantized CPU runtime, or optional hosted inference is
available.

## Acceptance tests for the first slice

- A small English/Tamil/Malayalam Unicode PDF produces a page-by-page preview.
- A scanned-only PDF is identified as requiring OCR instead of returning empty
  speech.
- Oversized, malformed, and encrypted PDFs fail with clear bounded errors.
- Extracted Malayalam passes through the automatic repair pipeline.
- Headers and page numbers do not appear repeatedly in synthesized text when
  the detector has high confidence.
- Restarting the service does not lose a durable document job.
- Speech chunks already completed are not regenerated during retry.

## Sources

- [pypdf text extraction documentation](https://github.com/py-pdf/pypdf/blob/main/docs/user/extract-text.md)
- [pypdf security limits](https://pypdf.readthedocs.io/en/6.6.1/user/security.html)
- [pypdf license FAQ](https://github.com/py-pdf/pypdf/blob/main/docs/meta/faq.md)
- [FastAPI file-upload documentation](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Tesseract installation and Apache-2.0 license](https://tesseract-ocr.github.io/tessdoc/Installation.html)
- [Tesseract language data](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)
- [Tesseract input formats](https://tesseract-ocr.github.io/tessdoc/InputFormats.html)
- [pypdfium2 licensing](https://github.com/pypdfium2-team/pypdfium2/blob/main/README.md)
