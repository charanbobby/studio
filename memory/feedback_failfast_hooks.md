---
name: Fail-fast hooks installable per project
description: A two-layer hook gate (Claude PreToolUse + git pre-commit) enforces the fail-fast rule from CLAUDE.md by blocking edits / commits to runtime files unless a fresh probe marker exists. Installable in any project via D:/.claude-seed-memory/install-failfast.sh.
type: feedback
---

The fail-fast rule from `~/.claude/CLAUDE.md` says: probe before committing code into any runtime artifact. That rule has been violated multiple times across projects. Memory alone has not been sufficient to enforce it.

**Why:** On 2026-05-01 (Find Evil hackathon), three of eight commits in a single session shipped without runtime probes despite the rule being prominent in CLAUDE.md and project memory. The user said: "What do we do to bake this into you? We always need to run fast." Memory-only enforcement is too easy to rationalize away in the moment.

**How to apply:**

When starting any new project where I will be writing runtime code (pipelines, services, scripts that exercise live systems), suggest installing the fail-fast hook system:

```
bash D:/.claude-seed-memory/install-failfast.sh
```

The installer adds, into the current git project:

- `scripts/probe.sh` - wrapper. Usage: `scripts/probe.sh <target-file> -- <command>`. On exit 0 it writes `.probes/<sanitized>.lastrun`.
- `scripts/fail-fast-gate.sh` - PreToolUse hook script. Blocks Edit/Write/MultiEdit on enforce-listed files unless a fresh marker exists.
- `scripts/pre-commit-fail-fast.sh` - same logic at commit time.
- `.probes/.gitignore` - gitignored marker dir.
- `.failfast.list.example` - starter config.
- `.git/hooks/pre-commit` - local stub that calls the tracked script.

After install, two manual steps:

1. `cp .failfast.list.example .failfast.list` and edit with project-specific glob patterns (one per line).
2. Append this `PreToolUse` block to `.claude/settings.json` under `hooks`:

```json
"PreToolUse": [
  {
    "matcher": "Edit|Write|MultiEdit",
    "hooks": [
      {
        "type": "command",
        "command": "bash scripts/fail-fast-gate.sh",
        "timeout": 10
      }
    ]
  }
]
```

**Config opt-in by design:** if `.failfast.list` does not exist, the gate is a no-op. So copying the scripts into a new project does not automatically enforce; the project owner explicitly opts in by adding paths to the list. This avoids breaking projects where the hooks are installed but not yet configured.

**The marker freshness rules:**
- Marker mtime must be >= the target file's mtime (every new edit forces a re-probe).
- Marker must be no older than 60 minutes.
- If both conditions hold, the gate allows the edit / commit.

**Bypass:** `git commit --no-verify` exists but the project CLAUDE.md typically forbids hook bypass; only use it with a documented reason.

**Limits of this enforcement:**
- The gate cannot inspect probe content. It only checks "you ran something targeting this file recently". Running a fake probe (`echo ok`) defeats the gate. The probe wrapper requires the target file as the first argument, so the marker is at least file-scoped, but the wrapper does not validate that the probe actually exercises the planned change.
- Gate fires on Claude-driven Edit/Write only. If the user edits the file directly in their IDE, no gate runs. Pre-commit catches that case.

**Source of truth:** the canonical scripts live at `D:/.claude-seed-memory/install/scripts/`. To update across projects, edit there and re-run `install-failfast.sh` in each project (the installer skips files that already exist; delete the project copies first if you want to re-install).
