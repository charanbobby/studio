# AI Questionnaire (Component C) - Draft

This is a starting draft. Each section leads with this build's evidence (commits, ADRs, probe artifacts) and marks `[POLISH]` where the user needs to add personal voice or specifics from prior projects.

---

## Q1. How many hours per week do you spend using AI tools?

- 25 to 35 hours per week, sustained, across personal projects and client work.
- Claude Code is the primary surface; multi-hour sessions are typical, with a single project session often spanning a full workday.
- Time covers: design conversations, code generation, debugging, deployment, documentation, retrospectives.
- Not just chat: tool-calling agents that read files, run shells, hit external APIs, and edit code in place.
- [POLISH] Add a sentence on the user's own week: rough split between AI-assisted vs. unassisted work, and any non-AI deep-focus time the user deliberately preserves.

---

## Q2. Which AI tools do you actively use?

Lead with the tools used in this build, then expand:

- **Claude Code (Anthropic):** primary engineering surface. Used for all design conversations, code generation, debugging, and orchestration in the Sri Studio build.
- **OpenRouter:** unified API for Claude Sonnet (planning) and Claude Haiku (extraction). Picked over the direct Anthropic SDK for provider portability and unified billing.
- **ElevenLabs:** Instant Voice Clone for narration; the same `with-timestamps` call returns character-level alignment used to burn captions (ADR-007).
- **Replicate:** hosted Flux Schnell for scene image generation at $0.003 per image, native 9:16 (ADR-002).
- **Langfuse Cloud:** per-call tracing on every LLM invocation; free tier covers dev plus assessor traffic (ADR-006).
- **n8n:** active in adjacent projects for SaaS glue and webhook routing where visual workflows are the right tool. Deliberately not used here (ADR-001) because the problem shape favored typed Python state.
- **GitHub Copilot / Cursor / Codex:** [POLISH] state which the user uses regularly vs. tried-and-dropped, and why.
- [POLISH] Add any other model providers the user keeps active subscriptions to (OpenAI direct, Gemini, Perplexity, etc.).

---

## Q3. Describe an automation you have built.

- Built **Sri Studio**: a tool that turns a one-sentence prompt into a 90-second vertical reel narrated in my cloned voice. Built in five days for the CSC take-home; live at studio.sshub.dev.
- **Tools:** LangGraph for orchestration, FastAPI backend with Server-Sent Events, Next.js 14 frontend with Tailwind, Claude Sonnet via OpenRouter for planning, Claude Haiku for intent extraction, ElevenLabs Instant Voice Clone for TTS plus alignment, Replicate Flux Schnell for visuals, ffmpeg for stitching, Langfuse Cloud for tracing.
- **Pipeline:** four nodes (Extract -> Plan -> Approval Gate -> Execute -> Stitch) with mandatory human review of the plan before any paid generation runs. Plan node writes a `plan.json` artifact to disk that the human (or assessor) reviews scene by scene in the frontend.
- **Cost discipline:** about $0.03 per 5-second reel, about $0.25 per 90-second reel. A daily cost cap stored as a JSON ledger aborts new runs the moment the day's running total would exceed the cap; the check fires before the paid call, not after, so a leaked password cannot blow the budget.
- **Deployed:** studio.sshub.dev with HTTP basic auth at nginx, Let's Encrypt TLS, Docker Compose, on a Hetzner Cloud VM. Two credential pairs: one for me, one for CSC scoped to the interview window.
- **Evidence:** `docs/decisions/001-langgraph-over-n8n.md` through `012-basic-auth-and-daily-cost-cap.md`; ten fail-fast probe scripts in `backend/experiments/`; full git history in the repo.
- [POLISH] Add a one-line "what I will keep using this for" sentence so the answer reads as a personal tool, not an interview artifact.

---

## Q4. Describe the most complex production deployment you have shipped.

