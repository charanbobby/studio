---
name: Prefer tracked markdown runbooks over in-session instructions
description: For multi-step procedures, write instructions into a committed markdown runbook (with checkboxes), not as chat-only output
type: feedback
---
When the user needs to execute a multi-step procedure (install, setup, migration, data prep, deployment, anything spanning more than a single session), put the instructions in a **markdown runbook file inside the project** (e.g. `docs/runbooks/<topic>-runbook.md`) with GitHub-flavored checkboxes so the user can tick items off as they go.

**Why:** First surfaced 2026-04-17. Claude Code sessions are ephemeral; instructions given only in chat disappear when the session ends. The user works across many sessions, often days apart. A persistent runbook lets them pick up exactly where they left off without re-asking. The user's words: *"cloud code instructions disappear so this is one way of saving everything."*

**How to apply:**

- Any procedure with more than 2 steps goes in a runbook, not chat.
- Use `- [ ]` checkboxes for every executable step so progress is visible at a glance.
- Chat responses become *pointers* to the runbook ("Updated Step 5 in [docs/runbooks/foo-runbook.md](...)"), not walls of commands duplicated in chat.
- When the user completes steps, update the runbook to mark them `- [x]` so past progress is preserved.
- Keep runbooks scoped: one runbook per slice/capability/migration. When that scope closes, the runbook is archived.
- Short conceptual explanations still belong in chat. Persistent artifacts (commands, file paths, settings, troubleshooting tables) belong in the runbook.
