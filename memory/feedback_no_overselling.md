---
name: Don't oversell scaffolding as engineering
description: Distinguish infrastructure/setup work from actual engineering. User pushes back on inflated framing of trivial progress.
type: feedback
---
Do not celebrate scaffolding, setup, installs, or "making the pipes connect" as an *achievement* or a *portfolio piece*. The user is calibrated and will call it out when you inflate the framing. Treat infra milestones as checkpoints, not wins.

**Why:** First surfaced 2026-04-17. After a setup slice completed (Docker plus tooling running, Claude Code answered one question on real input) the user pushed back: *"This is all Claude doing its thing and we haven't really done anything. Why is this an achievement?"* They were right. Running someone else's installer, pulling someone else's image, and using Claude Code's native reasoning is not differentiated work.

**How to apply:**

- Reserve words like "achievement," "impressive," "portfolio-worthy," "demo material," "celebrate" for work the user actually built: custom code, eval harnesses, self-correction loops, observability, UI. Not for setup or tool output that the framework produces natively.
- When a setup step completes, frame it as "infrastructure works, now the real work starts," not as a milestone to celebrate.
- When Claude Code does something impressive in a session (e.g. autonomous tool pivoting), call it "starter-kit behaviour" or "framework's native capability," not "our self-correction loop." The loop doesn't exist until we architect it explicitly (prompt, critic, retry policy, contradiction detection).
- Be especially careful mid-slice; it's tempting to narrate in-progress wins. Save celebrations for completion of slices that contain genuine engineering.
- If unsure whether something is scaffolding vs engineering, ask: *"Did we write the code that made this work, or are we demonstrating a library/tool doing what it already does?"*
