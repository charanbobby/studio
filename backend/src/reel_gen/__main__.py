"""CLI entry: python -m reel_gen --prompt "..." [--duration 5]"""
from __future__ import annotations

import argparse
import sys
import uuid

from reel_gen.graph import build_graph_until_plan
from reel_gen.state import ReelState
from reel_gen.tracing.langfuse_client import flush


def main() -> int:
    p = argparse.ArgumentParser(prog="reel_gen")
    p.add_argument("--prompt", required=True)
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--with-music", action="store_true")
    args = p.parse_args()

    run_id = uuid.uuid4().hex[:12]
    state = ReelState(
        run_id=run_id,
        brief=args.prompt,
        duration_s=args.duration,
        with_music=args.with_music,
    )
    graph = build_graph_until_plan()
    final: ReelState = graph.invoke(state)
    flush()

    print(f"\nrun_id: {run_id}")
    print(f"intent: {final['intent'] if isinstance(final, dict) else final.intent}")
    plan_obj = final["plan"] if isinstance(final, dict) else final.plan
    print(f"plan scenes: {len(plan_obj.scenes) if plan_obj else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
