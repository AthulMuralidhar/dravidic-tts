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

## Source index

- [Indic Parler-TTS model card](https://huggingface.co/ai4bharat/indic-parler-tts)
- [IndicF5 model card](https://huggingface.co/ai4bharat/IndicF5)
- [IndicF5 repository](https://github.com/AI4Bharat/IndicF5)
- [AI4Bharat Indic-TTS repository](https://github.com/AI4Bharat/Indic-TTS)
- [Meta MMS documentation](https://github.com/facebookresearch/fairseq/blob/main/examples/mms/README.md)
- [Meta MMS Tamil model card](https://huggingface.co/facebook/mms-tts-tam)
- [AI4Bharat IndicXlit repository](https://github.com/AI4Bharat/IndicXlit)

