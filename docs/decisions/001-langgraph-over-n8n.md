# 001: LangGraph over n8n
**Date:** 2026-05-07
**Status:** Decided

## Context
The JD at `Application*/jd.txt` lists "n8n preferred" as a tooling signal, but also accepts "or similar." The pipeline we are building is a stateful AI workflow: 5 nodes (intent, plan, voice, scenes, edit) with branching retries, shared `RunState`, and per-node tracing. n8n is a visual workflow tool optimized for SaaS glue, not for typed Python AI graphs. We had to choose between matching the literal JD wording and matching the problem shape.

## Decision
LangGraph is used for orchestration; there is no n8n surface in the codebase.

## Why
- LangGraph fits stateful AI pipelines: `StateGraph(RunState)` gives typed shared state, conditional edges drive retry on each node, and the graph compiles to a callable used by FastAPI.
- The JD says "n8n preferred" but explicitly allows "or similar"; tool-specificity is satisfied by named platforms LangGraph + FastAPI + Replicate + ElevenLabs.
- n8n cannot cleanly express our retry semantics (Replicate 6/min rate limit backoff per probe 10) or our cost-cap gate without bespoke nodes.
- Python-native control flow keeps fail-fast probes (`backend/experiments/probe_*.py`) using the same imports as the runtime; no second runtime to maintain.
- The walkthrough story is stronger as "I picked the right tool" than "I followed the suggestion."

## Tradeoffs
- The walkthrough must explicitly justify the swap; an assessor who treats "n8n preferred" as mandatory will deduct.
- Loses the visual-flow demo that n8n gives for free.
- Future workflow-style integrations (Slack triggers, Sheets writes) are easier in n8n than in Python.

## Evidence
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 8b (API surface).
- Plan: `docs/superpowers/plans/2026-05-07-sri-studio-implementation.md` (graph wiring tasks).
- Code: `backend/graph.py` wires all 5 nodes via `StateGraph`.
- JD: `Application {Received Interview} - csc-generation-2026-05-04-015415-46619c7f/jd.txt`.
