# 011: "Sri Studio" branding and studio.sshub.dev deployment
**Date:** 2026-05-07
**Status:** Decided

## Context
The project needed a name and a live URL for the walkthrough. The user wanted the brand built around their initials (the S in sshub.dev). Other tools on the same Hetzner host already follow a `<name>.sshub.dev` subdomain pattern, so the deployment story could either reuse that pattern or invent something new. The walkthrough needs a clickable URL, not just a `localhost:3000` screen recording.

## Decision
The product is branded "Sri Studio" and deploys to `studio.sshub.dev` on the existing Hetzner host.

## Why
- Personal brand alignment: the user's initials anchor sshub.dev; "Sri Studio" inherits that voice.
- Live URL is the strongest "I shipped it" signal in the walkthrough; assessors can click and try it themselves rather than trusting a recording.
- Reuses the existing Hetzner deploy pattern (`deploy/deploy.sh`, `nginx/` per-subdomain config), which is a known-good shape from prior projects.
- Keeps the post-assessment use case viable: the user wants to keep producing reels, and a permanent URL is friendlier than spinning up a local stack each time.
- No DNS or new TLS work; sshub.dev wildcard cert covers the subdomain.

## Tradeoffs
- A live deploy is more risk surface than local-only: the assessor could rack up costs (mitigated by ADR 012 cap), or hit it during an outage.
- Production secrets (Replicate, ElevenLabs, Langfuse keys) live on the Hetzner box and need rotation discipline.
- "Sri Studio" is brand-neutral; an assessor unfamiliar with the user's portfolio gets no brand story without the walkthrough narration.

## Evidence
- Spec: `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` section 8d.
- Config: `nginx/nginx.conf` with `studio.sshub.dev` server block.
- Script: `deploy/deploy.sh` reuses the sshub.dev pattern.
