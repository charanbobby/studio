# Sri Studio: Design Spec

**Product name:** Sri Studio
**Deployment target:** studio.sshub.dev
**Codebase:** `reel_gen` Python package + `sri-studio` frontend (the descriptive name lives in code; the brand name lives at the user surface)
**Date:** 2026-05-07
**Author:** Sricharan Sunkara, with Claude Code as thinking partner
**Submission target:** CSC Generation, AI Solutions Engineer take-home
**Project option:** Component A, Option 3 (AI Reel Generator)
**Status:** Approved by user; ready for implementation plan

---

## 1. Goal and constraints

Build a tool that generates a vertical Instagram-Reel-format MP4 (1080x1920, ~5-90s, with audio) from a single text prompt. The tool must:

- Run end-to-end without manual intervention (priority #1 per assessment rubric; non-working = auto-disqualify).
- Survive the assessment timebox of 2-3 days.
- Be a tool the user keeps using personally after the interview, not a one-shot demo.
- Speak in the user's own cloned voice across every generated reel.
- Cost less than ~$0.30 per 90s reel and less than ~$0.05 per 5s reel in API spend.
- Default to 5s reel duration for cheap iteration; spec-compliant 90s on tape for the walkthrough.
- Run locally via `docker compose up` for development.
- Deploy to **studio.sshub.dev** via Hetzner so the assessor sees a live production URL. Access gated by HTTP basic auth; one credential pair for the user, one temporary pair shared with CSC for the interview window. Daily cost cap aborts new runs when exceeded so the assessor cannot accidentally burn the user's API budget.

**Out of scope:** Instagram posting, multi-brand templating, deployment to a cloud host, GPU-accelerated local model serving, user auth / accounts, database persistence (filesystem-only).

## 2. Architecture

Two services orchestrated via Docker Compose: a FastAPI backend wrapping a LangGraph state machine, and a Next.js frontend for prompt input + live progress + result viewing. The LangGraph pipeline has four discrete nodes, each with one responsibility. Every paid API call wrapped in cost-print pre/post helpers per global CLAUDE.md. Tracing via Langfuse Cloud free tier. Filesystem-only state under `runs/<run_id>/`; no database.

```
  Browser                                                                     
   │                                                                          
   │ POST /api/runs {prompt, duration_s, with_music}                          
   ▼                                                                          
  ┌──────────────────┐    SSE: per-node events    ┌──────────────────────┐    
  │ Next.js frontend │ <───────────────────────── │  FastAPI backend     │    
  │   /              │                            │  (uvicorn)           │    
  │   /runs/[id]     │ <── GET /runs/{id}/reel ── │                      │    
  └──────────────────┘                            │  Wraps LangGraph     │    
                                                  │  state machine       │    
                                                  └──────┬───────────────┘    
                                                         │ run_graph(state)   
                                                         ▼                    
  ┌─────────────────────────────────────────────────────────────────────┐     
  │                  LangGraph State Machine                            │     
  │   ┌──────────┐                                                      │     
  │   │ EXTRACT  │ Claude Haiku via OpenRouter (cached system prompt)   │     
  │   │  node    │ → ExtractedIntent                                    │     
  │   └────┬─────┘                                                      │     
  │        ▼                                                            │     
  │   ┌──────────┐                                                      │     
  │   │  PLAN    │ Claude Sonnet via OpenRouter (cached system+schema)  │     
  │   │  node    │ → ScriptPlan, writes runs/<id>/plan.json             │     
  │   └────┬─────┘                                                      │     
  │        ▼                                                            │     
  │   ┌─────────────────────────────────────────────────┐               │     
  │   │  EXECUTE (parallel fan-out)                     │               │     
  │   │   ├─ tts:        ElevenLabs Voice Clone         │               │     
  │   │   │              + alignment timestamps         │               │     
  │   │   ├─ visuals[N]: Flux Schnell on Replicate      │               │     
  │   │   │              (asyncio.gather across scenes) │               │     
  │   │   └─ music:      ElevenLabs Music               │               │     
  │   │                  (graceful degrade to silence)  │               │     
  │   └────┬────────────────────────────────────────────┘               │     
  │        ▼                                                            │     
  │   ┌──────────┐                                                      │     
  │   │  STITCH  │ ffmpeg (deterministic):                              │     
  │   │  node    │   - pad/crop to 1080x1920                            │     
  │   └────┬─────┘   - Ken Burns zoompan motion                         │     
  │        │         - audio mix + sidechain duck                       │     
  │        │         - burn-in captions from alignment                  │     
  └────────┼────────────────────────────────────────────────────────────┘     
           ▼                                                                  
   runs/<id>/reel.mp4   runs/<id>/cost.json   runs/<id>/plan.json             
                                Langfuse trace                                
```

### Why this decomposition (per SKILL.md Phase 5)

- Each node has one job and produces a reviewable artifact.
- Plan node output is a structured Pydantic model written to disk; humans (or the assessor) can read `plan.json` and see exactly what the model decided to make before any expensive media generation ran.
- Each node uses a different model class (cheap classification, expensive planning, hosted media generation, deterministic post-processing), per SKILL.md Phase 5c per-step model selection.
- Failure is localized: wrong reel = inspect plan; wrong plan = inspect intent; wrong intent = inspect brief.

## 3. Provider picks

| Node | Provider | Reason | Approx cost @ 5s | Approx cost @ 90s |
|------|----------|--------|------------------|-------------------|
| Extract | Claude Haiku via OpenRouter (cached) | Mechanical structuring, cheap | ~$0.001 | ~$0.001 |
| Plan | Claude Sonnet via OpenRouter (cached) | Quality matters most here | ~$0.01 | ~$0.02 |
| TTS | ElevenLabs Instant Voice Clone | Best voice clone quality, returns alignment | ~$0.01 | ~$0.10 |
| Image gen | Flux Schnell on Replicate | Cheapest tier, native 9:16 | ~$0.006 | ~$0.018 |
| Captions | ElevenLabs `request_alignment` field | No extra service; character-level timestamps | $0 | $0 |
| Music | ElevenLabs Music (skipped at 5s default) | 5s music bed not audible | $0 | ~$0.10 |
| Stitch | ffmpeg in container | Free, deterministic | $0 | $0 |
| Tracing | Langfuse Cloud free tier | 50k observations/month free | $0 | $0 |
| **Total per reel** | | | **~$0.03** | **~$0.25** |

Cost-reduction levers already pulled: cheap image model, stills + Ken Burns over video gen, cached Claude system prompts, dev-mode asset cache by content hash, music skipped at default duration, voice clone reused across runs.

## 4. State schema

```python
class ReelState(TypedDict):
    # Input
    run_id: str
    brief: str
    duration_s: int          # 5 default, configurable up to 90+
    with_music: bool         # False at 5s, True at >=30s

    # After Extract
    intent: ExtractedIntent | None

    # After Plan (the auditable artifact)
    plan: ScriptPlan | None

    # After Execute (parallel fan-out)
    voiceover_path: Path | None
    image_paths: list[Path]
    music_path: Path | None
    captions: list[CaptionWord] | None  # from ElevenLabs alignment

    # After Stitch
    reel_path: Path | None

    # Side channels
    cost_ledger: list[CostEntry]
    errors: list[NodeError]

class ScriptPlan(TypedDict):
    hook: str
    scenes: list[Scene]      # 1-2 @ 5s, 6-8 @ 90s
    voiceover_text: str      # full narration timed to duration
    voice_style: str
    music_mood: str | None
    aspect_ratio: str        # "9:16"

class Scene(TypedDict):
    scene_idx: int
    duration_s: float
    visual_prompt: str       # full Flux Schnell prompt with 9:16
    voiceover_excerpt: str   # words said during this scene
    motion: str              # "zoom_in", "zoom_out", "pan_right", etc.
```

## 5. Failure modes and graceful degradation

Per node:

- **Extract:** If brief is too vague, mark `intent.notes = "AMBIGUOUS_BRIEF"` and proceed with conservative defaults. Never fabricate intent (per global CLAUDE.md absence-handling rule).
- **Plan:** Pydantic validation on Claude output. Up to 2 retries with validation errors fed back. On third failure, fall back to a deterministic plan template so the pipeline still ships a reel.
- **TTS:** Retry with exponential backoff (max 3). Hard failure aborts the run; voiceover is the spine of the reel and cannot be skipped.
- **Image gen:** Per-scene retry up to 3. NSFW filter rejection triggers one retry with a deterministically rewritten safer prompt. Final failure on a single scene falls back to a solid-color frame with the scene's voiceover text overlaid; the reel still ships.
- **Music:** Best-effort. If gen fails, set `music_path = None` and log an error; Stitch handles silence cleanly.
- **Stitch:** Either succeeds or fails loudly. No retry. Failure indicates Plan-Execute alignment bug (e.g., voiceover longer than total scene duration); needs human attention.

## 6. Probe matrix (run BEFORE LangGraph wiring)

Per SKILL.md Phase 3 and global CLAUDE.md fail-fast rule. Each probe is a standalone Python script in `experiments/`. None get folded into pipeline code until they exit 0 with expected output.

| # | Probe | What it proves |
|---|-------|----------------|
| 01 | `probe_01_openrouter_claude_cached.py` | Claude via OpenRouter honors `cache_control: ephemeral`; cost helpers print correct numbers |
| 02 | `probe_02_elevenlabs_voiceclone_tts.py` | Voice clone ID accepts text, returns MP3 + alignment array |
| 03 | `probe_03_replicate_flux_schnell_9x16.py` | Flux Schnell honors aspect_ratio="9:16", outputs at expected dimensions |
| 04 | `probe_04_replicate_flux_nsfw_behavior.py` | Document NSFW failure mode and error string for retry path |
| 05 | `probe_05_ffmpeg_kenburns_zoompan.py` | zoompan filter produces smooth motion on 1080x1920 stills |
| 06 | `probe_06_ffmpeg_caption_burn_in.py` | ASS subtitles from alignment data render correctly, sync within 100ms |
| 07 | `probe_07_ffmpeg_audio_mix_duck.py` | Sidechain compression ducks music under voiceover (deferred until music feature in scope) |
| 08 | `probe_08_elevenlabs_music.py` | Music API returns MP3 of requested duration matching mood (deferred) |
| 09 | `probe_09_langfuse_cloud_trace.py` | Langfuse Cloud SDK creates traces with nested spans |
| 10 | `probe_10_e2e_minimal.py` | End-to-end smoke: hardcoded plan to MP4 |

Order: 01 -> 02 -> 03 -> 05 -> 06 -> 09 -> 10. Probes 04, 07, 08 are deferred or fire-and-forget documentation.

## 7. Documentation artifacts (parallel to the build)

Five docs under `docs/`, written during the build, harvested into the final submission:

```
docs/
  decisions/                    # ADRs, ~1 page each
    001-langgraph-over-n8n.md
    002-flux-schnell-over-sdxl.md
    003-elevenlabs-voiceclone.md
    004-5s-default-with-90s-on-tape.md
    005-frontend-included-nextjs-fastapi.md
    006-langfuse-cloud-tracing.md
    007-captions-via-elevenlabs-alignment.md
    008-no-music-at-5s-default.md
    009-fail-fast-probe-matrix-as-phase-gate.md
    010-runs-as-filesystem-no-database.md
    011-sri-studio-name-and-studio-sshub-dev-deployment.md
    012-basic-auth-and-daily-cost-cap.md
  build-journal.md              # rolling chronological log
  walkthrough-script.md         # SKILL.md Phase 10b template
  questionnaire-draft.md        # 9 question sections, evidence accrues
  diagrams.html                 # SKILL.md Phase 10c
```

**Operational rule:** every real decision (provider pick, scope change, probe failure, fallback design) gets an ADR proposed in chat for sign-off, then written to `docs/decisions/`. Every probe result and every node-complete moment gets a build-journal entry. Questionnaire-draft accumulates bullets as evidence appears.

This approach is what makes Components B and C cheap to produce instead of frantic.

## 8. Repo layout

```
D:\Python Applications\CSC\
├── README.md
├── docker-compose.yml              # backend + frontend services
├── .env.example                    # all keys for backend
├── .failfast.list                  # gates backend/src/reel_gen/nodes/*.py
├── backend/
│   ├── Dockerfile                  # python:3.12-slim + ffmpeg + uv
│   ├── pyproject.toml              # uv-managed
│   ├── src/reel_gen/
│   │   ├── __main__.py             # CLI fallback: python -m reel_gen ...
│   │   ├── api.py                  # FastAPI app: routes, SSE, run lifecycle
│   │   ├── state.py                # Pydantic models (ReelState, ScriptPlan, ...)
│   │   ├── graph.py                # LangGraph wiring
│   │   ├── nodes/                  # extract.py, plan.py, execute_*.py, stitch.py
│   │   ├── llm/                    # openrouter client + cost helpers + prompts/
│   │   ├── media/                  # elevenlabs_tts.py, replicate_flux.py, ffmpeg_stitch.py
│   │   ├── cache/content_hash.py   # dev-mode asset cache
│   │   └── tracing/langfuse_client.py
│   └── experiments/                # SKILL.md Phase 3
│       ├── notebook_e2e.ipynb
│       └── probe_*.py
├── frontend/
│   ├── Dockerfile                  # node:20-alpine
│   ├── package.json                # next, react, tailwind, typescript
│   ├── app/                        # Next.js 14 App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                # / (new run form)
│   │   ├── runs/
│   │   │   ├── page.tsx            # /runs (history)
│   │   │   └── [id]/page.tsx       # /runs/{id} (live status + result)
│   │   └── globals.css             # Tailwind base
│   ├── components/                 # PromptForm, ProgressTimeline, PlanPreview, ReelPlayer, CostLedger
│   └── lib/                        # api client, SSE hook, types mirroring backend Pydantic models
├── runs/                           # gitignored; mounted into both services as a shared volume
│   └── <run_id>/
│       ├── intent.json
│       ├── plan.json
│       ├── voiceover.mp3
│       ├── scene_*.png
│       ├── music.mp3
│       ├── reel.mp4
│       └── cost.json
├── docs/                           # decisions/, build-journal.md, walkthrough-script.md, questionnaire-draft.md, diagrams.html, superpowers/specs/
├── memory/                         # already seeded
├── scripts/                        # already installed: probe.sh, fail-fast-gate.sh, pre-commit-fail-fast.sh
└── .probes/                        # already installed
```

### 8a. Docker Compose

```yaml
services:
  backend:
    build: ./backend
    env_file: .env
    volumes:
      - ./runs:/app/runs
    ports: ["8000:8000"]
    command: uvicorn reel_gen.api:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports: ["3000:3000"]
    depends_on: [backend]
    command: npm run start
```

### 8b. Backend API surface

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/runs` | Start a run; body: `{prompt, duration_s, with_music, review_plan_first}`. Returns `{run_id}`. |
| `GET` | `/api/runs` | List past runs with thumbnails (latest first). |
| `GET` | `/api/runs/{id}` | Run status snapshot: phase, plan, cost ledger, error list, reel URL when ready. |
| `GET` | `/api/runs/{id}/stream` | Server-Sent Events: per-node start/end, cost entries, errors. Frontend subscribes here while the run is live. |
| `POST` | `/api/runs/{id}/approve-plan` | Stretch goal: when `review_plan_first=True`, this is the gate Execute waits for. |
| `GET` | `/api/runs/{id}/reel.mp4` | The generated MP4. Streamed from disk. |
| `GET` | `/api/runs/{id}/plan.json` | The auditable plan artifact. |
| `GET` | `/healthz` | Liveness probe for Docker. |

### 8c. Frontend pages

| Route | Components | Purpose |
|-------|-----------|---------|
| `/` | `PromptForm` | New run: prompt textarea, duration slider (5-90s), music toggle (default off, auto-on at >=30s), voice select (defaults to user's clone), Generate button. On submit POSTs `/api/runs` and routes to `/runs/{id}`. |
| `/runs/{id}` | `ProgressTimeline`, `PlanPreview`, `CostLedger`, `ReelPlayer` | Subscribes to SSE. Shows Extract/Plan/Execute/Stitch as a vertical timeline with per-node status. When Plan completes, `PlanPreview` renders `plan.json` (hook, scene-by-scene shots, voiceover script). When Stitch completes, `ReelPlayer` shows the MP4 with a download link. `CostLedger` streams entries inline. Footer link to the Langfuse trace. |
| `/runs` | `RunCard[]` | History grid: each card shows the prompt, thumbnail (last frame of reel), cost, date. Click to open `/runs/{id}`. |

UI is deliberately spartan: Tailwind defaults, no design system, clean typography. Goal is professional and functional in the walkthrough video, not portfolio-stunning. Branded as **Sri Studio** across the page header, favicon, and `<title>` tag. (Stretch polish if time permits.)

### 8d. Deployment (studio.sshub.dev)

Per SKILL.md Phase 9.

- **Host:** Hetzner Cloud (using the user's existing Hetzner Cloud Setup pattern from `d:\Python Applications\Hetzner Cloud Setup`).
- **Reverse proxy:** nginx terminating TLS via Let's Encrypt for `studio.sshub.dev`. nginx routes `/` and `/runs/*` to the frontend container, `/api/*` to the backend container, with SSE keep-alive timeouts tuned for long-running runs.
- **Auth:** HTTP basic auth at the nginx layer (cheapest possible gate). Two credential pairs in `.htpasswd`: one for the user (long-lived), one for CSC (provisioned for the interview window, revoked after).
- **Cost cap:** backend tracks per-day cost in a JSON file in the runs volume; before any paid API call, `_llm_cost_pre` checks the day's running total and aborts the run with a friendly error if it exceeds `DAILY_COST_CAP_USD` (default $5). The cap is independent of user/credential.
- **Secrets:** all API keys in `.env` on the server only. Never in git, never in the Docker image. Bumping `APP_VERSION` before each deploy per SKILL.md Phase 9.
- **Volumes:** named volume for `runs/` so generated reels survive container restarts.
- **Healthcheck:** nginx checks `GET /healthz` on the backend; frontend has its own readiness check.

## 9. Walkthrough video plan (Component B, 10-15 min)

| Section | Duration | Content |
|---------|----------|---------|
| Hook | 0:30 | Open at https://studio.sshub.dev. "This is Sri Studio. It generates reels in my voice. Let me show you." Play the final 90s reel up front so panel knows it works. |
| The brief | 1:00 | Why option 3, why a tool I'd keep using, why I deployed instead of demoing locally |
| LangGraph over n8n | 2:00 | Walk through ADR-001; explicit about respect for n8n in its lane |
| Architecture | 2:30 | 4-node decomposition, state schema, plan.json as auditable artifact, FastAPI wrapper + SSE per-node events |
| Fail-fast probes | 1:30 | Show probe scripts, run probe 10 live |
| Live demo | 2:30 | Open the live Sri Studio UI at studio.sshub.dev, type the brief, click Generate, narrate the live SSE stream as Extract -> Plan -> Execute -> Stitch nodes complete. Show plan.json preview rendering inline. Final video plays in the browser. Then play the 90s version recorded earlier. |
| Observability + cost | 1:00 | Langfuse trace, cost.json, daily cost cap, $250/month for 1000 reels math |
| Failure handling | 1:30 | Pydantic validation, NSFW retry, music degrade, scene fallback, cost-cap abort |
| Production deployment | 1:00 | Hetzner + Docker Compose + nginx + Let's Encrypt + basic auth at studio.sshub.dev. SKILL.md Phase 9 in production for this build, not just prior projects. |
| What's next + limits | 0:30 | Stretch goals, honest limits |
| My role vs AI's | 0:30 | SKILL.md two-column close + pattern statement |

Recording rule: voice in the walkthrough = the same cloned voice in the reels. Continuity hook nobody else will have.

## 10. AI Questionnaire approach (Component C, 9 questions)

| Q | Strategy |
|---|----------|
| Q1 hours/week | Direct honest answer |
| Q2 active tools | Lead with Claude Code, OpenRouter, ElevenLabs, Replicate, Langfuse, n8n |
| Q3 automation built | Lead with this build (recursive; live URL studio.sshub.dev); 2nd Find Evil; 3rd Fair Play / MaplePulse |
| Q4 most complex production | Sri Studio deployed at studio.sshub.dev via Hetzner + nginx + Let's Encrypt + basic auth + cost cap (this build is itself a production deployment); 2nd Find Evil DFIR pipeline |
| Q5 manual process translation | Fair Play document-to-DB pipeline |
| Q6 handling pushback | This build's n8n -> LangGraph reasoning; cite ADR-001 |
| Q7 kept human-only | plan.json review point, voice clone IDs user-supplied, deterministic NSFW retry |
| Q8 preventing AI errors | Pydantic validation, retries, graceful degradation, fail-fast probes, cost tracing, dual-channel evidence boundary |
| Q9 staying current | Direct honest answer |

The build is the proof-of-work for 5 of the 9 questions. The assessment is designed to be evaluated together, not in isolation.

## 11. Schedule (rough)

- Day 1 morning: probe matrix (probes 01-06, 09, 10). Decision records 001-013 backfilled (012 covers the UI scope addition; 013 covers the Sri Studio name + studio.sshub.dev deployment).
- Day 1 afternoon: Extract + Plan nodes + plan.json artifact. FastAPI `api.py` skeleton with `POST /api/runs` + SSE endpoint stub. Cost-cap helper. Build journal entries.
- Day 2 morning: Execute fan-out (TTS + image gen + captions). Notebook validation per SKILL.md Phase 3. Wire LangGraph node events to SSE.
- Day 2 afternoon: Stitch node + ffmpeg recipes. End-to-end run at 5s via API. Then 90s.
- Day 3 morning: Next.js frontend (`/`, `/runs/[id]`, components). Tailwind styling. Sri Studio branding (header, favicon, title). Smoke test through the browser locally.
- Day 3 afternoon: Deploy to studio.sshub.dev via existing Hetzner pattern. nginx + Let's Encrypt + basic auth. Smoke test the live URL. Diagrams.html. Walkthrough script polish.
- Day 3 evening: Record walkthrough video using the live studio.sshub.dev URL as the demo surface. Final submission package.

**Risk callouts:**
- The frontend half-day is the most compressible. Fallback: ship CLI-only locally and demo via screen share; the CLI path is preserved as `python -m reel_gen ...` for this exact reason.
- Deployment depends on the existing Hetzner pattern being in working order. Fallback: demo locally and link the assessor to the GitHub repo if the deploy slips.
- Plan-review-first toggle is explicitly stretch; ship without it first.

## 12. Open items / stretch goals

- IG posting via Graph API (deferred; not in scope)
- Plan-review-first toggle (Phase 6c human-in-the-loop checkpoint; ship core flow first, add if time)
- Music gen at >=30s reels (probe 08, deferred)
- Multi-brand presets (post-assessment, personal-use feature)
- Auth and multi-user support (single-user local tool by design)
- Run history search / filtering (basic list only at submission)

## 13. References

- Job description: `Application {Received Interview} - csc-generation-2026-05-04-015415-46619c7f/jd.txt`
- Working style: `skills/my-working-style/SKILL.md`
- Global rules: `~/.claude/CLAUDE.md`
- Seed memory: `memory/feedback_*.md`
