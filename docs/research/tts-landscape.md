# TTS landscape for English, Tamil, and Malayalam

Research date: 2026-09-21

This document records the evidence behind BhashaVox's initial speech-engine
strategy. It is a snapshot, not a permanent claim: model cards, access terms,
weights, and inference support can change.

## Requirements used for comparison

The MVP needs:

- English, Tamil, and Malayalam;
- local inference without requiring a paid API;
- an open license that does not prevent future deployment or commercial use;
- acceptable CPU behavior for a functional fallback;
- a higher-quality path for machines or deployments with suitable hardware;
- a clean way to process mixed-script input;
- no required voice cloning or user-supplied voice recording.

## Candidate comparison

| Candidate | Language fit | License | Operational fit | Decision |
| --- | --- | --- | --- | --- |
| AI4Bharat Indic Parler-TTS | English, Tamil, and Malayalam are officially supported | Apache-2.0 | 0.9B parameters; style and named-speaker controls; gated Hugging Face download; no hosted inference provider on the model card | Preferred high-quality local provider |
| AI4Bharat IndicF5 | Tamil and Malayalam, but English is not in its 11-language list | MIT on the model card | 0.4B parameters; requires reference audio plus its transcript; gated download; voice-cloning consent obligations | Research/advanced provider, not the MVP default |
| Meta MMS-TTS | Separate English, Tamil, and Malayalam checkpoints | CC-BY-NC-4.0 | Roughly 145 MB per listed Tamil checkpoint; simple Transformers integration; separate models complicate mixed text | Excluded from the default due to non-commercial restriction |
| AI4Bharat Indic-TTS | Tamil and Malayalam among 13 Indian languages | Repository is open source; individual model/data terms must be checked before shipping | Older training/inference stack; no single English/Tamil/Malayalam model path | Useful baseline, not first implementation |
| eSpeak NG | English, Tamil, and Malayalam voices are available in typical distributions | GPL-3.0-or-later executable used out of process | Small, CPU-friendly, deterministic, and easy to containerize; speech is robotic | Functional local fallback and CI provider |

## Preferred model: Indic Parler-TTS

