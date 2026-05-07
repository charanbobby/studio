# 002: Flux Schnell over SDXL for scene images
**Date:** 2026-05-07
**Status:** Decided

## Context
The reel generator needs roughly 6 to 8 vertical 9:16 scene images per 90-second reel (and 1 to 2 at the 5s default). The image model has to be cheap enough to iterate on, native to 9:16, and fast enough that scene generation does not dominate wall time. Replicate offers both Flux Schnell and SDXL variants; we had to pick one.

## Decision
Flux Schnell on Replicate (`black-forest-labs/flux-schnell`) is the default scene image model.

## Why
- Cost: Flux Schnell is $0.003 per image flat (see `backend/llm/cost.py` UNIT_RATES). SDXL on Replicate has variable pricing tied to step count and resolution, typically higher per image.
- Native 9:16: probe 03 (`backend/experiments/probe_03_*.py`) produced 768x1344 output in a single call, no upscale or crop step.
- Speed: Schnell renders in roughly 1 to 2 seconds per image on Replicate hardware, fast enough that 8 images run within the 90s reel budget.
- Cost table: spec section 3 lists scene cost as a small fraction of TTS + video, so the cheap-image choice keeps headroom for the parts that matter.
- Rate limit: probe 10 confirmed Replicate's 6/min cap; Schnell's speed lets the scenes node retry-with-backoff inside the budget.

## Tradeoffs
- Less photorealistic than Flux Dev or Pro variants; some prompt nuance is lost.
- 4-step model means fewer knobs (no negative prompt, no step tuning) for prompt engineers.
- Style consistency across scenes is weaker than a fine-tuned SDXL pipeline.

## Evidence
- Probe: `backend/experiments/probe_03_flux_schnell_aspect.py` (verified 768x1344).
- Code: `backend/llm/cost.py` UNIT_RATES dict.
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 3 cost table.
