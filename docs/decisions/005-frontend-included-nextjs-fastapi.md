# 005: Next.js frontend plus FastAPI backend instead of CLI-only
**Date:** 2026-05-07
**Status:** Decided

## Context
The initial design considered a CLI-only deliverable (`python -m backend.cli "<prompt>"`) since the assessment is graded on architecture and code quality, not UI. The user pushed for a UI: the walkthrough is a marketing artifact, not just a code review, and a live URL with a working form is the strongest "I shipped it" signal. We had to weigh ~1 day of frontend work against demo impact.

## Decision
A Next.js 14 + Tailwind frontend talks to the FastAPI backend over HTTP; both run in Docker Compose; production deploys behind nginx at studio.sshub.dev.

## Why
- SKILL.md Phase 6 default in the user's process is "frontend included unless cost is prohibitive."
- The walkthrough plays better as a screen recording of typing a prompt and watching the reel render than as a terminal session.
- Matches the user's portfolio style; other shipped projects (sshub.dev sub-apps) all have Next.js front ends.
- FastAPI separation lets the backend stay testable in isolation; the frontend is a thin client over a small JSON contract.
- Docker Compose hybrid (Node + Python in one stack) is the same shape as other projects on the same Hetzner host, so deployment is a known pattern.

## Tradeoffs
- Roughly one full day of frontend work (form, run-list, run detail, polling).
- Build complexity: multi-stage Dockerfile, package-lock pinning, Tailwind config maintenance.
- Two surfaces to keep in sync; a backend-only API change can break the frontend silently.

## Evidence
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` sections 8b (API), 8c (frontend), 8d (deploy).
- Tree: `frontend/` with `app/`, `components/PromptForm.tsx`, `components/RunList.tsx`.
- Compose: `docker-compose.yml` defines both services.
