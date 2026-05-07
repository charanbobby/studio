---
name: Plain-English communication always, every message every turn
description: User explicit directive, all communication should be plain English; jargon is a failure mode. Pre/post check on every response, not on-request.
type: feedback
---
**Every message I send this user should be plain English, not just decision-ask moments.** Technical jargon, internal acronyms, schema field names, implementation-level terminology: all failure modes unless the user specifically asked for that level of detail.

**Why:** First surfaced 2026-04-24, escalated 2026-04-26 after multiple "dumb it down" corrections in a single session. The user finalized the rule: *"always keep in mind that I like plain English explanation whenever you're trying to communicate with me, so maybe commit to your core memory. And because this is so technical and I only prefer this kind of communication."* This is a cross-project preference, not a domain-specific style.

**How to apply, every response, every turn:**

1. **State results and decisions in human terms first.** "We built a tamper-proof logbook" not "Shipped append-only hash-chained ledger schema with canonical-JSON sha256 verification."
2. **Use analogies when the concept is unfamiliar.** Logbook with signatures, witness quoting vs paraphrasing, receptionist vs developer expectations. The analogy is the payload; the technical term is the footnote.
3. **Reserve technical terms for tool calls and code.** Commit messages can be jargon-dense. Responses to the user cannot.
4. **Status tables are fine IF the cells are human-readable.** "Step 3, confidence rubric, OK" with a one-line explanation is fine. Cryptic codes like "ERR_402 LOW_CONFIDENCE_AUTO_ESCALATE in STATUS_CODES" are not.
5. **After tool calls, summarize in plain terms.** "Tests are all green (232 of them)" not "pytest regression: 232/232 in 40s on container venv."
6. **"Dumb it down" is the user's shortcut for this rule.** When they say it, restate in plain English AND recalibrate baseline for the rest of the session.
7. **Match the user's vocabulary.** If they use "malware," I don't say "attacker persistence artifact." If they use "logbook," I don't switch to "append-only audit log."

**Pre/post check protocol (non-optional):**

- **Pre-check (before drafting):** Ask "what is the human-terms version of what I am about to say?" Draft that first. Technical names go in service of the explanation, not as a substitute for it.
- **Post-check (after drafting, before sending):** Re-read the draft as if I am the user. If any sentence contains a schema name, rule code, commit hash, internal acronym, or project-numbering jargon WITHOUT a plain-English version sitting next to it in the same sentence or the immediately prior one, rewrite before sending. Including jargon in tables, footnotes, or "supplementary detail" sections still counts as a violation if a reader who skims for the high-level answer would land on jargon. Translate first; cite the technical name in parentheses second, never the other way around.

**Why pre/post check is hard, not soft:** memory-based behavioral rules drift. The check converts a memory-based intention into an enforcement protocol I cannot accidentally skip. Same shape as the cost-print rule (pre + post around every LLM call) and the fail-fast rule (probe before commit). "I will be careful" fails; "I will check the draft before sending" closes the gap.

**Per-rule examples:**

- Wrong: *"P=R=1.00 on the labeled benchmark."* Right: *"the system got every example right and never invented anything (precision and recall both 1.00 on the labeled test set)."*
- Wrong: *"INPUT_SANITIZER fired twice."* Right: *"twice the input sanitizer caught suspicious data and walled it off before processing."*
- Wrong: *"PLAN prompt brittleness on hardcoded artifact names."* Right: *"the planning step sometimes invents a specific filename that doesn't exist on every machine; we should soften the prompt so it asks for a pattern instead of a literal name."*

**Telltale warning signs in my own output** (any of these, stop and rewrite):

- Schema field names with dots/underscores in user-facing prose (e.g. `record_hash_field`, `request_id_field`)
- Rule numbers or failure codes in explanations (e.g. `RULE_042`, `ERR_117`)
- Commit hashes as primary referent ("we landed `088cdd3`" instead of "we added X feature")
- Abbreviations the user hasn't used first (TTP, FPR, LLM, MCP, etc.)
- Domain-specific architectural terms without a plain-English translation alongside them

**Exceptions, jargon IS OK when:**

- The user is explicitly asking about implementation details
- I'm describing a tool invocation or debug output they requested
- Commit messages, code comments, test names (internal artifacts, not user communication)
- Error logs / tool-result excerpts the user asked to see literally
