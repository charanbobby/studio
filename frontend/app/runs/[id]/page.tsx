"use client";

import { useEffect, useState } from "react";

import { CostLedger } from "@/components/CostLedger";
import { PlanReviewPanel } from "@/components/PlanReviewPanel";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { ReelPlayer } from "@/components/ReelPlayer";
import { getRun } from "@/lib/api";
import { useRunStream } from "@/lib/sse";
import type { RunSnapshot } from "@/lib/types";

export default function RunPage({ params }: { params: { id: string } }) {
  const [snap, setSnap] = useState<RunSnapshot | null>(null);
  const events = useRunStream(params.id);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      while (!cancelled) {
        try {
          const s = await getRun(params.id);
          if (!cancelled) setSnap(s);
          if (s.status === "completed" || s.status === "rejected" || s.status === "error") return;
        } catch {
          // transient errors are swallowed; SSE drives the UI
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [params.id, events.length]);

  if (!snap) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs text-neutral-500 font-mono">{snap.run_id}</div>
        <div className="text-sm text-neutral-300 mt-1">{snap.brief}</div>
      </div>

      <ProgressTimeline events={events} />

      {snap.status === "awaiting_approval" && snap.plan && (
        <PlanReviewPanel
          runId={snap.run_id}
          plan={snap.plan}
          onResolved={() => {}}
        />
      )}

      {snap.status === "completed" && <ReelPlayer runId={snap.run_id} />}

      {snap.status === "rejected" && (
        <div className="text-neutral-400">Run rejected. No media was generated.</div>
      )}

      {snap.status === "error" && (
        <div className="text-red-400">An error occurred. Check the backend logs.</div>
      )}

      <CostLedger events={events} />
    </div>
  );
}
