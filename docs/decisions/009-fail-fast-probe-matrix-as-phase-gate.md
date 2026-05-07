# 009: Fail-fast probe matrix as phase gate before node code commits
**Date:** 2026-05-07
**Status:** Decided

## Context
The user's global CLAUDE.md has a hard rule: "Before I write code into a notebook cell, runbook, Dockerfile, script, or any committed artifact, I MUST run a minimal execution probe against the actual runtime that proves the new code runs and produces the expected output." Three documented past incidents (2026-04-12, 2026-04-17, 2026-04-19) where unverified code shipped to a project file and broke. For Sri Studio, every external API (Replicate, ElevenLabs, Langfuse) has surface area where a single shape surprise burns a full pipeline run.

## Decision
A 10-probe matrix gates node implementation: 7 required probes must exit 0 before the corresponding node code is committed; 1 docs probe; 2 deferred probes for optional features.

## Why
- Catches API surprises early and cheaply: probe 10 confirmed Replicate's 6/min rate limit, which would otherwise have failed the scenes node mid-run.
- Probe 02 nailed the ElevenLabs alignment shape (character-level timestamps with explicit `chars` and `character_start_times_seconds` fields) before any caption code was written.
- Probe 03 confirmed Flux Schnell native 9:16 at 768x1344 (see ADR 002) before scene generation code shipped.
- Probe spend (~$0.05) is a fraction of one wasted full pipeline run.
- Probe scripts double as living examples: each `backend/experiments/probe_*.py` is the canonical "minimum code to call this API," referenced from the actual node implementations.
- The phase-gate discipline matches the user's "fail-fast verify before committing ANY code" rule, so the project memory and the global rule reinforce each other.

## Tradeoffs
- Upfront cost: ~2 hours of probe-writing time before any node ships.
- ~$0.05 in real API spend on probes (small but nonzero).
- Probes can drift from the runtime if not re-run after API updates; we accept this in exchange for the upfront safety.

## Evidence
- Probes: `backend/experiments/probe_*.py` (10 files).
- Probe README: `backend/experiments/README.md` documents the matrix and required-vs-deferred status.
- Global rule: user CLAUDE.md "Fail-fast verify before committing ANY code into any project file."
