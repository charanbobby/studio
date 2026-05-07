---
name: Fail-fast verify before committing ANY code into a tracked artifact
description: ALWAYS run a fail-fast probe of new code/APIs/patterns against the live runtime before inserting into a notebook, runbook, or committed file. Probe-then-commit, never commit-then-hope.
type: feedback
---

**RULE, not a suggestion.** Every block of code I'm about to commit into a notebook cell, runbook, Dockerfile, script, or any tracked artifact MUST pass a fail-fast probe in the actual runtime BEFORE the insertion goes to disk. No exceptions.

**Why the rule is hard, not soft:**

- Three observed incidents in a single project where I prescribed unverified APIs and the user caught the error later. Each cost a kernel restart, a re-read, or a re-edit pass plus friction with the user.
- The user has flagged it explicitly multiple times: *"You should commit to memory to always use a fail-fast approach. You seem to be missing it a lot."*
- The pattern of missing it: I treat small / "obviously correct" code as exempt from fail-fast. It isn't. The cost of a 30-second probe is trivial vs the cost of committing broken code, which a) requires re-editing after feedback, b) wastes user attention, c) breaks their trust in my outputs.

**The explicit protocol, every time:**

1. **Write the new code to a temp file** (`d:/tmp/probe_*.py` or similar).
2. **Extract dependent symbols from earlier scope** (notebook cells, modules) so the probe runs in realistic context.
3. **Run it against the live venv / container / environment.** Use real data if the code should work on it.
4. **Only after the probe exits 0 with the expected output** do I edit the target file.
5. **After the modification, re-validate the target file** if it's a structured format (JSON, notebook, etc.).

**Step 3 is not optional. Syntax-checking via `ast.parse` is NOT a substitute.** The probe must actually execute.

**Beyond code, applies to document revisions too:**

When renumbering or restructuring a document with cross-references (runbooks, architecture docs, plans), write a validator script that parses the final document and confirms every cross-reference resolves. "The headers are sequential" is not the same as "the cross-references still point where they should." On 2026-04-20 a 10-line validator caught two real broken "Step N" references after a doc renumbering pass that surface-level review missed.

**How to apply beyond notebook code:**

- Before recommending an API, env var, SDK method, or runtime pattern in a runbook, probe the live system.
- After any unverified error is reported by the user, treat the previous prescription as a hypothesis that just failed; investigate the real API before prescribing a replacement.

**Telltale warning signs in my own reasoning:**

The phrases *"this should work"*, *"this is straightforward"*, *"syntax is valid"*, or *"I'll verify after"* are flags that I'm about to skip fail-fast. When I notice them, stop and probe.
