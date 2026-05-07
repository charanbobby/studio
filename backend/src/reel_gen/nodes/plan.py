"""Plan node: ExtractedIntent + duration -> ScriptPlan, written to disk."""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from reel_gen.llm.openrouter import call_claude_cached
from reel_gen.state import NodeError, ReelState, Scene, ScriptPlan
from reel_gen.tracing.langfuse_client import with_span

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "plan.md"
_MAX_RETRIES = 2


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _fallback_plan(state: ReelState) -> ScriptPlan:
    """Deterministic fallback when the LLM keeps returning malformed JSON."""
    return ScriptPlan(
        hook=state.brief[:80],
        scenes=[Scene(
            scene_idx=0, duration_s=float(state.duration_s),
            visual_prompt=f"{state.brief}, vertical 9:16, cinematic",
            voiceover_excerpt=state.brief[:120], motion="zoom_in",
        )],
        voiceover_text=state.brief[:200],
        voice_style="neutral",
        music_mood=None,
        aspect_ratio="9:16",
    )


@with_span(name="plan_node")
def plan_node(state: ReelState) -> ReelState:
    model = os.environ.get("PLAN_MODEL", "anthropic/claude-sonnet-4-6")
    intent_json = state.intent.model_dump_json() if state.intent else "{}"
    user = f"INTENT:\n{intent_json}\n\nDURATION_S: {state.duration_s}\n" \
           f"WITH_MUSIC: {state.with_music}"

    last_err: str | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = call_claude_cached(
                model=model,
                system=_load_system_prompt(),
                user=user if attempt == 0 else
                     user + f"\n\nVALIDATION_ERROR_FROM_PRIOR_ATTEMPT: {last_err}",
                max_tokens=2000,
                phase="plan",
            )
            data = json.loads(_strip_fences(result.text))
            plan = ScriptPlan.model_validate(data)
            state.plan = plan
            state.cost_ledger.append(result.cost_entry)
            break
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)
            if attempt == _MAX_RETRIES:
                state.errors.append(NodeError(
                    node="plan", message=f"plan validation failed after retries: {e}",
                    fatal=False,
                ))
                state.plan = _fallback_plan(state)
        except Exception as e:
            state.errors.append(NodeError(node="plan", message=str(e), fatal=True))
            state.plan = _fallback_plan(state)
            break

    # Write plan.json for audit (the "plan is the product" rule from SKILL.md).
    runs = Path(os.environ.get("RUNS_DIR", "./runs"))
    run_dir = runs / state.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(state.plan.model_dump_json(indent=2))
    if state.intent:
        (run_dir / "intent.json").write_text(state.intent.model_dump_json(indent=2))
    return state
