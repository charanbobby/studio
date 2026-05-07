---
name: Prompt caching is on by default for any Claude API call
description: Every Claude API call gets `cache_control: ephemeral` on the stable portion (system prompt / tool schemas). No exceptions without an explicit reason stated.
type: feedback
---
**Rule:** When I write, review, or ship code that calls a Claude model via the Anthropic SDK, the Claude API directly, or an OpenAI-compatible gateway (OpenRouter, Bedrock passthrough, Vertex), **prompt caching is on by default**. Cache the stable portion (system prompt, large tool/schema specs, few-shot examples) via `cache_control: {"type": "ephemeral"}`. The cached block must meet the per-model minimum (1024 tokens for Sonnet, 2048 for Haiku at the time of writing; check current minimums at build time).

**Why:** Verified 2026-04-19 on `anthropic/claude-sonnet-4.6` via OpenRouter. A 2208-token system block went from **$0.0084 on the first call to $0.0008 on the second** (90%+ savings on the cached portion, 10x cost reduction for cache hits). The "write premium" on the first call is around 25%, so the break-even is one hit; essentially any iterative development loop, any retry, any investigation that runs the same prompt twice. Leaving caching off is burning money for no reason. The user has explicitly told me this is a default, not a toggle.

**How to apply:**

1. **Any Claude API call new code introduces:** add `cache_control` immediately, not as a follow-up. The system message becomes a multi-block content list with `cache_control` on the stable text block. Don't ship a single-string system message against a Claude model.
2. **Any Claude API call I review or modify:** if caching is off, flag it as a defect the same way I would flag a missing error handler. Propose adding it even if the user didn't ask.
3. **OpenAI-compatible shape (most gateways):**
   ```python
   messages=[
       {"role": "system", "content": [
           {"type": "text", "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}},
       ]},
       {"role": "user", "content": user_input},
   ]
   ```
4. **Native Anthropic SDK shape:**
   ```python
   client.messages.create(
       model="claude-sonnet-4-6",
       system=[
           {"type": "text", "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}},
       ],
       messages=[{"role": "user", "content": user_input}],
       max_tokens=...,
   )
   ```
5. **Large tool schemas:** if `tools=[...]` is passed, those blocks can also take `cache_control`. Cache tool schemas when they're large and stable.
6. **Non-Claude models** (Gemini, OpenAI, etc.): `cache_control` is Anthropic-specific. Don't blindly add it to Gemini calls (Gemini has its own context-cache API with a 32K-token minimum that's rarely met by typical prompts). For Gemini via OpenRouter, leave off unless there's a reason.
7. **Verifying it's on:** check the response's `usage.prompt_tokens_details.cached_tokens` (or equivalent in your tracing tool) is greater than 0 on the second call with an unchanged system prompt. Zero means caching isn't active or the block is under the minimum token size.

**Exceptions:** only when there's an explicit, stated reason: security policy forbidding prompt storage, A/B-testing a non-cached baseline, the prompt genuinely changes every call (rare). State the reason in a code comment so the next reviewer doesn't "fix" it by adding caching.
