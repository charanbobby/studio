# Sri Studio - Build Journal

Chronological log of the surprises, pivots, and small disasters that shaped the build. One entry per high-value moment, not one per commit.

---

## 2026-05-07 08:30 - Spec rebrand to Sri Studio with a live URL target

**What happened:** The first design draft framed the deliverable as a CLI-only reel generator. After a brainstorming pass with Claude Code I rewrote the spec to add a Next.js frontend, a FastAPI wrapper, and a live deployment to studio.sshub.dev. ADR-005 and ADR-011 captured the two halves.

**What surprised me:** The frontend half-day was scarier on paper than in practice once I committed to Tailwind defaults and a deliberately spartan UI. The deployment was the real cost driver, not the React work.

**What I changed because of it:** Promoted the human-approval gate from stretch to required at the same time (commit `a47ffe6`); a deployed URL needs a hard cost wall in front of the assessor. Rebranded the package and added the deployment to the spec (commit `0ccd93d`).

**Linked decision record:** docs/decisions/005-frontend-included-nextjs-fastapi.md, docs/decisions/011-sri-studio-name-and-studio-sshub-dev-deployment.md

---

## 2026-05-07 09:00 - ADR-001: the n8n to LangGraph pivot

**What happened:** The JD lists "n8n preferred" as a tooling signal. After running the brainstorming skill against the requirements I picked LangGraph instead and wrote ADR-001 to defend the choice in the walkthrough.

**What surprised me:** The decision felt risky in the abstract ("am I picking against the interviewer?") and obvious in concrete ("n8n cannot model my retry semantics or shared typed state cleanly"). Writing the ADR collapsed the abstract risk into concrete tradeoffs I was happy to defend on camera.

**What I changed because of it:** Made the "respect for n8n in its lane" framing explicit in both the ADR and the walkthrough script; the goal is "I picked the right tool for the problem," not "n8n is bad."

**Linked decision record:** docs/decisions/001-langgraph-over-n8n.md

---

## 2026-05-07 09:30 - Probe 09 found Langfuse v4, not v2

**What happened:** Probe 09 was supposed to confirm the Langfuse Python SDK works with my `with_span` decorator pattern. The first attempt followed the v2-shape examples I had cached from an older project. They failed cleanly: the SDK API had moved on.

**What surprised me:** How much of the official documentation and Stack Overflow answers I found were still v2. The v4 SDK uses a different decorator surface, a different client construction pattern, and a different way to attach cost to a span.

**What I changed because of it:** Rewrote `backend/tracing/langfuse_client.py` against v4 only; pinned the SDK version in `pyproject.toml`; re-ran the probe to exit clean (commit `89bcf5e`). Added a note to ADR-006 to remind future-me that v4 is now baseline.

**Linked decision record:** docs/decisions/006-langfuse-cloud-tracing.md

---

## 2026-05-07 10:00 - Probe 10 found Replicate's 6-per-minute rate limit

**What happened:** Probe 10 is the end-to-end smoke test against real services. The first run looked fine for a single scene but threw a 429 the moment I asked for a multi-scene plan. Replicate enforces a 6-per-minute rate limit on Flux Schnell at my account tier.

**What surprised me:** The rate limit was nowhere in the obvious docs and only surfaced empirically. If I had skipped probe 10 the failure would have shown up mid-pipeline on the first 90-second reel, after I had already paid for TTS.

**What I changed because of it:** Added explicit 429 backoff to `backend/media/replicate_flux.py` (commit `8ae6524`). The exponential delay is computed from the response headers when present and falls back to a fixed schedule otherwise. Cited the discovery in ADR-002 and ADR-009.

**Linked decision record:** docs/decisions/009-fail-fast-probe-matrix-as-phase-gate.md

---

## 2026-05-07 11:00 - Captions for free via ElevenLabs alignment

**What happened:** Probe 02 was meant to confirm the TTS endpoint works with my voice clone ID. I noticed in the response payload that ElevenLabs returns a `chars` array with per-character start and end timestamps when you ask for `with-timestamps`. That meant captions could come from the same call as the audio, no Whisper post-process required.

**What surprised me:** I had budgeted half a day for a Whisper sidecar service. The alignment payload eliminated the entire dependency.

**What I changed because of it:** Wrote ADR-007 the same morning to lock in the decision and avoid re-litigating it later. Added a `_chars_to_words` helper to `backend/media/elevenlabs_tts.py` (commit `eb1091b`) that does a deterministic char-to-word grouping. Added probe 06 to confirm the resulting ASS file syncs within 100ms of the audio.

**Linked decision record:** docs/decisions/007-captions-via-elevenlabs-alignment.md

---

## 2026-05-07 12:00 - Pydantic validation retry on Plan node

**What happened:** Plan node returned a `ScriptPlan` JSON that failed Pydantic validation on the second test prompt. The model had nested `scenes` under `plan` instead of returning it at the top level, against the schema I had pinned in the prompt.

