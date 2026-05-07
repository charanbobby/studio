import asyncio

import pytest

from reel_gen.runs import RunRegistry


@pytest.mark.asyncio
async def test_register_and_get(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    reg = RunRegistry()
    rid = await reg.create(brief="hello", duration_s=5, with_music=False)
    assert rid
    snap = await reg.snapshot(rid)
    assert snap["brief"] == "hello"
    assert snap["status"] == "pending"


@pytest.mark.asyncio
async def test_event_stream_yields_events(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    reg = RunRegistry()
    rid = await reg.create(brief="x", duration_s=5, with_music=False)

    async def producer():
        await reg.publish(rid, {"event": "extract_start"})
        await reg.publish(rid, {"event": "extract_end"})
        await reg.complete(rid, "completed")

    async def consumer():
        events = []
        async for e in reg.subscribe(rid):
            events.append(e)
        return events

    _, events = await asyncio.gather(producer(), consumer())
    kinds = [e["event"] for e in events]
    assert "extract_start" in kinds
    assert "extract_end" in kinds
