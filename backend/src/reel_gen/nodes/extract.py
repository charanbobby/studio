"""Extract node: free-form brief -> ExtractedIntent JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

from reel_gen.llm.openrouter import call_claude_cached
from reel_gen.state import ExtractedIntent, NodeError, ReelState
from reel_gen.tracing.langfuse_client import with_span

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "extract.md"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


@with_span(name="extract_node")
def extract_node(state: ReelState) -> ReelState:
    model = os.environ.get("EXTRACT_MODEL", "anthropic/claude-haiku-4-5")
    user = f"BRIEF:\n{state.brief}\n\nDURATION_S: {state.duration_s}"
    try:
        result = call_claude_cached(
            model=model,
            system=_load_system_prompt(),
            user=user,
            max_tokens=400,
            phase="extract",
        )
        text = result.text.strip()
        # Strip accidental markdown fences if the model adds them.
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
        data = json.loads(text)
        intent = ExtractedIntent.model_validate(data)
        state.intent = intent
        state.cost_ledger.append(result.cost_entry)
    except Exception as e:
        state.errors.append(NodeError(node="extract", message=str(e), fatal=True))
        state.intent = ExtractedIntent(
            topic=state.brief[:80],
            tone="neutral",
            audience="general",
            notes="EXTRACT_FAILED",
        )
    return state
