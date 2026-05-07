"""LangGraph wiring. Phase 3 ships Extract -> Plan only.
Approval Gate, Execute, and Stitch land in Phases 5, 6, 7.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from reel_gen.nodes.extract import extract_node
from reel_gen.nodes.plan import plan_node
from reel_gen.state import ReelState


def build_graph_until_plan():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", END)
    return g.compile()
