"""Brand-voice eval: post-stitch LLM judge that grades voiceover-vs-intent fit.

Runs after the reel is stitched. Asks Claude Haiku to score how well the
voiceover matches the extracted intent (topic, tone, audience, brand_voice)
on a 0-10 scale, persists the score to ``runs/<id>/eval_brand_voice.json``,
and emits a Langfuse ``eval.brand_voice`` numeric score on the run's session.

Failures are non-fatal: a busted eval call must never invalidate a successful
reel render. All exceptions are recorded as a non-fatal NodeError on state.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from reel_gen.llm.openrouter import call_claude_cached
from reel_gen.state import NodeError, ReelState

EVAL_PROMPT = """You are a brand-voice quality grader. Given:
- intent (topic, tone, audience, brand_voice)
- voiceover_text (the actual narration generated)
Grade how well the voiceover matches the intent on a 0-10 scale, where:
- 9-10: voiceover lands the brand voice / intent precisely
- 6-8: voiceover is close but has minor drift
- 3-5: voiceover is generic; doesn't reflect the brand
- 0-2: voiceover contradicts or fails the intent

Output ONLY a JSON object: {"score": <0-10 int>, "rationale": "<one sentence>"}
"""


def _strip_fences(text: str) -> str:
    """Strip any ```json ... ``` fences a chatty model might add around the JSON."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    t = t.strip("`")
    if "\n" in t:
        t = t.split("\n", 1)[1]
    if t.endswith("```"):
        t = t[:-3]
    return t.strip()


async def eval_brand_voice_node(state: ReelState) -> ReelState:
    """Post-stitch LLM judge. Non-fatal: exceptions are appended to state.errors."""
    if not state.intent or not state.plan:
        return state

    try:
        model = os.environ.get("EVAL_MODEL", "anthropic/claude-haiku-4-5")
        user = (
            f"INTENT:\n{state.intent.model_dump_json()}\n\n"
            f"VOICEOVER:\n{state.plan.voiceover_text}"
        )
        # call_claude_cached is sync (httpx.post under the hood). Bounce it
        # into a worker thread so we don't stall the event loop while the
        # OpenRouter call is in flight.
        result = await asyncio.to_thread(
            call_claude_cached,
            model=model,
            system=EVAL_PROMPT,
            user=user,
            max_tokens=200,
            phase="eval_brand_voice",
        )
        cleaned = _strip_fences(result.text)
        data = json.loads(cleaned)
        score_int = int(data.get("score", 5))
        rationale = str(data.get("rationale", ""))[:200]

        # Best-effort Langfuse score. Wrap in a tiny span under the run's
        # session so the score is attached to a trace_id (v4.5.1 will not
        # surface session-only scores via GET /api/public/scores). Any
        # failure here must not break the reel completion or persistence.
        try:
            from langfuse import get_client, propagate_attributes  # local import

            lf = get_client()
            with propagate_attributes(
                session_id=state.run_id,
                tags=["sri-studio", "eval"],
                metadata={"run_id": state.run_id, "kind": "eval_brand_voice"},
            ):
                with lf.start_as_current_observation(
                    name="eval_brand_voice.score",
                    as_type="span",
                    input={"score": score_int, "rationale": rationale},
                ):
                    lf.score_current_trace(
                        name="eval.brand_voice",
                        value=float(score_int),
                        data_type="NUMERIC",
                        comment=rationale,
                    )
            try:
                lf.flush()
            except Exception:
                pass
        except Exception:
            pass

        run_dir = Path(os.environ.get("RUNS_DIR", "./runs")) / state.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "eval_brand_voice.json").write_text(
            json.dumps({"score": score_int, "rationale": rationale}, indent=2)
        )
        state.cost_ledger.append(result.cost_entry)
    except Exception as e:
        state.errors.append(
            NodeError(node="eval_brand_voice", message=str(e), fatal=False)
        )
    return state
