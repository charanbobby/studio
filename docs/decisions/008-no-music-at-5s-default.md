# 008: No background music at the 5s default
**Date:** 2026-05-07
**Status:** Decided

## Context
Background music makes a 30s+ reel feel polished, but at 5 seconds it barely fades in before the reel ends. Music generation also adds a Replicate call (cost), an ffmpeg ducking pass (complexity), and a sync edge case where music length must match VO length. Given that 5s is the dev default (see ADR 004), we had to decide whether music belongs in the default path.

## Decision
Music is skipped at 5s default; available with a `--with-music` flag (and an auto-toggle in the frontend at 30s+) for longer reels.

## Why
- Cost: keeps the 5s dev iteration price down; music gen is a measurable line item in `backend/llm/cost.py` UNIT_RATES that adds up across dozens of dev runs.
- Inaudibility at 5s: a 5-second clip cannot fit a meaningful music intro + duck + outro; the ffmpeg ducking gain is wasted.
- Complexity: skipping the music branch removes a whole ffmpeg filtergraph stage from the dev path, simpler to debug.
- Frontend `PromptForm` auto-enables music when duration >= 30s, so the user does not have to remember to toggle it for the 90s walkthrough run.
- Spec section 3 cost table accounts for music as an opt-in line item, not a baseline.

## Tradeoffs
- 5s reels feel less polished than reels from competitor tools that include stock music; assessors who try the live deploy at the default get a barer output.
- Two code paths to maintain: the with-music ffmpeg pipeline and the no-music one.
- Auto-toggle at 30s is a magic-number boundary that needs a comment to be discoverable.

## Evidence
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 3 cost table.
- Code: `frontend/components/PromptForm.tsx` duration-based music toggle.
- Code: `backend/media/ffmpeg_assemble.py` music branch gated on flag.