- **Sri Studio (this build) is itself a production deployment.** Live at studio.sshub.dev on Hetzner Cloud. Two-service Docker Compose (FastAPI backend + Next.js frontend), nginx reverse proxy with Let's Encrypt TLS, HTTP basic auth at the nginx layer with two credential pairs (one long-lived for me, one short-lived for CSC), SSE keep-alive timeouts tuned for long-running runs, named volume for run artifacts that survive container restarts, secrets in `.env` on the server only. Daily cost cap at the application layer prevents runaway spend regardless of who is authenticated.
- **Operational rigor:** `APP_VERSION` bumped on every deploy so I can tell which build is live by hitting `/healthz`. Deploy script reuses an existing Hetzner pattern shared across the sshub.dev family of subdomains.
- [POLISH] Second example: if the user has a Find Evil DFIR pipeline or another prior production system to cite, add it here with its own complexity callouts (worker queues, multi-tenant data, scale, etc.).
- [POLISH] Optional third example: another shipped subdomain at sshub.dev that demonstrates the reused pattern (Fair Play, MaplePulse, etc.).

---

## Q5. Describe a manual process you translated into automation.

- [POLISH] Lead with a non-AI manual process the user has personally automated. Candidates from prior projects: the Fair Play document-to-database pipeline, the Find Evil DFIR triage flow, or any client-side process where the user replaced a multi-step human procedure with a typed Python workflow.
- Frame the answer in three beats: the manual procedure as it existed, the failure modes that pushed the user to automate, and the design choices that survived the translation.
- Connect back to this build: the same pattern shows up in Sri Studio. The manual procedure was "write a brief, plan scenes, write voiceover, find b-roll, record audio, edit, caption, export." The automation collapses it into one prompt plus one approval click while preserving the human review at the only step where judgment matters: approving the plan before spending money on generation.
- [POLISH] One concrete metric on time saved or volume increased.

---

## Q6. How do you handle pushback on AI-driven decisions?

- The cleanest example from this build is **picking LangGraph over n8n**, against a JD signal that listed n8n as preferred.
- Reasoning is documented in `docs/decisions/001-langgraph-over-n8n.md`. Three concrete grounds: (1) the pipeline is a stateful AI graph with typed Pydantic state and conditional retries on validation errors, which LangGraph models natively; (2) the JD allows "or similar" explicitly, so I am inside the spec; (3) my fail-fast probes are written in Python against the same SDKs the production code uses, so there is no second runtime to maintain.
- I do not minimize n8n. The ADR is explicit that n8n is the right tool for SaaS glue and webhook routing; it is the wrong tool for typed Python AI graphs with bespoke retry semantics.
- The pattern: I treat pushback as a request for evidence, not a request for compliance. If the evidence supports the original decision, I write it down (an ADR) so the reasoning is auditable. If the pushback is right, I update the design.
- [POLISH] Add a non-build example: a time the user pushed back on AI output that turned out to be wrong, or a time someone pushed back on the user's AI-driven decision and the user updated.

---

## Q7. What parts of your process do you keep human-only?

- **Mandatory human-approval gate between Plan and Execute.** This is the answer for this build. After the Plan node writes `plan.json`, the LangGraph state machine pauses. The frontend renders the plan scene by scene: hook, voiceover script, per-scene visual prompts, motion type, music mood. The pipeline only resumes on an explicit Approve click. ADR-005 (frontend) and the spec section 2 cover the design.
- Three specific reasons it is non-negotiable:
  1. **Cost bound:** a wrong plan never burns image-gen / TTS / music spend. About $0.015 spent on Extract + Plan vs about $0.25 wasted if a bad plan ran all the way through Execute.
  2. **Evidence boundary:** the human reads the structured plan, not the freeform prompt. The model cannot hide a misinterpretation in plain prose; it has to commit to scenes, motion, and voiceover text in JSON.
  3. **Trust signal:** the assessor sees, on camera, that this pipeline cannot accidentally spend money without a human click. That is the answer to Q7 made visible.
