---
title: MCP wrapper for Sri Studio Helper (sub-project B)
date: 2026-05-10
status: drafted autonomously while user is on break; awaiting user spec review
audience: future implementer (you, three months from now)
depends_on:
  - 2026-05-10-helper-as-a-service-design.md (sub-project A): defines the HTTP API this wrapper calls.
  - 2026-05-10-extensions-page-design.md (sub-project D, in studio repo): names this wrapper as one of the three extensions featured on /extensions.
---

# Sri Studio Helper MCP wrapper

## Goal

Expose the Helper HTTP service (sub-project A) as a Model Context Protocol server so an LLM agent (Claude Code, Claude Desktop, any MCP-aware client) can produce a Helper screencast video without the user hand-rolling a `curl` and a `tar` invocation. Single-user, local stdio transport for v1; the wrapper runs on the user's machine and calls the remote Helper service over HTTPS.

This sub-project is the second of the two extensions named on the `/extensions` showcase page (sub-project D). Its existence is the load-bearing claim for "I extended this tool to MCP."

## Non-goals

- Multi-tenant or hosted MCP (no remote stdio-over-HTTP, no per-user auth, no MCP gateway). Single user, local install.
- Auto-generation of the project tarball contents from a natural-language goal. That is sub-project A's deferred Tier 2 work; the MCP tool accepts a project directory the user has already authored, exactly like `curl` would.
- A graphical UI for inspecting jobs. The MCP client (Claude Code) IS the UI.
- Bundling the Helper service binary itself. The MCP server is a thin client; it depends on a running Helper service somewhere.
- PyPI distribution in v1. Run from a local clone via `uv run`. PyPI publish tracked in `Future work`.
- Any change to the Helper HTTP API beyond what spec A and the spec-A addendum recorded in spec D already describe (`/helper/jobs`, `/helper/jobs/:id/voice`, `/helper/jobs/:id`, `/helper/jobs/:id/log`, `/helper/skill`, `/helper/samples`, `/helper/health`, `DELETE /helper/jobs/:id`).

## Approach decision

One approach considered seriously: thin stdio MCP server in Python that maps four tools to existing Helper HTTP endpoints, accepts a local directory path for the project (and tars it internally), reads auth from env. No alternatives meaningfully different at this v1 size. Listed in `Alternatives considered` so future-me sees what was rejected and why.

## Tools exposed

Four MCP tools. Each maps to one user intent and one Helper HTTP endpoint.

