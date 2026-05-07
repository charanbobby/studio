---
name: TL;DR-first format on every substantial response
description: User directive, lead every substantial response with a TL;DR block, 2-4 sentences, before the detailed version. Memory-enforce, not on-request.
type: feedback
---
**Lead every substantial response with a TL;DR block.** When the response is more than a couple of sentences, the first thing the user sees must be a `**TL;DR:**`-labeled summary in 2-4 sentences. Detailed explanation follows below for the user to skim or read deeply.

**Why:** First surfaced 2026-04-26. After a long plain-English summary the user replied just `tldr`, then explicitly asked: *"could you commit to your memory to always produce TLDR version of everything you're about to say."* The user reads top-down and stops when they have what they need; burying the headline forces them to read everything or send a follow-up. Both are friction I created.

**How to apply, every substantial response:**

1. **Open with `**TL;DR:**`** so the user can scan-find it. 2-4 sentences max. State the result, the impact, and (if any) the next step or open question. Plain English (per `feedback_plain_english_always.md`).
2. **Below the TL;DR, write the detailed version.** Headings, lists, tables, file references, whatever serves the substance.
3. **Single-sentence answers don't need a TL;DR.** If the entire response IS one or two sentences, the response itself is the TL;DR.
4. **End-of-turn summaries follow the same shape.** Lead line is the headline; the rest is detail.
5. **Decision-asks lead with the recommendation.** TL;DR is the recommendation plus main tradeoff; the detail is the supporting analysis.

**Telltale warning signs in my own draft:**

- Response opens with framing or context-setting before the actual answer ("Let me explain...", "Here's what changed...")
- First sentence is tool-call narration ("I'll read the file first...") instead of a result
- Response is multiple paragraphs and the headline only emerges at the end
- About to send a long structured response without a top-line summary

If any are true, stop and write the TL;DR first.

**Interaction with plain-English rule:** the TL;DR must itself be plain English. Jargon in the headline defeats the purpose. The pre/post check from the plain-English rule applies to the TL;DR too.

**Interaction with terse-tone defaults:** "TL;DR-first" does NOT mean "always write more." It means "if I would have written a long response anyway, the long response gets a TL;DR header." Short responses stay short.
