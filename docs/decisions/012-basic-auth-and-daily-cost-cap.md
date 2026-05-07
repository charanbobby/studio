# 012: HTTP basic auth at nginx plus daily cost cap
**Date:** 2026-05-07
**Status:** Decided

## Context
A live deploy at `studio.sshub.dev` (see ADR 011) is open to the internet. Two failure modes: random scrapers triggering paid LLM/TTS/image calls, and an assessor running enough genuine experiments to blow the API budget. We needed a gate that keeps random traffic out and a budget guard that keeps even authenticated traffic bounded.

## Decision
HTTP basic auth is enforced at nginx for the entire frontend and API; a `DAILY_COST_CAP_USD` JSON ledger (`cost_cap.json`) aborts new runs the moment the day's spend exceeds the cap.

## Why
- Cheapest possible gate: nginx `auth_basic` is one config block, no auth service, no JWT, no session store.
- Cap is independent of who triggered the run, so a leaked password cannot blow the budget; the wall is dollar-amount, not user-identity.
- Aborts BEFORE the paid call, not after: cost cap check runs at the start of each run-creation request, so a cap-breaching prompt never reaches Replicate or ElevenLabs.
- Same JSON-on-disk pattern as run state (see ADR 010); one less storage technology to manage.
- Cap value lives in `.env` so the user can adjust per day without redeploying.
- Pairs with the global "print pre/post pricing" rule: the per-run cost log feeds the same JSON the cap reads.

## Tradeoffs
- nginx-level auth has no per-user attribution; cost ledger is global, so we cannot say "the assessor used $X, I used $Y."
- Cap is a hard wall not a soft warning; an assessor mid-walkthrough could hit it and see an abrupt failure instead of a degraded run.
- Basic auth credentials in nginx are static; rotating them means redeploying nginx.
- A clock skew or a manual edit of `cost_cap.json` would make the ledger lie; we accept this in single-user scope.

## Evidence
- Config: `nginx/nginx.conf` `auth_basic` directive.
- Code: `backend/llm/cost_cap.py` (JSON ledger and `assert_under_cap`).
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 8d.
