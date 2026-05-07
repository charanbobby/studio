---
name: LLM cost print pattern, implementation guide for any project pipeline
description: Code template for _llm_cost_pre / _llm_cost_post helpers; copy into any project that calls an LLM API. The behavioral rule (never guess, always print) lives in global CLAUDE.md; this file is the engineering implementation.
type: feedback
---
**The behavioral rule lives in `~/.claude/CLAUDE.md`.** This memory is the code-level template: copy these helpers into any project's LLM call module so you have working cost printing from day one.

**Why:** On 2026-04-23 an LLM pipeline ran 5 times at $2.68-2.73 per run while cost estimates said $0.08. The root cause was a bundle builder sending ~120k tokens of inode directory tables to an analysis LLM that didn't need them. Real-time cost output on every call would have surfaced the problem on run 1.

**Drop this into your project's LLM call module:**

```python
import tiktoken

# Update this dict for every model the project uses.
# Rates are (input_$/1M_tokens, output_$/1M_tokens).
# Check current rates at platform pricing pages before finalizing.
_LLM_RATES: dict[str, tuple[float, float]] = {
    "anthropic/claude-sonnet-4-6":   (3.00, 15.00),
    "anthropic/claude-haiku-4-5":    (0.80,  4.00),
    "anthropic/claude-opus-4-7":    (15.00, 75.00),
    # add models as needed; missing model prints "rate unknown"
}

def _llm_cost_pre(phase: str, model: str, messages: list) -> None:
    """Print estimated cost before an LLM call."""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            tokens += len(enc.encode(content))
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    tokens += len(enc.encode(block.get("text", "")))
    rates = _LLM_RATES.get(model)
    if rates:
        est = tokens * rates[0] / 1_000_000
        print(f"[COST PRE ] {phase} | model={model} | est_input_tokens={tokens:,} | est_cost=${est:.5f}")
    else:
        print(f"[COST PRE ] {phase} | model={model} | est_input_tokens={tokens:,} | rate unknown")


def _llm_cost_post(phase: str, model: str, usage) -> None:
    """Print actual cost after an LLM call. Pass response.usage from the API response."""
    rates = _LLM_RATES.get(model)
    in_tok  = getattr(usage, "prompt_tokens", 0)
    out_tok = getattr(usage, "completion_tokens", 0)
    if rates:
        cost_in  = in_tok  * rates[0] / 1_000_000
        cost_out = out_tok * rates[1] / 1_000_000
        total    = cost_in + cost_out
        print(
            f"[COST POST] {phase} | "
            f"in={in_tok:,} (${cost_in:.5f}) "
            f"out={out_tok:,} (${cost_out:.5f}) | "
            f"total=${total:.5f}"
        )
    else:
        print(f"[COST POST] {phase} | in={in_tok:,} out={out_tok:,} | rate unknown")
```

**Call site pattern (OpenAI-compatible client):**

```python
_llm_cost_pre(phase, model, messages)
response = client.chat.completions.create(model=model, messages=messages, ...)
_llm_cost_post(phase, model, response.usage)
```

**Call site pattern (Anthropic SDK):**

```python
_llm_cost_pre(phase, model, messages)
response = client.messages.create(model=model, messages=messages, ...)
# Anthropic SDK uses input_tokens / output_tokens instead of prompt_tokens / completion_tokens.
# Either adapt the helper or use a small shim:
class _UsageShim:
    def __init__(self, r):
        self.prompt_tokens     = r.usage.input_tokens
        self.completion_tokens = r.usage.output_tokens
_llm_cost_post(phase, model, _UsageShim(response))
```

**Rules that don't change regardless of project:**

- Every call site gets BOTH helpers. Not just POST. The PRE establishes what you expected; the POST confirms what happened. When they diverge by more than ~20%, investigate the bundle builder.
- Missing a model from `_LLM_RATES` prints "rate unknown," not $0. Never silently skip.
- Do NOT anchor scope decisions (is this re-run affordable? how many ablation rows can we do?) on a cost figure from a buggy run. Always pull the number from a recent POST line printed after the bug was fixed.

**Design smell the PRE output catches:**

If the PRE line shows 80k+ estimated input tokens for a phase that should only see a few kilobytes of evidence, the bundle builder is over-feeding the LLM. Check what structured fields the bundle includes and strip anything the analysis phase doesn't use (e.g. navigation/staging tool outputs that only served the executor).