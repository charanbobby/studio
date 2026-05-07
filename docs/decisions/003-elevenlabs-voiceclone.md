# 003: ElevenLabs Instant Voice Clone for narration
**Date:** 2026-05-07
**Status:** Decided

## Context
The user wants Sri Studio to keep producing reels post-assessment for personal use, and the strongest hook in the walkthrough is "every reel sounds like me." The voice provider needs to support cloning, return per-character timestamps so we can burn captions, and stay inside the assessor cost cap. Options considered: ElevenLabs (cloning + alignment), OpenAI TTS (no clone), Replicate XTTS (clone but no alignment).

## Decision
ElevenLabs Instant Voice Clone is the TTS provider; the user's voice ID is configured via `.env` (`ELEVENLABS_VOICE_ID`).

## Why
- Voice quality: ElevenLabs Instant Voice Clone trained on a 1 to 3 minute sample produces output indistinguishable from a recorded VO, validated subjectively against probe 02 output.
- Alignment data: probe 02 confirmed the `with-timestamps` endpoint returns per-character start/end times, which feeds the caption burn-in pipeline (see ADR 007).
- Cost: starter plan covers the assessor walkthrough; UNIT_RATES in `backend/llm/cost.py` price TTS per 1k characters, and a 90s VO is roughly 200 to 250 characters.
- Walkthrough hook: voice continuity is the most obvious "this is Sri's tool" signal in the demo.
- One vendor for TTS + alignment removes the Whisper post-process step that a non-clone provider would force.

## Tradeoffs
- Locks the project to ElevenLabs; swapping to a different TTS later means re-doing alignment plumbing.
- Requires the user to upload a 1 to 3 minute voice sample; non-trivial onboarding for any new user.
- Voice ID is per-account, so the live deploy uses the user's voice for any assessor input (intentional for the demo).

## Evidence
- Probe: `backend/experiments/probe_02_elevenlabs_alignment.py`.
- Code: `backend/llm/cost.py` UNIT_RATES, `backend/media/elevenlabs_tts.py`.
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 3.
