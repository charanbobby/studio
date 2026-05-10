---
title: Helper-as-a-Service (sub-project A)
date: 2026-05-10
status: approved (brainstorm complete; awaiting user spec review)
audience: future implementer (you, six months from now)
---

# Helper-as-a-Service Design

## Goal

Make the existing Sri Studio Helper CLI pipeline (see repo `README.md`) callable as an HTTP service hosted under `studio.sshub.dev/helper/`, so future demos can be triggered with a `curl` call (or, in sub-project B, an MCP tool) instead of editing project files and running shell scripts manually. Preserve the silent-first cost discipline that justifies the existing pipeline shape.

## Non-goals

These belong to other sub-projects or v2 hardening; they are explicitly out of scope here.

- LLM auto-generation of beats/scenes from a "goal + codebase" input. Future work; see Approach 2 in `Alternatives considered`.
- Multi-tenant or public access. Single-trusted-caller (you, plus your future MCP wrapper) only.
- Per-job sandboxing (Docker-in-Docker, ephemeral per-job containers, AST scanning of uploaded scenes). Future v2 hardening.
- Off-site backup of `/data`. Jobs are reproducible from the source tarball you keep locally.
- The hiring-manager-facing showcase page on studio.sshub.dev that lists samples. Tracked as sub-project D, separate spec.
- The Sentinel page where the SIP Sentinel demo video lives. Tracked as sub-project C, separate spec.
- Portfolio tile linking to Sentinel. Tracked as sub-project E, separate spec.
- The MCP wrapper itself. Tracked as sub-project B, separate spec; this spec lists the size-guard constraint that B must respect.

## Approach decision

Three approaches were considered (full descriptions in `Alternatives considered` below). **Approach 1, "thin service over today's CLI", is chosen for v1** because it:

- matches the silent-first discipline that already produces good output,
- ships in days instead of weeks,
- and does not bet the whole service on LLM-generated Playwright reliability.

The chosen approach explicitly leaves the door open to layer Approach 2 ("Auto mode") on top later as a Tier 2 wrapper, without breaking Tier 1 callers.

## API surface

Five endpoints, all under `studio.sshub.dev/helper/`. Two POSTs and one GET cover the happy path; no polling required.

| Method + Path | Behavior |
|---|---|
| `POST /helper/jobs` (multipart with project tarball) | Blocks until the silent-with-captions preview is ready (a few minutes). Returns `{ job_id, preview_url, estimate_usd, status: "awaiting_review" }`. |
| `POST /helper/jobs/:id/voice` | Approval; runs Phase E (voice) + Phase F (final mux). Blocks until done. Returns `{ final_url, status: "done" }`. |
| `GET /helper/jobs/:id` | Status and URLs. Available for callers who prefer async polling. |
| `GET /helper/jobs/:id/log` | Per-job log file (phase timestamps, beat durations, stack traces on failure). |
| `GET /helper/skill` | Returns the canonical `SKILL.md` (markdown). The same lessons-learned document that lives in the repo root, shipped with the running container so callers (MCP clients, curl users, future Tier 2 LLM agent) can fetch authoritative best-practices guidance without cloning the repo. |
| `DELETE /helper/jobs/:id` | Manual cleanup. (TTL also runs automatically.) |

**Convenience flag:**

`POST /helper/jobs?auto_approve=true` runs both phases in one call (skips D.5 review gate). Off by default; intended for trusted callers using known-good templates.

**Why project-tarball upload, not JSON-with-base64-Python:**

The existing CLI workflow has callers author a project as a directory (`config.py`, `captions.py`, `scenes/`, `probes/`). The service accepts that exact layout as a multipart `project=@demo.tar.gz` upload. Local authoring stays identical; the only new step is `tar czf demo.tar.gz . && curl ...`. Avoids JSON gymnastics and the cross-reference-by-name footgun between separate `beats` and `scenes` arrays.

**MCP fit (informs sub-project B):**

The two POSTs map cleanly to two MCP tools:

- `helper_render_silent(project_tar) -> { preview_url, estimate_usd, job_id }`
- `helper_render_voice(job_id) -> { final_url }`
- Optional `helper_render_full(project_tar) -> { final_url }` wraps the auto-approve path for one-shot generation.
- Plus a `helper_skill() -> markdown` tool that returns `GET /helper/skill`, so the MCP client can load best-practices guidance into the LLM's context before it tries to construct a project tarball.

Each MCP tool maps to one user intent; inputs are JSON-Schema-able; outputs are small structured objects (see `Cost discipline` below for the size-guard constraint MCP tools MUST respect). The `helper_skill()` tool is the one exception, returning a roughly 5 KB markdown blob; well under the size-guard threshold.

