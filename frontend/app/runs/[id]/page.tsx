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
  const [gateResolved, setGateResolved] = useState(false);
  const [optimisticApproved, setOptimisticApproved] = useState(false);
  const events = useRunStream(params.id);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      while (!cancelled) {
        try {
          const s = await getRun(params.id);
          if (!cancelled) setSnap(s);
          if (s.status === "completed" || s.status === "rejected" || s.status === "error") return;
          // Faster polling cadence while the run is non-terminal so the UI
          // catches up quickly after the user approves the plan (SSE is not
          // reliable behind basic-auth + Cloudflare).
          await new Promise((r) => setTimeout(r, 1500));
        } catch {
          // transient errors are swallowed; SSE drives the UI
          await new Promise((r) => setTimeout(r, 2000));
        }
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [params.id, events.length]);

  if (!snap) return <div>Loading...</div>;

  const showPlanPanel =
    snap.status === "awaiting_approval" && snap.plan && !gateResolved;
  const isTerminal =
    snap.status === "completed" ||
    snap.status === "rejected" ||
    snap.status === "error";
  // Show the "Generating media..." card whenever we are between approval and
  // a terminal state, OR when the user has just approved but the next poll
  // hasn't yet flipped status off "awaiting_approval". Don't show it when
  // the user just rejected (we'll fall through to the rejected message once
  // the status flips).
  const justRejected =
    gateResolved && !optimisticApproved && snap.status === "awaiting_approval";
  const showGenerating = !showPlanPanel && !isTerminal && !justRejected;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs text-neutral-500 font-mono">{snap.run_id}</div>
        <div className="text-sm text-neutral-300 mt-1">{snap.brief}</div>
      </div>

      <ProgressTimeline events={events} />

      {showPlanPanel && snap.plan && (
        <PlanReviewPanel
          runId={snap.run_id}
          plan={snap.plan}
          onResolved={(approved) => {
            setGateResolved(true);
            setOptimisticApproved(approved);
          }}
        />
      )}

      {showGenerating && (
        <div className="border border-indigo-700 bg-indigo-950/30 rounded p-5 flex items-center gap-4">
          <span className="inline-block w-4 h-4 rounded-full bg-indigo-500 animate-pulse ring-2 ring-indigo-500/40" />
          <div>
            <div className="text-base font-medium text-indigo-200">
              Generating media...
            </div>
            <div className="text-xs text-neutral-400 mt-1">
              This typically takes 20-40 seconds for 5s reels.
            </div>
          </div>
        </div>
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