The [official model card](https://huggingface.co/ai4bharat/indic-parler-tts)
states that:

- the model is Apache-2.0 licensed;
- it is a 0.9B-parameter model;
- it officially supports 20 Indic languages plus English, including Tamil and
  Malayalam;
- it provides 69 voices, with recommended voices for English, Malayalam, and
  Tamil;
- style prompts can control pace, pitch, expressiveness, recording quality,
  and related characteristics;
- its files require accepting Hugging Face access conditions; and
- it is not currently served by a Hugging Face inference provider.

Those properties make it a strong local-quality target but a poor hard
dependency for first boot. BhashaVox therefore exposes a provider interface:
the application can start with eSpeak NG, while Indic Parler-TTS can be added
as an optional image/profile once its exact CPU performance and memory use are
measured on target hardware.

The card says language is inferred from the prompt, but it does not establish
that arbitrary code-switched paragraphs retain one voice and consistently
pronounce every span. We should test rather than assume this. Our service will
segment clearly different Unicode scripts before synthesis, while keeping the
segmentation policy replaceable.

## IndicF5

The [IndicF5 model card](https://huggingface.co/ai4bharat/IndicF5) lists Tamil
and Malayalam among 11 Indian languages, uses an MIT license, and describes a
0.4B-parameter model. English is not listed. Inference requires the target
text, a reference audio clip, and a transcript of that clip. The card also
explicitly prohibits cloning voices without permission.

This may become valuable for a consent-based custom-voice feature, but it adds
product, safety, storage, and deployment complexity unrelated to paste-to-
speech. It is deliberately out of MVP scope.

## MMS-TTS

Meta's [MMS documentation](https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md)
describes TTS coverage across more than 1,100 languages. The
[Tamil model page](https://huggingface.co/facebook/mms-tts-tam) exposes a
straightforward Transformers API and a relatively small language-specific
checkpoint. However, the weights are CC-BY-NC-4.0. “Non-commercial” is a
future deployment constraint, so MMS must not be the default engine even
though it is useful for experiments.

## Romanized Tamil and Malayalam

Latin script is ambiguous: `amma`, `palli`, or an English-looking token cannot
reliably identify Tamil versus Malayalam without user intent and context.
Automatic script detection alone therefore cannot solve Tanglish or Manglish.

The [AI4Bharat IndicXlit project](https://github.com/AI4Bharat/IndicXlit) is a
roughly 11M-parameter transliteration model covering 21 languages, including
Tamil and Malayalam. Its application documentation supports Roman-to-native
and native-to-Roman conversion. The repository is MIT licensed, while older
related model releases have had different Creative Commons terms; exact
artifact licensing must be rechecked before bundling weights.

Planned behavior:

1. Native English, Tamil, and Malayalam scripts work without transliteration.
2. When users explicitly choose “Tanglish” or “Manglish,” a transliteration
   preview is shown before speech generation.
3. The user can edit or bypass the preview because names and code-mixed words
   are inherently ambiguous.
4. No Latin sentence is silently rewritten based only on a guess.

## Experiments still required

- Benchmark eSpeak NG cold start, latency, and intelligibility for all three
  languages.
- Benchmark Indic Parler-TTS on CPU and at least one GPU configuration.
- Test single-language and mixed-script paragraphs with native reviewers.
- Check whether one selected Parler voice stays acceptably consistent across
  language boundaries.
- Measure chunk size versus latency and audible discontinuities.
- Evaluate IndicXlit specifically on colloquial Tanglish and Manglish, not
  only formal benchmark words.
- Re-check all licenses immediately before distributing model weights in an
  image or hosted service.

## Local prototype findings — 2026-09-21

The first eSpeak NG end-to-end test was rejected. Although the provider
generated valid WAV files and supported the requested language codes, its
Malayalam was robotic, frequently unintelligible, and not suitable as a user-
facing fallback. It may remain useful only for automated plumbing checks. The
UI now labels diagnostic tone mode explicitly, and eSpeak must also be labeled
as low quality if it remains available to developers.

The sample pasted during testing also exposed a separate source-text problem:
it contained Malayalam pre-base vowel marks in invalid copy/paste order (for
example, forms shaped like `െ` or `േ` appearing before the consonant they
modify) and question marks where conjunct characters had been lost. This is
typical of text extracted from some PDFs, legacy-font documents, or faulty OCR.
Unicode NFC alone cannot restore missing characters. BhashaVox needs a review
stage that can safely reorder deterministic vowel-mark corruption and flag
irrecoverable characters before synthesis.

Docker Desktop exposed 16 CPUs and approximately 14.6 GB RAM to containers;
no NVIDIA runtime was detected. Indic Parler-TTS should fit its documented
roughly 4–6 GB CPU memory requirement, but latency must be measured. The
official `ai4bharat/indic-parler-tts` checkpoint is currently gated: an
unauthenticated request for `model.safetensors` returned HTTP 401, and the
3.75 GB model card requires accepting its access conditions. The token must be
supplied as a build secret or local Hugging Face credential and must never be
committed or baked into image metadata.

An ungated Apache-2.0 ONNX mirror exists at
[`OpenVoiceOS/phoonnx-indic-parler`](https://huggingface.co/OpenVoiceOS/phoonnx-indic-parler).
It contains about 5 GB of float32 graphs and reports waveform parity with the
PyTorch checkpoint. It is a possible CPU fallback, but it is a third-party
export with a smaller user base and must be evaluated before replacing the
official model path.

## Source index

- [Indic Parler-TTS model card](https://huggingface.co/ai4bharat/indic-parler-tts)
- [IndicF5 model card](https://huggingface.co/ai4bharat/IndicF5)
- [IndicF5 repository](https://github.com/AI4Bharat/IndicF5)
- [AI4Bharat Indic-TTS repository](https://github.com/AI4Bharat/Indic-TTS)
- [Meta MMS documentation](https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md)
- [Meta MMS Tamil model card](https://huggingface.co/facebook/mms-tts-tam)
- [AI4Bharat IndicXlit repository](https://github.com/AI4Bharat/IndicXlit)
- [OpenVoiceOS phoonnx Indic Parler ONNX export](https://huggingface.co/OpenVoiceOS/phoonnx-indic-parler)
- [VEXYL-TTS CPU implementation notes](https://github.com/vexyl-ai/vexyl-tts)

## Implementation checkpoint — 2026-09-22

The earlier recommendation to flag irrecoverable characters was superseded by
the product decision that correction must be built into the synthesis path and
must not require user editing. Deterministic Unicode-order repair is now
automatic. The two placeholder corruptions observed in the supplied sample are
also restored automatically. Unknown Malayalam-adjacent question marks are
currently removed so the speech engine cannot vocalize them; this is a safe
audio fallback, not proof that the missing word was reconstructed correctly.

Research found no ready-to-use, Malayalam-specific post-correction checkpoint
that could be adopted without evaluation. AI4Bharat IndicBART supports
Malayalam and was trained with a text-infilling objective, but non-Devanagari
input requires script conversion and the model card presents infilling as a
pretraining/generation capability rather than a validated Malayalam OCR repair
system. The open Datuk corpus contains more than 83,000 Malayalam dictionary
entries under ODbL-1.0 and is a possible candidate source for lexical matching,
but its share-alike database obligations and lack of contextual frequency
ranking need design review before redistribution.

The neural runtime scaffold follows the official Indic Parler-TTS inference
sequence: load the Parler model, tokenize transcript and voice description
separately, generate waveform samples, and write 44.1 kHz model output to WAV.
The implementation pins the Parler-TTS source revision used during research
because its package currently pins Transformers 4.46.1. Actual Docker build and
CPU inference results are recorded below.

## Neural runtime measurements — 2026-09-22

The CPU-only neural image built successfully after isolating its Python
dependencies in `/opt/venv`. Installing PyTorch and Torchaudio from the CPU
wheel index before the remaining packages prevented pip from selecting a much
larger CUDA dependency graph. The verified runtime contains PyTorch 2.5.1+cpu,
Torchaudio 2.5.1+cpu, Transformers 4.46.1, and Parler-TTS 0.2.2. CUDA is not
available on this host.

Hugging Face authentication alone was insufficient for the gated checkpoint:
metadata was readable while `config.json` still returned HTTP 403 until the
same user account accepted the model's access conditions in a browser. After
approval, the first short Malayalam request using the Anjali voice completed
successfully. It included the one-time model download and load, took 451.3
seconds, and produced a 240,684-byte WAV. A second short request in the warm
process took 41.9 seconds and produced a 289,836-byte WAV. The health endpoint
remained responsive during generation.

These numbers establish that local CPU inference works, but not that it is fast
enough for long-form interactive use. Audio naturalness and Malayalam
pronunciation still require user listening tests. Sentence chunking, progress
reporting, and queued generation are required before testing long pasted text.

Additional sources:

- [AI4Bharat IndicBART model card](https://huggingface.co/ai4bharat/IndicBART)
- [Datuk Malayalam dictionary corpus](https://github.com/knadh/datuk)
- [Hugging Face Parler-TTS repository](https://github.com/huggingface/parler-tts)