## Data flow

```
Caller                                    Helper service
  |                                            |
  |  POST /helper/jobs (multipart: tar.gz)     |
  |-------------------------------------------->|
  |                                            |--> create /data/jobs/<id>/, untar
  |                                            |--> Phase A: probes (fail fast if site unreachable)
  |                                            |--> Phase B: per-beat Playwright recordings
  |                                            |     (one MP4 per beat in workdir)
  |                                            |--> Phase C: ffmpeg concat -> silent.mp4
  |                                            |--> Phase D: SRT + ffmpeg burn -> preview.mp4
  |                                            |--> count voiceover chars * USD_PER_CHAR = estimate_usd
  |                                            |
  | <-- 200 { job_id, preview_url, estimate_usd, status: "awaiting_review" }
  |                                            |
  |   (caller watches preview_url, decides)    |
  |                                            |
  |  POST /helper/jobs/<id>/voice              |
  |-------------------------------------------->|
  |                                            |--> Phase E: ElevenLabs per beat -> MP3s
  |                                            |--> Phase F: mux preview.mp4 + MP3s -> final.mp4
  |                                            |
  | <-- 200 { final_url, status: "done" }      |
  |                                            |
  |  GET <final_url>                           |
  |-------------------------------------------->|
  | <-- MP4 stream                             |
```

**Workdir model:**

One directory per job: `/data/jobs/<job_id>/`. Holds the untarred project (`config.py`, `scenes/`, etc.), per-beat MP4s, `silent.mp4`, `preview.mp4`, per-beat MP3s, `final.mp4`. TTL (default 7 days) deletes the whole directory. Public URLs only expose `preview.mp4` and `final.mp4`; uploaded source is never reachable over HTTP.

**Concurrency:**

Sequential queue for v1 (Playwright + ffmpeg are CPU-heavy and the VPS is single-tenant). `GET /helper/jobs/:id` exposes `position_in_queue` for `queued` jobs. Easy upgrade path to a worker pool later.

**Failure semantics (the important part):**

| Phase failure | Effect |
|---|---|
| A (probes) | Job dies fast, status `failed`, no recording. Cheapest possible failure. |
| B (any beat) | Job dies before C, status `failed`, error names the beat and selector. No captions, no voice; preserves silent-first discipline. |
| D (caption burn) | Preview never produced; status `failed`. Voice never runs. |
| E (ElevenLabs) | Workdir preserved, status `voice_failed`. Caller can `POST /voice` again to retry without re-recording; the silent stage's outputs are still on disk. This is the cost-discipline payoff. |
| F (final mux) | Same as E; preserved, retryable. |

**Cost guard for ElevenLabs:**

At the end of Phase D (just before returning the preview), the response includes `estimate_usd` derived from `sum(len(beat.voiceover) for beat in beats) * USD_PER_CHAR`. If `estimate_usd > daily_remaining_budget`, the `POST /voice` is rejected with 402 plus `{ reason: "would_exceed_daily_cap", remaining: ..., needed: ... }`. No surprise spend.

## Container architecture

**Single container** that bundles today's demo-video image plus a FastAPI HTTP server plus an in-process sequential job runner. Reasons: matches "thin service" intent, no inter-container networking, easy VPS deploy, easy upgrade path to a worker pool or per-job ephemeral containers later.

