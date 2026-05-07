---
name: _resume.md is the session-continuation primer
description: On break/pause/session-end, rewrite `_resume.md` at the repo root, not `resume.md`, not in `docs/`, not a new file
type: feedback
---
When the user signals a break ("taking a break", "continuing later", "update the resume file", "pause here", or similar), **rewrite `_resume.md` at the repo root of the active project** with the current state.

**Why:** `_resume.md` is the user's established convention. The leading underscore marks it as ephemeral, rewritten per break, pasted into the next Claude Code session's opening prompt, then deleted. It is NOT a rolling doc, NOT in `docs/`, and NOT called `resume.md`. Creating a new file in the wrong place wastes the user's time and clutters the repo.

**How to apply:**

1. **Always `Glob "**/*resume*"` (or read repo root) first** to find the existing file. Don't search for the exact name you expect.
2. **Read the existing `_resume.md` before overwriting** to match its established structure and tone.
3. **Before writing, scan for parallel work.** The user runs things between sessions. Check mtimes on common output / docs / runbook directories for anything newer than the previous `_resume.md`'s own mtime. If found, incorporate it; don't carry stale claims forward. **Reason:** on 2026-04-19 I re-signed a stale resume that named an outdated milestone while the user had actually finished several more milestones in parallel, produced output JSON, and authored new artifacts. The user had to correct me.
4. **Standard sections:**
   - **Frontmatter block with `last_updated: <ISO timestamp + tz>`** at the very top. Future-Claude needs to know how stale the file is before trusting any named path.
   - Header with date plus short state descriptor plus `(ephemeral, delete after use)` suffix
   - Opening paragraph: "paste this into a new Claude Code session and say 'resume from here.' Auto-memory loads on its own; don't repeat what's already in `memory/MEMORY.md`. Verify any specific path/command below still exists; this file was true at the timestamp above."
   - `## Where we are (YYYY-MM-DD)`: 1-2 paragraphs on current state plus what's NOT yet verified
   - `## Files that matter most (read in order)`: numbered list, canonical docs first (`memory/MEMORY.md`, `docs/planning/PLAN.md`, the active runbook, the notebook, the server)
   - `## What changed this session (not in memory, won't be obvious from git)`: the delta this session added; explain **why** each change, not just what
   - `## Immediate next steps (when user returns)`: numbered, actionable, in a `text` code block for copy-paste
   - `## What Claude should do on resume`: greet briefly, don't assume verification state, don't re-litigate locked decisions
   - `## Anti-patterns from this session (don't repeat)`: own this session's mistakes plus standing don'ts
   - `## Open questions / offers`: items Claude offered that the user hasn't answered
5. **Tone:** first-person-plural ("we"), terse, commit-message dense. No fluff. Code blocks for step-by-step, tables sparingly.
6. **Do NOT create `docs/resume.md`, `RESUME.md`, `notes.md`, or any other variant.** Just `_resume.md` at the repo root.

**When the user explicitly says to delete it after resuming, delete it.** Don't preserve it "just in case."