**What surprised me:** The fix was not to write a more emphatic prompt; it was to feed the validation error back into the next attempt and let the model correct itself. Two retries was enough to get a valid plan in every test case.

**What I changed because of it:** Added a retry loop with validation-error feedback to `backend/src/reel_gen/nodes/plan.py` (commit `9991511`). On a third failure the node falls back to a deterministic template plan so the pipeline always ships something.

**Linked decision record:** docs/decisions/009-fail-fast-probe-matrix-as-phase-gate.md (retry pattern documented as project standard)

---

## 2026-05-07 14:00 - Phase 7 e2e revealed bg.add_task to asyncio.create_task fix

**What happened:** First end-to-end run through the API failed silently after returning the run ID. Logs showed the run record was created but the LangGraph state machine never started. I had wired the long-running pipeline behind FastAPI's `BackgroundTasks.add_task`, which expects sync callables; my pipeline was async.

**What surprised me:** The failure mode was a quiet swallow, not a loud error. Background tasks that are coroutine objects are not awaited by `BackgroundTasks`; they sit on the event loop as un-awaited futures.

**What I changed because of it:** Switched the run kickoff from `bg.add_task(run_pipeline, run_id)` to `asyncio.create_task(run_pipeline(run_id))` inside the route handler, with the resulting task tracked by the run registry so cancellation works. Confirmed with a log line on every node entry that all four nodes fire end-to-end (commit `3c997b6`).

**Linked decision record:** docs/decisions/010-runs-as-filesystem-no-database.md (run registry section)

---

## 2026-05-07 14:45 - Phase 7 e2e revealed an ffmpeg path-resolution bug

**What happened:** Same e2e session: the Stitch node ran ffmpeg and reported success, but the resulting `reel.mp4` was zero bytes. ffmpeg had been writing to a path that resolved relative to the wrong working directory inside the container.

**What surprised me:** ffmpeg returned exit code 0 even though the output file was empty. The check that caught it was a stat-after-success in `backend/media/ffmpeg_stitch.py` that I had added "just in case" for fail-fast.

**What I changed because of it:** Switched every path passed to ffmpeg in the Stitch node to absolute paths resolved from the run directory. Added a stat assertion that the output file is at least 1KB before the node returns success. Re-ran the smoke test green (commit `18c0ea7`).

**Linked decision record:** docs/decisions/009-fail-fast-probe-matrix-as-phase-gate.md (the "stat-after-success" pattern is now a project standard)

---

## 2026-05-07 16:00 - Phase 8 hit gitignore-shadowing on frontend/app/runs/

**What happened:** Built the `/runs` history page and the `/runs/[id]` detail page in Next.js. Pushed the commit. The `frontend/app/runs/` directory and both `page.tsx` files were missing from the working tree on the deploy box.

**What surprised me:** Root-level `.gitignore` had a `runs/` entry to keep generated reel artifacts out of the repo. That pattern was unanchored, so git was also ignoring `frontend/app/runs/`. The frontend pages never got committed.

**What I changed because of it:** Anchored the ignore pattern to repo root: `/runs/` instead of `runs/` (commit `a910b5c`). Force-added the missing page files, verified with `git check-ignore -v` that the frontend path is now tracked, redeployed.

**Linked decision record:** docs/decisions/010-runs-as-filesystem-no-database.md (the runs-as-filesystem choice is what created the gitignore in the first place)

---

## 2026-05-07 17:30 - Deploy script and first-time host setup

**What happened:** Wrote the deploy script and the nginx config for studio.sshub.dev (commits `40e1c8d`, `cb5b401`). First deploy attempt failed because shell scripts had been checked in with CRLF line endings from Windows.

**What surprised me:** The error was the classic `bad interpreter: /bin/bash^M` and only showed up on the Linux host. Windows-side `bash scripts/deploy.sh` had run cleanly because Git Bash tolerates the line endings.

**What I changed because of it:** Added a `.gitattributes` rule to force LF for `*.sh` (commit `165c69d`); rewrote the affected scripts in place; restored the executable bit on the host (commit `74bdfb2`). Deploy went green; SSE keep-alive timeouts in the nginx block were the second-pass fix and went in clean.

**Linked decision record:** docs/decisions/011-sri-studio-name-and-studio-sshub-dev-deployment.md, docs/decisions/012-basic-auth-and-daily-cost-cap.md

---

## 2026-05-07 19:30 - ADR backfill pass

**What happened:** Ran a final pass to backfill ADR-001 through ADR-012 (commit `7c5a2d3`) so every meaningful decision in the build has a one-page record at sign-off. The questionnaire draft and the walkthrough script both reference these by number.

**What surprised me:** Twelve decisions in five days felt like a lot until I read them back. Each one is a real choice with a defensible rationale, not a stylistic preference. The volume reflects the surface area of the build, not over-documentation.

**What I changed because of it:** Locked the ADR set; future changes get a new ADR rather than an edit to an existing one. The `docs/` harvest (this journal, the walkthrough script, the questionnaire draft, and the diagrams.html) was the next and final task.

**Linked decision record:** docs/decisions/ (all 12)
