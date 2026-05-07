# CSC Reel Generator: Design Spec

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
- Run locally via `docker compose up`; no hosted service the assessor can run on the user's API keys. Bring-your-own-keys via `.env`.
- Default to 5s reel duration for cheap iteration; spec-compliant 90s on tape for the walkthrough.

**Out of scope:** Instagram posting, frontend UI, multi-brand templating, deployment to a cloud host, GPU-accelerated local model serving.

## 2. Architecture

A LangGraph state machine with four discrete nodes, each with one responsibility. Invoked by a CLI entry point. Every paid API call wrapped in cost-print pre/post helpers per global CLAUDE.md. Tracing via Langfuse Cloud free tier.

```
                      ┌─────────────────────────────────────────────────┐
   python -m          │           LangGraph State Machine               │
   reel_gen           │                                                 │
   --prompt "..." ──► │   ┌──────────┐                                  │
   --duration 5       │   │ EXTRACT  │ Claude Haiku via OpenRouter      │
                      │   │  node    │ (cached system prompt)           │
                      │   └────┬─────┘ → ExtractedIntent                │
                      │        │                                        │
                      │        ▼                                        │
                      │   ┌──────────┐                                  │
                      │   │  PLAN    │ Claude Sonnet via OpenRouter     │
                      │   │  node    │ (cached system + schema)         │
                      │   └────┬─────┘ → ScriptPlan (auditable artifact)│
                      │        │       writes runs/<id>/plan.json       │
                      │        ▼                                        │
                      │   ┌──────────────────────────────────────────┐  │
                      │   │  EXECUTE (fan-out)                       │  │
                      │   │   ├─ tts:        ElevenLabs Voice Clone  │  │
                      │   │   │              + alignment timestamps   │  │
                      │   │   ├─ visuals[N]: Flux Schnell on         │  │
                      │   │   │              Replicate (parallel)    │  │
                      │   │   └─ music:      ElevenLabs Music        │  │
                      │   │                  (graceful degrade)       │  │
                      │   └────┬─────────────────────────────────────┘  │
                      │        │ → MediaAssets                          │
                      │        ▼                                        │
                      │   ┌──────────┐                                  │
                      │   │  STITCH  │ ffmpeg (deterministic):          │
                      │   │  node    │   - pad/crop to 1080x1920        │
                      │   └────┬─────┘   - Ken Burns zoompan motion     │
                      │        │         - audio mix + sidechain duck   │
                      │        │         - burn-in captions from        │
                      │        │           ElevenLabs alignment         │
                      └────────┼────────────────────────────────────────┘
                               ▼
                       runs/<id>/reel.mp4
                       runs/<id>/cost.json
                       runs/<id>/plan.json
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
    005-cli-only-no-frontend.md
    006-byo-keys-no-hosted-service.md
    007-langfuse-cloud-tracing.md
    008-captions-via-elevenlabs-alignment.md
    009-no-music-at-5s-default.md
    010-fail-fast-probe-matrix-as-phase-gate.md
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
├── pyproject.toml                  # uv-managed, Python 3.12
├── docker-compose.yml
├── Dockerfile                      # python:3.12-slim + ffmpeg + uv
├── .env.example
├── .failfast.list                  # gates src/reel_gen/nodes/*.py
├── src/reel_gen/
│   ├── __main__.py                 # python -m reel_gen --prompt "..." --duration 5
│   ├── state.py                    # Pydantic models
│   ├── graph.py                    # LangGraph wiring
│   ├── nodes/                      # extract.py, plan.py, execute_*.py, stitch.py
│   ├── llm/                        # openrouter client + cost helpers + prompts/
│   ├── media/                      # elevenlabs_tts.py, replicate_flux.py, ffmpeg_stitch.py
│   ├── cache/content_hash.py       # dev-mode asset cache
│   └── tracing/langfuse_client.py
├── experiments/                    # SKILL.md Phase 3
│   ├── notebook_e2e.ipynb
│   └── probe_*.py
├── runs/                           # gitignored; intent.json, plan.json, *.mp3, *.png, reel.mp4, cost.json
├── docs/                           # decisions/, build-journal.md, walkthrough-script.md, questionnaire-draft.md, diagrams.html, superpowers/specs/
├── memory/                         # already seeded
├── scripts/                        # already installed: probe.sh, fail-fast-gate.sh, pre-commit-fail-fast.sh
└── .probes/                        # already installed
```

