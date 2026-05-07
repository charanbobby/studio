---
name: Drive fix verification programmatically, don't hand the user reload dances
description: After a code change in a debugging session, run the verification myself via a probe in the live environment. Don't prescribe reload-and-re-run snippets for the user to paste.
type: feedback
---
When I ship a fix mid-session, I DO the import plus re-run myself via a probe or script in the live environment. I do not hand the user a `importlib.reload(...)` snippet and ask them to paste it.

**Why:** First surfaced 2026-04-23 during a debug session. After three consecutive fixes I told the user "reload module X plus re-run cell Y" each time. After the third round they said: *"you do the import and run the cell next time, dont wait for me."* The mechanical reload steps were my job to automate, not theirs to execute.

**How to apply:**

- After editing source, immediately run a probe script that exercises the fix against real state. Probe scripts live under `d:/tmp/probe_*.py` per the fail-fast rule.
- I cannot reach into the user's notebook kernel. If verification requires kernel-resident state, reconstruct it programmatically from the on-disk artifacts the pipeline writes (intermediate JSONs, evidence files, tool plans) so I can rebuild the state without forcing the user to re-run their session.
- Capability tokens or any session-only artifacts I can't reconstruct from disk: mint fresh ones programmatically.
- If verification needs paid LLM spend, flag the expected cost and ask before firing. Otherwise just run.
- Keep the user's notebook clean for narrative plus final demo. Debugging iteration runs elsewhere.

**What this does NOT change:**

- `feedback_user_drives_infra.md` still applies: docker/compose/deploy commands remain the user's to run.
- `feedback_fail_fast_verify.md` still applies: probe BEFORE committing; this rule adds that the probe should also cover the fix's live verification, not stop at unit-test-level synthetic assertions.