- **Voice clone identity:** the voice ID is user-supplied via `.env`, never auto-generated or auto-selected. The model cannot decide to sound like someone else.
- **NSFW retry is deterministic, not autonomous:** when Replicate Flux rejects a prompt as NSFW (probe 04 documented the error string), the rewrite is a fixed transformation, not a "let the model figure it out" loop.
- **Cost cap is a hard wall, not a soft warning:** cap-breaching runs abort cleanly; the model never gets to "decide" whether to proceed past budget.
- [POLISH] Optional one-liner on a category the user keeps human-only across all projects (final review of any external-facing copy; final sign-off on any client-billed deliverable; etc.).

---

## Q8. How do you prevent or catch AI errors before they cause damage?

Five mechanisms shipped in this build:

- **Pydantic validation on every model output.** `backend/src/reel_gen/nodes/plan.py` validates Claude Sonnet's JSON output against the `ScriptPlan` model. On validation failure the node retries up to twice with the validation error fed back into the prompt; on a third failure it falls back to a deterministic template plan so the pipeline always ships a reel.
- **Deterministic NSFW retry.** `backend/src/reel_gen/media/replicate_flux.py` catches Replicate's NSFW rejection (error string documented in probe 04) and retries once with a deterministically rewritten safer prompt. No autonomous "let the model decide" loop.
- **Graceful degradation in Execute.** `backend/src/reel_gen/nodes/execute.py` falls back to a solid-color frame with the scene's voiceover excerpt overlaid if a single scene image fails after retries. One bad image never kills the whole run. Music failures degrade to silence; Stitch handles it cleanly.
- **Cost cap pre-check.** `backend/src/reel_gen/llm/cost_cap.py` checks the day's running total before any paid call. Cap-breaching requests abort with a 402 and zero spend. The wall is dollar-amount, not user-identity, so a leaked basic-auth password cannot blow the budget.
- **Fail-fast probe matrix as phase gate.** Ten probe scripts in `backend/experiments/probe_*.py` against every external service; node code is not committed until the corresponding probe exits zero. ADR-009 documents the discipline. Caught real surprises: Langfuse v4 vs v2 SDK shape (probe 09), Replicate's 6-per-minute rate limit (probe 10), ElevenLabs alignment shape (probe 02).
- **Per-call tracing in Langfuse Cloud** wraps everything: every LLM call has a span, every span has cost attached, every run is replayable from the trace. ADR-006.
- [POLISH] Add a one-line "this is not new for this build" sentence pointing at the user's standing rule across projects (the global CLAUDE.md fail-fast rule, the "print pricing breakdown before AND after every LLM call" rule, etc.).

---

## Q9. How do you stay current with the AI landscape?

- [POLISH] This is the most personal question. Lead with the user's actual practice; bullets below are scaffolding.
- Newsletters / RSS the user reads weekly: [POLISH].
- Practitioner accounts followed (Twitter/X, LinkedIn, Bluesky): [POLISH].
- Hands-on practice: every new model release the user tries on a known benchmark task within a week of launch. Cite a recent example.
- Communities: [POLISH] Discord, Slack, or local groups the user is active in.
- Building as the way to learn: this build itself is the answer. Five days from spec to shipped product against a model stack (Claude Sonnet, ElevenLabs voice clone, Flux Schnell, Langfuse v4) where most components had a meaningful API change in the last six months.
- Conferences / talks: [POLISH] any the user has attended or spoken at.
- Anti-pattern the user avoids: [POLISH] one sentence on what the user does NOT do (e.g., does not chase every model launch, does not consume "hot take" threads, does not depend on YouTube tutorials for technical depth).

---

## Closing pattern (use as a sign-off line on the questionnaire)

> I identify problems, design solutions, choose technologies, craft prompts, and direct architecture. Claude Code turns those decisions into working code, fast and reliably. The skill is knowing what to build and when to intervene.