## 9. Walkthrough video plan (Component B, 10-15 min)

| Section | Duration | Content |
|---------|----------|---------|
| Hook | 0:30 | Show the final 90s reel up front so panel knows it works |
| The brief | 1:00 | Why option 3, why a tool I'd keep using |
| LangGraph over n8n | 2:00 | Walk through ADR-001; explicit about respect for n8n in its lane |
| Architecture | 2:30 | 4-node decomposition, state schema, plan.json as auditable artifact |
| Fail-fast probes | 1:30 | Show probe scripts, run probe 10 live |
| Live demo | 2:30 | `python -m reel_gen` → plan.json → reel.mp4; play the 90s version recorded earlier |
| Observability + cost | 1:00 | Langfuse trace, cost.json, $250/month for 1000 reels math |
| Failure handling | 1:30 | Pydantic validation, NSFW retry, music degrade, scene fallback |
| What's next + limits | 1:00 | Stretch goals, honest limits |
| My role vs AI's | 0:30 | SKILL.md two-column close + pattern statement |

Recording rule: voice in the walkthrough = the same cloned voice in the reels. Continuity hook nobody else will have.

## 10. AI Questionnaire approach (Component C, 9 questions)

| Q | Strategy |
|---|----------|
| Q1 hours/week | Direct honest answer |
| Q2 active tools | Lead with Claude Code, OpenRouter, ElevenLabs, Replicate, Langfuse, n8n |
| Q3 automation built | Lead with this build (recursive); 2nd Find Evil; 3rd Fair Play / MaplePulse |
| Q4 most complex production | Find Evil DFIR pipeline (Slice 5 retro source) |
| Q5 manual process translation | Fair Play document-to-DB pipeline |
| Q6 handling pushback | This build's n8n -> LangGraph reasoning; cite ADR-001 |
| Q7 kept human-only | plan.json review point, voice clone IDs user-supplied, deterministic NSFW retry |
| Q8 preventing AI errors | Pydantic validation, retries, graceful degradation, fail-fast probes, cost tracing, dual-channel evidence boundary |
| Q9 staying current | Direct honest answer |

The build is the proof-of-work for 5 of the 9 questions. The assessment is designed to be evaluated together, not in isolation.

## 11. Schedule (rough)

- Day 1 morning: probe matrix (probes 01-06, 09, 10). Decision records 001-010 backfilled.
- Day 1 afternoon: Extract + Plan nodes + plan.json artifact. Build journal entries.
- Day 2 morning: Execute fan-out (TTS + image gen + captions). Notebook validation per SKILL.md Phase 3.
- Day 2 afternoon: Stitch node + ffmpeg recipes. End-to-end run at 5s. Then 90s.
- Day 3 morning: Diagrams.html. Walkthrough script polish. Questionnaire-draft polish.
- Day 3 afternoon: Record walkthrough video. Final submission package.

## 12. Open items / stretch goals

- IG posting via Graph API (deferred; not in scope)
- Frontend UI (deferred; CLI is sufficient for assessment)
- Music gen at >=30s reels (probe 08, deferred)
- Multi-brand presets (post-assessment, personal-use feature)

## 13. References

- Job description: `Application {Received Interview} - csc-generation-2026-05-04-015415-46619c7f/jd.txt`
- Working style: `skills/my-working-style/SKILL.md`
- Global rules: `~/.claude/CLAUDE.md`
- Seed memory: `memory/feedback_*.md`
