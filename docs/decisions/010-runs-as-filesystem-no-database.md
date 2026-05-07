# 010: Runs as filesystem artifacts, no database
**Date:** 2026-05-07
**Status:** Decided

## Context
The reel generator produces immutable run artifacts (intent, plan, voiceover, scenes, reel video, cost ledger). Scope is single-user plus assessor; there is no analytics requirement, no multi-tenant query, no audit trail beyond per-run JSON. We had to decide between a database (Postgres or SQLite) or a filesystem layout. Adding a DB would mean migrations, a schema, an ORM, and a backup story.

## Decision
All run state lives at `runs/<run_id>/` on disk: `intent.json`, `plan.json`, `voiceover.mp3`, `scene_*.png`, `reel.mp4`, `cost.json`, `state.json`. A small `RunRegistry` in `backend/runs.py` enumerates the directory.

## Why
- No DB to operate, back up, or migrate; the Hetzner box only runs nginx + Compose.
- Trivial to inspect: `ls runs/<id>` shows everything; no `psql` ceremony.
- Refresh-resilient: `state.json` mirrors the in-memory registry, so a backend restart re-hydrates from disk on first request.
- Cost cap is also a JSON file (`cost_cap.json`), so the entire data layer is one consistent shape.
- Each run directory is self-contained, which makes archiving (zip + upload) and debugging (download a folder) one operation.
- Sub-second latency for run lookup at our scale (tens of runs, not millions).

## Tradeoffs
- No multi-tenant query: cannot ask "all runs by user X" without a directory scan.
- No historical analytics: cannot graph cost over time without parsing every `cost.json`.
- Concurrent writes are naive: two backend workers writing the same run directory could race; mitigated today by single-worker uvicorn but not formally locked.
- Schema is implicit; a typo in a JSON key would not be caught by a migration.

## Evidence
- Code: `backend/runs.py` `RunRegistry`.
- Code: `backend/llm/cost_cap.py` (JSON ledger).
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` (run layout).
