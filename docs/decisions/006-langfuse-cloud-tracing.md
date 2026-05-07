# 006: Langfuse Cloud for per-call tracing
**Date:** 2026-05-07
**Status:** Decided

## Context
SKILL.md Phase 7 mandates per-call tracing on every LLM invocation; the user's global CLAUDE.md mandates printing pre/post pricing breakdowns on every LLM API call. We needed an observability layer that captures spans for each pipeline node, attaches input/output snapshots, and surfaces cost per run without us self-hosting yet another service. Options considered: Langfuse Cloud, self-hosted Langfuse, OpenTelemetry + Honeycomb, custom JSON logs only.

## Decision
Langfuse Cloud free tier (50k observations/month) is the tracing backend; spans are emitted via a `with_span` decorator that wraps each node.

## Why
- Cost: free tier covers 50k observations/month, well above expected dev + assessor traffic; no infra spend.
- Hosted: zero operational overhead, no Postgres or worker queue to maintain on the Hetzner box.
- SDK fit: probe 09 verified the v4 Python SDK works with our `with_span` decorator pattern, including nested spans for sub-steps.
- Cost capture: `langfuse.observe` plus our `_llm_cost_post` helper attach the actual usage and dollar amount to each span, satisfying the global rule.
- UI quality: per-trace timeline, per-node latency, and per-run cost rollup are visible without any custom dashboard work.

## Tradeoffs
- External dependency: a Langfuse outage degrades observability, though the pipeline keeps running because spans are fire-and-forget.
- Data egress: prompt content and tool outputs leave the host and live on Langfuse's servers; not appropriate for sensitive workloads but fine for the assessment.
- Free tier limits: a runaway loop could exhaust 50k observations; mitigated by the cost cap (see ADR 012) which stops new runs before that point.

## Evidence
- Probe: `backend/experiments/probe_09_langfuse_v4.py`.
- Code: `backend/tracing/langfuse_client.py`, `backend/tracing/decorators.py`.
- Global rule: user CLAUDE.md "Print pricing breakdown before AND after every LLM API call."
