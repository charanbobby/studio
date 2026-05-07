---
name: Don't propose unattended / overnight agent patterns
description: Claude Code needs human-in-loop for tool approvals; plans assuming overnight autonomy are unrealistic for this user's workflow
type: feedback
---
**Don't propose workflows that require Claude (or Codex, or any agent) to run overnight unattended. Every tool call needs human approval unless the user explicitly sets up a scoped allowlist or dangerous-permissions flag, and neither is the default operational mode for this user.**

**Why:** First surfaced 2026-04-24. I suggested "run Codex overnight on well-scoped mechanical tasks while you drive Claude during focused hours" as a way to speed up tier-2 work. User correctly flagged that this ignores how permission prompts actually work; every tool call needing approval means overnight unattended operation isn't realistic. I should have anticipated that.

**How to apply:**

- When proposing multi-agent or parallel work, assume a human-in-loop synchronous session for each agent.
- Frame second-LLM help as **asynchronous dispatch** (user gives a bounded task, walks away, reviews output later), not unattended overnight operation.
- For any "while you sleep" or "in the background" phrasing, stop and re-check: does this actually require human approvals? If yes, rewrite.
- When sizing work windows, size against the user's literal available hours that day, not against idealized 24-hour throughput.
