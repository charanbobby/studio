"""In-memory run registry with filesystem persistence + per-run async event bus.

Keeps things simple: one process serves all runs; state mirrored to
runs/<id>/state.json so a refresh recovers context. SSE consumers read
from a per-run asyncio.Queue.

Each run keeps a buffered event history so that a subscriber that joins
after some events have already been published still receives them in
order. This also makes the producer/consumer race in tests deterministic.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._history: dict[str, list[dict]] = {}
        self._closed: dict[str, bool] = {}
        self._approvals: dict[str, asyncio.Event] = {}
        self._approve_decisions: dict[str, bool] = {}
        self._edited_plans: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _runs_dir(self) -> Path:
        d = Path(os.environ.get("RUNS_DIR", "./runs"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def create(self, *, brief: str, duration_s: int, with_music: bool) -> str:
        rid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        rec = {
            "run_id": rid,
            "brief": brief,
            "duration_s": duration_s,
            "with_music": with_music,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        async with self._lock:
            self._runs[rid] = rec
            self._queues[rid] = []
            self._history[rid] = []
            self._closed[rid] = False
            self._approvals[rid] = asyncio.Event()
        self._persist(rid)
        return rid

    def _persist(self, rid: str) -> None:
        run_dir = self._runs_dir() / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "state.json").write_text(json.dumps(self._runs[rid], indent=2, default=str))

    async def snapshot(self, rid: str) -> dict:
        async with self._lock:
            return dict(self._runs.get(rid, {}))

    async def update(self, rid: str, **fields) -> None:
        async with self._lock:
            if rid not in self._runs:
                return
            self._runs[rid].update(fields)
            self._runs[rid]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist(rid)

    async def complete(self, rid: str, status: str) -> None:
        await self.update(rid, status=status)
        await self.publish(rid, {"event": "run_complete", "status": status})
        async with self._lock:
            self._closed[rid] = True
            for q in self._queues.get(rid, []):
                q.put_nowait(None)

    async def publish(self, rid: str, event: dict) -> None:
        async with self._lock:
            self._history.setdefault(rid, []).append(event)
            for q in self._queues.get(rid, []):
                q.put_nowait(event)

    async def subscribe(self, rid: str) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            # Replay buffered history so late subscribers see earlier events.
            for past in self._history.get(rid, []):
                q.put_nowait(past)
            self._queues.setdefault(rid, []).append(q)
            already_closed = self._closed.get(rid, False)
        if already_closed:
            q.put_nowait(None)
        try:
            while True:
                item = await q.get()
                if item is None:
                    return
                yield item
        finally:
            async with self._lock:
                if q in self._queues.get(rid, []):
                    self._queues[rid].remove(q)

    async def list_runs(self) -> list[dict]:
        async with self._lock:
            return sorted(self._runs.values(), key=lambda r: r["updated_at"], reverse=True)

    async def await_approval(self, rid: str) -> bool:
        ev = self._approvals.get(rid)
        if ev is None:
            return False
        await ev.wait()
        return self._approve_decisions.get(rid, False)

    async def set_approval(
        self,
        rid: str,
        *,
        approved: bool,
        edited_plan: dict | None = None,
    ) -> None:
        self._approve_decisions[rid] = approved
        if edited_plan is not None:
            self._edited_plans[rid] = edited_plan
        ev = self._approvals.get(rid)
        if ev:
            ev.set()

    def get_edited_plan(self, rid: str) -> dict | None:
        return self._edited_plans.get(rid)


REGISTRY = RunRegistry()
