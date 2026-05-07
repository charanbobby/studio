"use client";

import { useState } from "react";

import { approvePlan } from "@/lib/api";
import type { ScriptPlan } from "@/lib/types";

export function PlanReviewPanel({
  runId,
  plan,
  onResolved,
}: {
  runId: string;
  plan: ScriptPlan;
  onResolved: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function decide(approved: boolean) {
    setBusy(true);
    try {
      await approvePlan(runId, approved);
      onResolved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-amber-700 bg-amber-950/30 rounded p-5 space-y-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-semibold text-amber-300">Review the plan</h3>
        <span className="text-xs text-amber-400">
          No paid generation runs until you approve.
        </span>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Hook</div>
        <div className="text-base">{plan.hook}</div>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Voiceover</div>
        <div className="text-sm leading-relaxed">{plan.voiceover_text}</div>
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase text-neutral-400">Scenes ({plan.scenes.length})</div>
        {plan.scenes.map((s) => (
          <div key={s.scene_idx} className="border border-neutral-800 rounded p-3 text-sm">
            <div className="flex justify-between items-baseline">
              <div className="font-medium">Scene {s.scene_idx + 1}</div>
              <div className="text-neutral-400 text-xs">
                {s.duration_s.toFixed(1)}s, {s.motion}
              </div>
            </div>
            <div className="text-neutral-300 mt-1">{s.voiceover_excerpt}</div>
            <div className="text-neutral-500 text-xs mt-1 italic">{s.visual_prompt}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={() => decide(true)}
          disabled={busy}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 px-5 py-2 rounded font-medium"
        >
          Approve and generate
        </button>
        <button
          onClick={() => decide(false)}
          disabled={busy}
          className="bg-neutral-700 hover:bg-neutral-600 disabled:bg-neutral-800 px-5 py-2 rounded"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
