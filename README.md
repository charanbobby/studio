# Sri Studio

AI reel generator. A text brief becomes a vertical short-form video with voice-cloned narration, image scenes, and burn-in captions, with a mandatory human-in-the-loop approval gate before any paid media APIs fire.

Live: https://studio.sshub.dev/ (basic auth; credentials shared in the submission email)

## What it does

1. **Extract** the brief into structured intent (brand, audience, duration, mood) via Claude Haiku.
2. **Plan** a `ScriptPlan` (hook, voiceover text, per-scene visual prompts, motion) via Claude Sonnet.
3. **Approve / edit** the plan in the browser. The user can rewrite the hook, voiceover, and per-scene prompts before anything bills. Edits are captured to `runs/<id>/plan_edits.json` for prompt distillation.
4. **Execute** in parallel: Flux Schnell for 9:16 images, ElevenLabs for cloned-voice TTS plus alignment-driven captions.
5. **Stitch** with ffmpeg into a 1080x1920 MP4.

Pipeline is a LangGraph state machine with deterministic node order, traced end to end on Langfuse.

## Repository layout

```
backend/        FastAPI + LangGraph pipeline, pytest suite (24 tests)
frontend/       Next.js 14 app (typed, Tailwind), runs page + plan-review UI
docs/
  decisions/    ADRs (LangGraph over n8n, Flux over SDXL, runs-as-filesystem, ...)
  superpowers/  Spec and 11-phase implementation plan
deploy/         tar-over-ssh deploy script for Hetzner
nginx/          studio.sshub.dev system-nginx site config
samples/        End-to-end sample reels (mp4 + plan.json + cost.json)
runs/           Per-run artifacts (gitignored)
```

## Local dev

```bash
cp .env.example .env       # fill in OpenRouter, Langfuse, Replicate, ElevenLabs keys
docker compose up --build  # backend on :8000, frontend on :3000
```

Open http://localhost:3000 and submit a brief.

### Backend tests

```bash
cd backend
uv pip install -e ".[dev]"
uv run pytest
```

### Frontend typecheck

```bash
cd frontend
npm install
npm run typecheck
```

## Cost discipline

Every LLM and media call writes to `runs/<id>/cost.json`. A daily cap (`DAILY_COST_CAP_USD`, default $5) is enforced server-side in `runs/_daily_cost.json`. The approval gate is the primary cost control: if the plan looks wrong, the user rejects before any image, TTS, or stitch call fires. Sample reels in `samples/` cost $0.03 to $0.06 each end to end. A rejected run cost $0.0058 (Extract + Plan only).

## Deployment

The production host runs Docker Compose behind system nginx + Let's Encrypt + basic auth. Both containers bind to `127.0.0.1` only; the host's nginx routes `studio.sshub.dev/api/*` to the backend container and `studio.sshub.dev/` to the Next.js container. See `nginx/studio.sshub.dev.conf` and `deploy/deploy.sh`.

## Design choices worth knowing

- **Human approval is mandatory, not optional.** ADR 012. The gate exists because text-to-video pipelines are easy to drive into expensive runaway loops.
- **Runs are filesystem-backed, no database.** ADR 010. Each run is `runs/<id>/` with `intent.json`, `plan.json`, `plan_edits.json`, `cost.json`, scene images, audio, captions, and the final `reel.mp4`. Trivially diffable, archivable, and shippable as samples.
- **LangGraph over n8n.** ADR 001. Typed state, version-controlled graph, native Python testability.
- **5-second default with 90 seconds on tape.** ADR 004. The model plans long, the stitcher trims short, the user always has the source.
- **Plan edits are training signal.** Every edit at the approval gate is captured with original-vs-edited diff. Future work: aggregate edits to identify systemic Plan-prompt failures and distill better defaults.

## Sample reels

See `samples/README.md`. Three end-to-end runs from the live system: a Sri Studio launch teaser, a Sur La Table spring sale, and a deliberately rejected Cozy autumn coffee shop brief.
