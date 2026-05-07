---
name: Second-invocation check, design must answer what happens the second time
description: Before treating any code that writes persistent state as done, answer the 4 second-invocation questions. Design-time rule, upstream of fail-fast.
type: feedback
---
**Before I treat any code that writes persistent state as done (output files, database rows, cache entries, ledger entries, log files, anything that survives the process exiting), I must answer four questions about it:**

1. **What does the second time this runs look like?** (overwrites, appends, fails-loud, isolates per-run?)
2. **What does a crash mid-flight leave behind?** (partial files, stale lock, broken hash chain, orphaned rows?)
3. **What do two of these running in parallel do?** (race conditions, clobbering, file-handle conflicts, deadlocks?)
4. **How does someone find prior outputs after a re-run?** (do they exist? where? is there a "latest" pointer?)

If I cannot answer all four without reading my own code, **the design is incomplete and I do not commit.** Probing-then-committing is fine; designing-then-committing without these answers is the failure mode.

**Why this rule exists:**

First surfaced 2026-04-25 in a prior project. The user discovered that a per-case output writer had no run isolation. Every re-run silently overwrote the prior run's output files (`findings.json`, `evidence.jsonl`, `tool_plan.json`, etc.). The bug had been live in committed code for days. The user diagnosed it in seconds: *"We are not saving them at the workstation level, they are being saved in the global level, which is getting rewritten."* I had read the same folder listing minutes earlier (with files dated across multiple days sitting in the same directory) and not flagged the smell.

**Signals to catch in folder listings and module organization:**

- Files with mtimes spanning multiple days in the same folder are a "what happened here?" smell. Either intentionally accumulating history (commit it to memory why) or silently overwriting (a bug).
- One writer in a module having explicit resume-from-prior logic while sibling writers in the same module do not is asymmetry worth questioning.
- Words like "ablation," "sweep," "compare runs," or "re-run" in a plan should trigger "how does multi-run isolation work?"

**Relationship to the existing fail-fast-verify rule:**

Fail-fast says *"verify before shipping."* This rule says *"the design is not finished yet, do not even probe."* It is upstream. A successful probe of an overwriting writer would have shown today's outputs landing on disk and exited zero; it would NOT have surfaced the silent overwrite of yesterday's run. Probing tells you the code runs; second-invocation thinking tells you the code is well-shaped.

**How to apply:**

- Any function/script that writes a file: think about it.
- Any function that mutates shared state: think about it.
- Any pipeline node that produces an artifact downstream consumers depend on: think about it.
- During a code review of someone else's code: ask the four questions of THAT code too.

**Telltale warning signs in my own reasoning that I am skipping this rule:**

- Phrases like *"the case_id partitions the output"* or *"each run gets its own X"* without checking if X is per-run or per-case.
- Treating "I've thought about the happy path" as equivalent to "I've thought about it."
- Writing path joins like `Path(base) / case_id / "output.json"` without ever asking what happens if the case is re-run.
- A file listing with mixed mtimes that I notice but do not investigate.

**What this is NOT:**

- Not a paranoia rule that demands per-run isolation always. Some files SHOULD be append-only (logs, ledgers). Some SHOULD be overwritten (latest-snapshot caches). The rule is to **decide deliberately**, not to default-overwrite.
- Not a replacement for fail-fast verify; it adds a check before fail-fast becomes meaningful.
