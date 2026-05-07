import asyncio

import pytest

from reel_gen.nodes.approval_gate import approval_gate_node
from reel_gen.runs import REGISTRY
from reel_gen.state import ExtractedIntent, ReelState, Scene, ScriptPlan


@pytest.mark.asyncio
async def test_approval_gate_approves(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    rid = await REGISTRY.create(brief="x", duration_s=5, with_music=False)
    state = ReelState(
        run_id=rid, brief="x", duration_s=5,
        plan=ScriptPlan(
            hook="A.", scenes=[Scene(scene_idx=0, duration_s=5, visual_prompt="p",
                                     voiceover_excerpt="A", motion="zoom_in")],
            voiceover_text="A.", voice_style="warm", music_mood=None, aspect_ratio="9:16",
        ),
    )

    async def approver():
        await asyncio.sleep(0.05)
        await REGISTRY.set_approval(rid, approved=True)

    asyncio.create_task(approver())
    new_state = await approval_gate_node(state)
    assert new_state.approved is True


@pytest.mark.asyncio
async def test_approval_gate_rejects(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    rid = await REGISTRY.create(brief="x", duration_s=5, with_music=False)
    state = ReelState(run_id=rid, brief="x", duration_s=5)

    async def rejector():
        await asyncio.sleep(0.05)
        await REGISTRY.set_approval(rid, approved=False)

    asyncio.create_task(rejector())
    new_state = await approval_gate_node(state)
    assert new_state.approved is False