**The image (delta from today's `sri_studio_helper/Dockerfile`):**

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      ffmpeg fonts-ibm-plex \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --quiet uv

# NEW: service deps via uv (per project rule: always uv, never pip)
RUN uv pip install --system --no-cache \
      fastapi uvicorn[standard] python-multipart aiofiles

# NEW: ship the existing sri_studio_helper package + the FastAPI app
COPY sri_studio_helper/ /app/sri_studio_helper/
COPY helper_service/    /app/helper_service/

# NEW: ship the canonical SKILL.md so /helper/skill can serve it; this is the
# best-practices guidance MCP clients (and the future Tier 2 LLM agent) need
# to write correct project tarballs.
COPY SKILL.md           /app/SKILL.md

# NEW: data dir for job workdirs (volume-mounted at runtime)
RUN mkdir -p /data/jobs

WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "helper_service.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

`helper_service/` is the new code:

- `api.py` (FastAPI routes)
- `runner.py` (sequential pipeline orchestrator that shells out to existing `assemble_silent.sh`, `burn_captions.sh`, `assemble_final.sh`, plus calls into `record_beat.py` / `voice_gen.py`)
- `auth.py`
- `budget.py` (daily ElevenLabs cap, spend log)
- `cleanup.py` (TTL background task)

**docker-compose.yml on the VPS:**

```yaml
services:
  helper:
    image: sri-studio-helper:latest
    restart: unless-stopped
    ports: ["127.0.0.1:8001:8000"]   # bind localhost; nginx reverse-proxies
    volumes:
      - ./data:/data                  # job workdirs survive restarts
    environment:
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - HELPER_AUTH_KEY=${HELPER_AUTH_KEY}
      - DAILY_BUDGET_USD=5
      - JOB_TTL_DAYS=7
      - ELEVENLABS_USD_PER_CHAR=0.00044
    deploy:
      resources:
        limits: { cpus: "2", memory: "3G" }
```

**nginx (delta on the existing studio.sshub.dev block):**

```nginx
location /helper/ {
    proxy_pass         http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_request_buffering off;          # stream tarball uploads
    client_max_body_size 50m;             # cap upload size
    proxy_read_timeout 600s;              # silent-phase blocks for minutes
}
```

**Resource sizing rationale:**

Playwright + Chromium use roughly 1 GB RAM per job. ffmpeg uses roughly 500 MB during mux. Sequential queue means one job at a time, so 3 GB total + 2 CPUs is comfortable headroom on a small Hetzner VPS.

**Why no Docker-in-Docker / per-job sandboxing for v1:**

Uploaded Python runs in the same container as the API. That is acceptable because the only auth-key holder is you. When this service is ever opened to other callers, per-job ephemeral containers become required. Tracked in `Future work`.

## Routing + auth

**Routing:**

`studio.sshub.dev/helper/*` reverse-proxied to `127.0.0.1:8001` inside the container, single TLS cert (existing studio.sshub.dev), 50 MB upload cap, 600s read timeout.

**Auth (v1, single trusted caller):**

Static API key in a header.

```
POST /helper/jobs
X-Helper-Key: <random-hex-from-env>
Content-Type: multipart/form-data
...
```

- Server reads `HELPER_AUTH_KEY` from env at boot. Any request without a matching header returns 401.
- Rotation: update env file on VPS, `docker-compose up -d` (about 30 seconds downtime; acceptable).
- One key, all endpoints. No per-user model, no OAuth, no JWT. Future MCP wrapper reads the key from its own env.

If multi-caller is ever needed: add a tenant table mapping key to tenant + per-tenant budget. Not in v1.

**Rate limiting:**

- Daily ElevenLabs budget gate (see `Cost discipline`). Sole hard money guard.
- Job concurrency: sequential queue is the implicit rate limit; new jobs wait.
- No per-IP RPM limit. If we ever see abuse, add it in nginx.

**Sandboxing trade-off (v1):**

Uploaded Python runs in the same process space as the API. Worst case if the key leaks: attacker can run arbitrary Python in the container, spam ElevenLabs (capped by daily budget), delete files in `/data` (recoverable). Cannot escape the container boundary into the VPS host. Acceptable for v1; v2 hardening listed in `Future work`.

**Secrets handling:**

- `ELEVENLABS_API_KEY`, `HELPER_AUTH_KEY` are env vars only. Never logged, never echoed in responses.
- Caller's tarball must not contain secrets; this is documented as a caller responsibility. We do not scan uploads in v1.

**Logging and audit:**

- API stdout to `docker-compose logs` (rotated by docker default).
- Per-job log: `/data/jobs/<id>/log.txt` (phase start/end, beat durations, error tracebacks). Exposed via `GET /helper/jobs/:id/log` with the same auth.
- Audit log: `/data/audit.log`, one line per request, fields `ts, method, path, job_id, ip, ua, response_code`. No body content, no keys.

**TLS:**

Inherits the existing studio.sshub.dev cert via the same nginx server block. Nothing new to provision.

## Cost discipline + persistence

**ElevenLabs cost guard (sketch):**

```python
# helper_service/budget.py
DAILY_BUDGET_USD = float(os.environ["DAILY_BUDGET_USD"])           # default 5
USD_PER_CHAR     = float(os.environ.get("ELEVENLABS_USD_PER_CHAR", "0.00044"))
SPEND_FILE       = "/data/spend.json"

def estimate(beats):  # called at end of Phase D, returned to caller
    return sum(len(b["voiceover"]) for b in beats) * USD_PER_CHAR

def remaining_today():
    s = load_spend()                                    # resets each calendar day
    return DAILY_BUDGET_USD - s["spent_usd"]

def gate_voice(beats):
    est = estimate(beats)
    if est > remaining_today():
        raise HTTPException(402, {"reason": "would_exceed_daily_cap",
                                   "remaining": remaining_today(), "needed": est})
```

Per the project rule "print pricing breakdown before AND after every LLM API call", every ElevenLabs request gets:

- PRE: `[voice] beat=intro chars=128 estimate=$0.056` to job log + stdout
- POST: `[voice] beat=intro chars=128 actual=$0.056` to job log + stdout (ElevenLabs response includes character count; logged if it differs from the estimate)

ElevenLabs is not strictly an LLM provider, but the spirit of the rule (real-time cost transparency on every paid external call) applies; we treat it the same way.

**Spend log structure (`/data/spend.json`, rolls over daily):**

```jsonc
{
  "date": "2026-05-10",
  "spent_usd": 0.83,
  "by_job": {
    "abc123": {"chars": 612,  "estimated_usd": 0.27, "actual_usd": 0.27},
    "def456": {"chars": 1340, "estimated_usd": 0.59, "actual_usd": 0.56}
  }
}
```

**Persistence:**

- Job workdir: `/data/jobs/<job_id>/` (volume-mounted; survives container restart).
- TTL cleanup: background task walks `/data/jobs/` every hour; deletes any whose final-mtime is older than `JOB_TTL_DAYS` (default 7). Manual `DELETE /helper/jobs/:id` for explicit cleanup.
- Disk guard: new `POST /helper/jobs` rejected with 503 if `/data` has less than 1 GB free. Stops a runaway from filling the VPS.
- Per-job size budget: roughly 50 to 200 MB. At 5 jobs/day x 7-day TTL = roughly 7 GB peak. Comfortable on a small Hetzner VPS.

**No automated off-site backup in v1.** Jobs are reproducible from the source tarball you keep locally; if the VPS dies, you re-run. Tracked in `Future work`.

**Bridge to sub-project D (showcase page samples):**

Optional flag on the voice POST:

```
POST /helper/jobs/<id>/voice?save_as_sample=true
```

On success, copy `final.mp4` to `/data/samples/<job_id>/final.mp4` and write a manifest:

```jsonc
// /data/samples/<job_id>/manifest.json
{ "job_id": "abc123",
  "generated_at": "2026-05-10T14:00:00Z",
  "goal": "demo SIP Sentinel onboarding",
  "target_url": "https://sentinel.sshub.dev",
  "beats_summary": ["intro", "feature_x", "outro"] }
```

The future showcase page (sub-project D) reads `/data/samples/*/manifest.json` to render the sample table. No extra coordination required between A and D.

## Testing + verification

**Per-component fail-fast probes (built alongside each piece, per project rule):**

| Component | Probe (before committing the code) |
|---|---|
| HTTP layer | `curl -F project=@tiny.tar.gz -H "X-Helper-Key: $K" .../jobs` returns 200 + `job_id` |
| Pipeline orchestrator | Shell out to existing `assemble_silent.sh` on a known-good workdir; `silent.mp4` exists, `ffprobe` shows a video stream |
| ElevenLabs wrapper | Call `voice_gen.py` with a 5-character phrase; MP3 produced, cost line logged PRE+POST |
| Auth | `curl` with wrong key returns 401; with right key returns 200 |
| Budget gate | `DAILY_BUDGET_USD=0.001` + submit job whose estimate exceeds it returns 402 with `{reason: "would_exceed_daily_cap"}` |
| Disk guard | Fake `/data` near-full state; `POST /jobs` returns 503 |
| Container boot | `python -c "from helper_service.api import app"` at build time catches import errors |

**Persistent test suite (`helper_service/tests/`, runs in CI):**

Unit:

- `test_estimate.py`: char-count to USD math across beat counts and lengths.
- `test_spend_log.py`: daily rollover, atomic write, multi-job accumulator.
- `test_auth.py`: header matching matrix.
- `test_disk_guard.py`: mocked `/data` free-space scenarios.
- `test_state_machine.py`: happy path plus each failure transition.

Integration (one big end-to-end):

- Fixture: `tests/fixtures/tiny_demo.tar.gz`, a one-beat project pointing at a localhost static page in CI.
- Test: `POST /jobs` to wait for `awaiting_review`; assert `preview_url` returns a valid MP4; `POST /voice` to wait for `done`; assert `final_url` MP4 has both video and audio streams via `ffprobe -show_streams`.
- ElevenLabs in CI: mocked (captures HTTP request, returns canned MP3 from fixture). Catches integration bugs without burning tokens.
- ElevenLabs nightly cron on VPS: one real call (about $0.005). Confirms key is live and responding.

**Operational health endpoints (production):**

- `GET /helper/health` returns `{ ok: true, version, daily_budget_remaining_usd, queue_depth }`.
- `GET /helper/health/voice` (optional) is a dry-run ping to ElevenLabs that confirms key validity without burning tokens (uses ElevenLabs `/v1/user`).
- Nightly cron from VPS runs the tiny-fixture happy path end-to-end; alerts on failure via the existing `approve.sshub.dev/notify` Telegram pipe.

**MP4 sanity helper (used by integration test and nightly cron):**

```python
def assert_mp4_has_audio_and_video(path):
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "0", "-print_format", "json", "-show_streams", path]))
    types = {s["codec_type"] for s in info["streams"]}
    assert "video" in types and "audio" in types, f"expected both, got {types}"
```

**Heads-up for sub-project B (MCP wrapper):**

The MCP tool MUST NOT return the full per-job log to the LLM. Logs can run hundreds of KB on a multi-beat job (per-beat timestamps, ffmpeg stderr, etc.). Per the project's "tool output sent to an LLM must have a size guard" rule, MCP tool outputs are restricted to small structured objects (`{ job_id, preview_url, estimate_usd, status }` and `{ final_url, status }`). The full log lives at `/helper/jobs/:id/log` for human debugging. Flagged here so the netscan / fls_list class of bug does not repeat.

## Alternatives considered

### Approach 2: Agentic goal-only ("just give a goal")

HTTP API accepts `{ goal, url, codebase }`; an LLM agent reads the codebase, plans beats, generates Playwright scenes and captions, then runs the silent-first pipeline. Rejected for v1 because:

- Much bigger build (planning agent, codebase indexing, scene-code generation, scene-failure recovery).
- Generated Playwright will be fragile; selectors break, waits go wrong, the agent has to debug itself.
- Discards the silent-first cost discipline (no human review means voice runs every time without confirmation).

Re-visit as a Tier 2 layer on top of v1 once Tier 1 is stable. The Tier 2 wrapper would call Tier 1 internally (`POST /helper/jobs` with a tarball it generated).

### Approach 3: Two-tier (Pro mode + Auto mode)

Same as Approach 1 for v1 but with explicit API + container shape designed for an Auto mode (Approach 2 behavior) layered on top later. Functionally equivalent to "Approach 1 first, designed with future Tier 2 in mind"; the chosen Approach 1 already keeps that door open. No additional v1 work.

## Future work (tracked, not in v1)

- **Sub-project B (MCP wrapper)**, separate spec. Two tools: `helper_render_silent`, `helper_render_voice`. Optional `helper_render_full` for auto-approve. Tool outputs are restricted to small structured objects per the size-guard rule.
- **Sub-project C (Sentinel page)**, separate spec. Polish the page; embed the SIP Sentinel demo video.
- **Sub-project D (Showcase page)**, separate spec. Hiring-manager-facing page on studio.sshub.dev with service details + sample table; reads `/data/samples/*/manifest.json`.
- **Sub-project E (Portfolio tile)**, separate spec. Add a tile linking to Sentinel.
- **v2 hardening**: per-job ephemeral container; AST scan of uploaded scenes for forbidden imports; network egress restriction per job; per-beat timeout.
- **Off-site backup of `/data`** (rsync nightly).
- **Multi-tenant**: API key to tenant lookup; per-tenant budget; per-tenant samples directory.

## Decisions log

- 2026-05-10: Decomposed scope into 5 sub-projects (A through E). Started with A.
- 2026-05-10: Approach 1 chosen for v1.
- 2026-05-10: API surface revised from JSON-with-base64-Python (rejected as user-unfriendly) to multipart project-tarball upload.
- 2026-05-10: State machine collapsed from 5-step polling to 2 blocking POSTs + 1 GET.
- 2026-05-10: D.5 review gate preserved as a real `POST /voice` step (not auto-skipped).
- 2026-05-10: Optional `?auto_approve=true` for trusted-template flow; off by default.
- 2026-05-10: No per-job sandboxing for v1; single trusted caller.
- 2026-05-10: ElevenLabs cost-discipline rules from CLAUDE.md applied (PRE/POST log lines, daily budget gate, char-count estimate).
- 2026-05-10: SKILL.md shipped inside the container (COPY in Dockerfile) and exposed via `GET /helper/skill`. Reason: callers (MCP clients, future Tier 2 agent, curl users) need authoritative best-practices guidance without cloning the repo. Treated as a static asset; rebuilt with the image when SKILL.md changes.
