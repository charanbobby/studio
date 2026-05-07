# 004: 5s default duration with 90s recorded for the walkthrough
**Date:** 2026-05-07
**Status:** Decided

## Context
The spec calls for a 90-second reel to satisfy the assessment, but iterating on a 90s pipeline during dev costs roughly $0.25 or more per run (TTS + 8 scenes + video assembly). With a daily cost cap and many iteration cycles required for prompt tuning, captions, and ffmpeg work, full-length runs would exhaust the budget before we shipped.

## Decision
Reel duration is configurable via `target_duration_seconds`; the default is 5s for development; the walkthrough records one canonical 90s run.

## Why
- Iteration speed: 5s reels generate 1 voice line + 1 to 2 scenes + a 5-second mux, completing in well under a minute and costing a fraction of a 90s run.
- Cost discipline: lets us stay inside `DAILY_COST_CAP_USD` (see ADR 012) while doing the dozens of dev iterations that prompt and caption work require.
- Spec compliance is shown via the recorded 90s run in the walkthrough video, so we never give up the headline deliverable.
- Frontend `PromptForm` already exposes the duration slider; the auto-toggle for music at 30s+ (see ADR 008) shares the same field.
- 5s is long enough to validate every stage of the pipeline (intent, plan, voice, scenes, edit, captions) end-to-end.

## Tradeoffs
- The walkthrough has to demonstrate both lengths (5s for the live demo, 90s on tape) which adds narration complexity.
- An assessor doing a live test on the deployed URL gets 5s by default and may not know to bump it.
- Some 90s-only failure modes (caption sync drift over long audio, scene boredom) only surface in the recorded run.

## Evidence
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 11 (schedule) and section 3 (cost table).
- Plan: `docs/superpowers/plans/2026-05-07-sri-studio-implementation.md` walkthrough section.
- Code: frontend `PromptForm` duration slider.
