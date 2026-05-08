"""LangGraph wiring: Extract -> Plan -> Approval Gate -> Execute -> Stitch -> Eval."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from reel_gen.nodes.approval_gate import approval_gate_node
from reel_gen.nodes.eval_brand_voice import eval_brand_voice_node
from reel_gen.nodes.execute import execute_node
from reel_gen.nodes.extract import extract_node
from reel_gen.nodes.plan import plan_node
from reel_gen.nodes.stitch import stitch_node
from reel_gen.state import ReelState


def _route_after_approval(state: ReelState) -> str:
    return "execute" if state.approved else "end_rejected"


def build_graph():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.add_node("approval_gate", approval_gate_node)
    g.add_node("execute", execute_node)
    g.add_node("stitch", stitch_node)
    g.add_node("eval_brand_voice", eval_brand_voice_node)
    g.add_node("end_rejected", lambda s: s)

    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", "approval_gate")
    g.add_conditional_edges("approval_gate", _route_after_approval, {
        "execute": "execute",
        "end_rejected": "end_rejected",
    })
    g.add_edge("execute", "stitch")
    # Brand-voice judge runs after stitch and writes a Langfuse score plus
    # eval_brand_voice.json. Non-fatal: failures inside the node are appended
    # to state.errors and do not block reaching END.
    g.add_edge("stitch", "eval_brand_voice")
    g.add_edge("eval_brand_voice", END)
    g.add_edge("end_rejected", END)
    return g.compile()


# Phase 3 builder kept for partial CLI runs; used by tests.
def build_graph_until_plan():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", END)
    return g.compile()
