# 007: Captions via ElevenLabs alignment, not Whisper
**Date:** 2026-05-07
**Status:** Decided

## Context
Reels are watched sound-off on mobile feeds; burned-in captions are table stakes. We need word-level timestamps so the ASS subtitle file syncs cleanly with the VO. Initial plan considered running Whisper as a post-process to transcribe and align the generated MP3, which would add a model download, a Python dependency, and a second inference step.

## Decision
Captions are produced from ElevenLabs `with-timestamps` endpoint character-level alignment, grouped into words and rendered as ASS for ffmpeg burn-in.

## Why
- Single call: the same TTS request that returns audio also returns alignment, so there is no extra Whisper service to deploy.
- Precision: probe 02 measured the alignment delta vs total audio duration at well under 30ms, tighter than Whisper word timestamps in our experience.
- No model footprint: avoids shipping or downloading Whisper weights inside the container; keeps the image small.
- Cost: alignment is included in TTS pricing; no extra API spend.
- Code path: `media/elevenlabs_tts.py::_chars_to_words` does a deterministic char-to-word grouping that has been probed end-to-end.

## Tradeoffs
- Caption shape is coupled to ElevenLabs response; if we ever swap TTS providers (see ADR 003), captions need a new alignment source.
- No fallback today if ElevenLabs returns audio without timestamps; the run would fail caption rendering rather than degrade to plain-audio.
- Word grouping is heuristic (whitespace + punctuation), so unusual punctuation patterns can split a word.

## Evidence
- Probes: `backend/experiments/probe_02_elevenlabs_alignment.py`, `backend/experiments/probe_06_caption_burn.py`.
- Code: `backend/media/elevenlabs_tts.py` (`_chars_to_words`).
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` (caption pipeline).