| MCP tool | Maps to | Input | Returns |
|---|---|---|---|
| `helper_render_silent` | `POST /helper/jobs` (multipart tarball) | `{ project_dir: string }` (absolute path on the user's machine; server tars it before upload) | `{ job_id, preview_url, estimate_usd, status: "awaiting_review" }` |
| `helper_render_voice` | `POST /helper/jobs/:id/voice` | `{ job_id: string }` | `{ final_url, status: "done" }` |
| `helper_render_full` | `POST /helper/jobs?auto_approve=true` (one-shot) | `{ project_dir: string }` | `{ job_id, final_url, total_cost_usd }` |
| `helper_skill` | `GET /helper/skill` | (no input) | markdown string (the canonical SKILL.md, roughly 5 KB) |

`helper_render_silent` is the safe default for any LLM-driven flow: it stops at the silent-with-captions preview and surfaces the cost estimate before voice generation runs. The agent can then ask the human user (via Claude Code's normal conversation) whether to proceed; on yes, it calls `helper_render_voice`. This mirrors the silent-first cost discipline that justifies spec A's whole architecture.

`helper_render_full` is the trusted-template shortcut: it skips the review gate by passing `?auto_approve=true`. Reserved for cases where the user has explicitly told the agent "use the known-good template" and accepts the cost.

`helper_skill` returns the SKILL.md content. An MCP client should call this once at session start to load best-practices guidance into the LLM's context (so the LLM understands what a "beat" is, what scenes look like, and the silent-first discipline) before constructing a project tarball.

## Tool size-guard compliance

Per the size-guard rule called out in spec A's testing section: MCP tool outputs must be small structured objects.

| Tool | Output size |
|---|---|
| `helper_render_silent` | Few hundred bytes (URLs + status). |
| `helper_render_voice` | Few hundred bytes. |
| `helper_render_full` | Few hundred bytes. |
| `helper_skill` | Roughly 5 KB markdown. **Documented exception** (see spec A section 1, MCP fit). Well under the threshold; a one-shot preload, not per-call traffic. |

The MCP server **never returns the per-job log** (`GET /helper/jobs/:id/log`) as a tool output; logs can run hundreds of KB on a multi-beat job. If an agent needs the log for debugging, the agent constructs a curl command from `job_id` and asks the human to run it. The log endpoint exists in spec A; no MCP tool wraps it.

## Code layout

Lives in the Helper repo as a new top-level package, sibling to `sri_studio_helper/` and the (future) `helper_service/`.

```
sri_studio_helper/    (existing; the CLI pipeline)
helper_service/       (future, from spec A; the HTTP service)
mcp_server/           (THIS spec; the MCP wrapper)
  __init__.py
  __main__.py         # python -m mcp_server entry point
  server.py           # MCP server registration + tool dispatch
  tools.py            # one function per tool, calls helper_client
  helper_client.py    # thin httpx wrapper over the Helper HTTP API
  tar_project.py      # tar a local directory into a tempfile, with size pre-check
  config.py           # reads HELPER_BASE_URL + HELPER_AUTH_KEY from env
  pyproject.toml      # mcp_server-specific deps (mcp, httpx) via uv
  tests/
    test_tools.py     # mocked httpx responses for each tool
    test_tar.py       # size pre-check refuses oversize dirs
    fixtures/
      tiny_project/   # smallest valid project tarball for integration tests
```

The package is its own `pyproject.toml` so it can later be PyPI-published independently of the rest of the repo.

## Transport and distribution

**Transport (v1):** local stdio. The MCP server reads JSON-RPC framed requests on stdin, writes responses on stdout, and is launched per-session by the MCP client.

**Distribution (v1):** run from a local clone of the Helper repo via `uv`. No PyPI publish, no Docker image.

**Claude Code installation snippet** (the user pastes this into `~/.claude/mcp.json` or per-project `.claude/mcp.json`):

```jsonc
{
  "mcpServers": {
    "sri-studio-helper": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "D:/Python Applications/Sri Studio Helper",
        "python", "-m", "mcp_server"
      ],
      "env": {
        "HELPER_BASE_URL": "https://studio.sshub.dev",
        "HELPER_AUTH_KEY": "<paste from 1Password>"
      }
    }
  }
}
```

**Future distribution paths** (tracked, not in v1): PyPI publish for `uv tool install sri-studio-helper-mcp`; bundled Docker image that includes both helper service + MCP server for self-hosting; remote MCP via streamable HTTP for multi-user access.

## Auth and config

Two env vars, read by `mcp_server/config.py` at server boot. Server exits 1 with a clear stderr message if either is missing.

| Env var | Purpose |
|---|---|
| `HELPER_BASE_URL` | Where the Helper service lives. Default `https://studio.sshub.dev`. Override for local-loopback testing (`http://127.0.0.1:8001`). |
| `HELPER_AUTH_KEY` | The static API key from spec A's auth model. Sent in every request as `X-Helper-Key`. |

The server itself has no second auth layer; if you can launch the MCP server, you're trusted (you're already running arbitrary code on the user's machine via the MCP client).

## Tar handling

`helper_render_silent` and `helper_render_full` accept a local `project_dir` path. The server:

1. Verifies the directory exists and is readable.
2. Walks the tree, sums file sizes. If total > 25 MB (spec A's nginx upload cap), refuses with a structured error: `{ error: "project_too_large", size_bytes: ..., limit_bytes: 26214400 }`.
3. Tars to a tempfile (gzip compression).
4. POSTs as multipart `project=@<tempfile>`.
5. Deletes the tempfile after the upload completes (success or failure).

The server does NOT scan the directory for secrets. Spec A documents that as a caller responsibility, and "the caller" here is the user invoking the MCP tool. If the user's project contains a `.env`, it gets uploaded.

## Failure modes (what tools return when things go wrong)

Each tool catches the obvious failure modes and returns a structured error object instead of crashing the MCP server. Errors are MCP `isError: true` responses with a JSON payload.

| Failure | Returned to LLM |
|---|---|
| `HELPER_BASE_URL` unreachable | `{ error: "helper_unreachable", base_url: ... }` |
| Auth rejected (401) | `{ error: "auth_failed", suggest: "check HELPER_AUTH_KEY env var" }` |
| Project dir does not exist | `{ error: "project_dir_not_found", path: ... }` |
| Project too large (> 25 MB) | `{ error: "project_too_large", size_bytes: ..., limit_bytes: ... }` |
| Daily budget exceeded (402 from `/voice`) | `{ error: "would_exceed_daily_cap", remaining: ..., needed: ..., suggest: "shorten beats voiceover, or wait until daily reset" }` |
| Job not found (404) | `{ error: "job_not_found", job_id: ... }` |
| Helper service 5xx | `{ error: "helper_error", status: ..., body: ... }` (body truncated to 200 chars per size-guard rule) |
| Network timeout | `{ error: "timeout", endpoint: ... }` |

The MCP server crashing entirely (Python exception not caught) is itself a failure mode the MCP client surfaces. Tests assert each of these returns a structured error, not an unhandled exception.

## Testing

**Per-component fail-fast probes (during build, per project rule):**

| Component | Probe |
|---|---|
| MCP server boot | `python -m mcp_server` with valid env, send a tools/list request via stdin, assert all four tools listed. |
| `helper_skill` | Run against a fake helper that serves SKILL.md from the repo, assert returned markdown matches. |
| `helper_render_silent` | Run against a fake helper that returns canned `{ job_id, preview_url, estimate_usd }`, assert tool returns the same shape with no extra fields. |
| Tar handling | Run on `tests/fixtures/tiny_project/`, assert tempfile produced + has gzip magic bytes + contains expected entries. |
| Size guard | Synthesize a 26 MB fake dir, assert `helper_render_silent` returns `project_too_large`. |
| Auth missing | Unset `HELPER_AUTH_KEY`, launch server, assert exit 1 with a clear stderr message. |

**Persistent test suite (`mcp_server/tests/`, runs in CI):**

- `test_tools.py`: each tool, happy path + each documented failure mode, with `httpx` mocked.
- `test_tar.py`: tar a fixture dir, verify contents; size-guard refusal.
- `test_config.py`: env var presence, base URL normalization (trailing slash handling).
- `test_size_guard.py`: documented in spec A's size-guard rule; assert no tool returns more than 5 KB on a worst-case fake response.

**Integration test (one big end-to-end):**

- Spin up a fake Helper API on localhost (FastAPI) that mirrors the spec-A endpoints.
- Spin up the MCP server pointing at that fake.
- Invoke `helper_render_silent` with a tiny fixture project, assert the response shape.
- Invoke `helper_render_voice` with the returned `job_id`, assert the response shape.
- Invoke `helper_skill`, assert markdown returned.

**Manual smoke (after Helper service is live on the VPS):**

- Configure Claude Code with the MCP server snippet above.
- In a fresh Claude Code session, ask "use the helper to render the find_evil_demo project". Assert the LLM calls `helper_render_silent`, surfaces the preview URL, surfaces the cost estimate, and pauses for human approval before calling `helper_render_voice`.

## Cross-spec touches

This spec consumes spec A unchanged plus the one already-recorded spec-A addendum (the public `/helper/samples` endpoint, called out in spec D section 9, applied to A's implementation tasks).

This spec records ONE new spec-A addendum here:

- The Helper HTTP API responses for `POST /helper/jobs` and `POST /helper/jobs/:id/voice` MUST include the existing fields `{ job_id, preview_url, estimate_usd, status }` and `{ final_url, status }` respectively at minimum, since the MCP wrapper depends on them. Spec A already specifies these fields, so this is a check, not a new requirement. If implementation drifts (e.g. renames `preview_url` to `silent_url`), update both spec A and this spec.

## Future work (tracked, not in v1)

- PyPI publish (`sri-studio-helper-mcp`) so `uv tool install sri-studio-helper-mcp` is the install path; v1 requires a local clone.
- Remote MCP transport (streamable HTTP) so multi-user invocation is possible without each user running a local stdio server. Pairs with multi-tenant Helper service from spec A's future work.
- A `helper_jobs_list` tool that paginates the user's recent jobs. Useful for "what did I render last week" queries; not load-bearing for v1.
- A `helper_render_silent_from_url` variant that fetches a project tarball from a URL the LLM can produce, instead of requiring a local path. Useful for cases where the LLM is constructing the project itself rather than referencing one the user already has on disk.
- A `helper_explain_log` tool: takes a `job_id`, fetches the log, summarizes failure cause for the LLM in <500 chars (preserving the size-guard discipline). Useful for "why did my render fail" queries; needs careful summarization to avoid blowing the size budget.

## Alternatives considered

### Remote MCP server hosted alongside the Helper service

Run the MCP server in the same container as the Helper HTTP service; expose over streamable HTTP so multi-user invocation is possible without per-user local installs. Rejected for v1 because:

- Single-user system today; the user is the only one calling Helper.
- Adds an HTTP-MCP transport surface to the container and requires per-user auth on top of the Helper auth key (otherwise everyone shares one MCP session).
- Adds a second set of operational concerns (streaming HTTP, session resumption) without a real demand.
- Re-visit when the Helper service goes multi-tenant (tracked in spec A's future work).

### A "fat" MCP tool that auto-generates the project from a goal

`helper_render_from_goal({ goal, url, codebase_dir })`: the MCP server uses an LLM to plan beats + scenes + voiceover, tars them into a project, calls Helper. Rejected for v1 because:

- This is the Tier 2 / Auto mode work explicitly deferred in spec A. Building it inside the MCP wrapper would mean the planning logic lives in the MCP server instead of the Helper service, which is the wrong layer.
- An LLM agent calling `helper_render_silent` with a hand-authored project is not meaningfully more work for the user than writing a goal; the agent constructs the project files in a local dir, then calls one tool.
- Re-visit when spec A ships Tier 2; at that point, expose a `helper_render_from_goal` tool that simply forwards to the new endpoint.

## Decisions log

- 2026-05-10: Drafted autonomously while user on break; awaiting user review per the brainstorming skill's user-review gate.
- 2026-05-10: Stdio transport over HTTP-MCP. Reason: single-user, local install, avoids per-user auth on top of Helper auth.
- 2026-05-10: Four tools (silent, voice, full, skill) chosen to mirror spec A's HTTP endpoints. No log-fetching tool to preserve size-guard discipline.
- 2026-05-10: Code lives in the Helper repo under `mcp_server/`, sibling to `sri_studio_helper/` and (future) `helper_service/`.
- 2026-05-10: v1 distribution = local clone + `uv run`. PyPI tracked in future work.
- 2026-05-10: `project_dir` (path to a local directory) chosen over base64-encoded tarball or per-file JSON. Reason: smallest LLM-facing input surface, easiest for the LLM to produce, lets the MCP server handle the tar mechanics.
- 2026-05-10: Tool returns are restricted to small structured objects (per spec A's size-guard rule); `helper_skill` is the documented exception at ~5 KB.
- 2026-05-10: No log-fetch tool. Logs run hundreds of KB; if the LLM needs them, it constructs a `curl` and asks the human to run it.
- 2026-05-10: Two env vars (HELPER_BASE_URL, HELPER_AUTH_KEY) only. No second auth layer on the MCP server.
