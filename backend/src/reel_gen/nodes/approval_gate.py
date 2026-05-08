"""Mandatory human-approval gate. Pauses the pipeline until a frontend
POST /api/runs/{id}/approve-plan resolves the registry's approval Event.
"""
from __future__ import annotations

from reel_gen.runs import REGISTRY
from reel_gen.state import ReelState, ScriptPlan


async def approval_gate_node(state: ReelState) -> ReelState:
    await REGISTRY.publish(state.run_id, {"event": "awaiting_approval"})
    await REGISTRY.update(state.run_id, status="awaiting_approval")
    approved = await REGISTRY.await_approval(state.run_id)
    state.approved = approved
    # If the user edited the plan during approval, swap state.plan to the
    # edited version so Execute fan-out generates from what the user saw.
    if approved:
        edited = REGISTRY.get_edited_plan(state.run_id)
        if edited is not None:
            try:
                state.plan = ScriptPlan.model_validate(edited)
            except Exception:
                # Fall back to the original plan if the edit cannot be parsed.
                pass
    await REGISTRY.publish(state.run_id, {"event": "plan_decision", "approved": approved})
    return state
