"use client";

import { useMemo, useState } from "react";

import { RatingControl } from "@/components/RatingControl";
import type { FieldFeedback } from "@/components/RatingControl";
import { approvePlan } from "@/lib/api";
import type { Motion, Scene, ScriptPlan } from "@/lib/types";

const MOTIONS: Motion[] = ["zoom_in", "zoom_out", "pan_left", "pan_right", "static"];

const EMPTY_FEEDBACK: FieldFeedback = { rating: null, note: "" };

function feedbackHasAnyRating(fb: Record<string, FieldFeedback>): boolean {
  for (const key of Object.keys(fb)) {
    const v = fb[key];
    if (v && (v.rating !== null || v.note.length > 0)) return true;
  }
  return false;
}

function plansEqual(a: ScriptPlan, b: ScriptPlan): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function PlanReviewPanel({
  runId,
  plan,
  onResolved,
}: {
  runId: string;
  plan: ScriptPlan;
  onResolved: (approved: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [draft, setDraft] = useState<ScriptPlan>(() => JSON.parse(JSON.stringify(plan)));
  const [feedback, setFeedback] = useState<Record<string, FieldFeedback>>({});

  function getFeedback(path: string): FieldFeedback {
    return feedback[path] ?? EMPTY_FEEDBACK;
  }

  function setFieldFeedback(path: string, next: FieldFeedback) {
    setFeedback((f) => ({ ...f, [path]: next }));
  }

  // Snapshot the original plan once at mount so the "Edited" badge tracks
  // user edits, not server-side updates that could race in mid-edit.
  const original = useMemo<ScriptPlan>(
    () => JSON.parse(JSON.stringify(plan)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const isEdited = !plansEqual(original, draft);

  function updateScene(idx: number, patch: Partial<Scene>) {
    setDraft((d) => ({
      ...d,
      scenes: d.scenes.map((s) => (s.scene_idx === idx ? { ...s, ...patch } : s)),
    }));
  }

  async function decide(approved: boolean) {
    setBusy(true);
    setErrorMsg(null);
    // Optimistic: hide form contents immediately so the user sees feedback
    // before the server round-trip + next poll cycle completes.
    setSubmitted(true);
    try {
      const edits = approved && isEdited ? draft : null;
      const fb = feedbackHasAnyRating(feedback) ? feedback : null;
      await approvePlan(runId, approved, edits, fb);
      onResolved(approved);
    } catch (e) {
      // Revert optimistic state so the user can retry.
      setSubmitted(false);
      setErrorMsg(e instanceof Error ? e.message : "Failed to submit decision");
    } finally {
      setBusy(false);
    }
  }

  if (submitted) {
    return (
      <div className="border border-amber-700 bg-amber-950/30 rounded p-5 text-sm text-amber-200">
        <div className="flex items-center gap-3">
          <span className="inline-block w-3 h-3 rounded-full bg-amber-400 animate-pulse" />
          <span>Submitting your decision...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-amber-700 bg-amber-950/30 rounded p-5 space-y-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-semibold text-amber-300">Review the plan</h3>
        <div className="flex items-center gap-2">
          {isEdited && (
            <span className="text-xs px-2 py-0.5 rounded bg-amber-700/50 text-amber-100 border border-amber-600">
              Edited
            </span>
          )}
          <span className="text-xs text-amber-400">
            No paid generation runs until you approve.
          </span>
        </div>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Hook</div>
        <input
          type="text"
          value={draft.hook}
          onChange={(e) => setDraft((d) => ({ ...d, hook: e.target.value }))}
          disabled={busy}
          className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-base focus:outline-none focus:border-amber-500"
        />
        <RatingControl
          value={getFeedback("hook")}
          onChange={(next) => setFieldFeedback("hook", next)}
        />
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Voiceover</div>
        <textarea
          value={draft.voiceover_text}
          onChange={(e) => setDraft((d) => ({ ...d, voiceover_text: e.target.value }))}
          disabled={busy}
          rows={4}
          className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm leading-relaxed focus:outline-none focus:border-amber-500"
        />
        <RatingControl
          value={getFeedback("voiceover_text")}
          onChange={(next) => setFieldFeedback("voiceover_text", next)}
        />
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase text-neutral-400">
          Scenes ({draft.scenes.length})
        </div>
        {draft.scenes.map((s) => (
          <div
            key={s.scene_idx}
            className="border border-neutral-800 rounded p-3 text-sm space-y-2"
          >
            <div className="flex justify-between items-baseline">
              <div className="font-medium">Scene {s.scene_idx + 1}</div>
              <div className="flex items-center gap-2 text-neutral-400 text-xs">
                <span>{s.duration_s.toFixed(1)}s</span>
                <select
                  value={s.motion}
                  onChange={(e) =>
                    updateScene(s.scene_idx, { motion: e.target.value as Motion })
                  }
                  disabled={busy}
                  className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-xs text-neutral-200 focus:outline-none focus:border-amber-500"
                >
                  {MOTIONS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-neutral-500 mb-1">
                Voiceover excerpt
              </div>
              <textarea
                value={s.voiceover_excerpt}
                onChange={(e) =>
                  updateScene(s.scene_idx, { voiceover_excerpt: e.target.value })
                }
                disabled={busy}
                rows={2}
                className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-200 focus:outline-none focus:border-amber-500"
              />
              <RatingControl
                value={getFeedback(`scenes[${s.scene_idx}].voiceover_excerpt`)}
                onChange={(next) =>
                  setFieldFeedback(`scenes[${s.scene_idx}].voiceover_excerpt`, next)
                }
              />
            </div>
            <div>
              <div className="text-xs uppercase text-neutral-500 mb-1">
                Visual prompt
              </div>
              <textarea
                value={s.visual_prompt}
                onChange={(e) =>
                  updateScene(s.scene_idx, { visual_prompt: e.target.value })
                }
                disabled={busy}
                rows={2}
                className="w-full bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-xs italic text-neutral-300 focus:outline-none focus:border-amber-500"
              />
              <RatingControl
                value={getFeedback(`scenes[${s.scene_idx}].visual_prompt`)}
                onChange={(next) =>
                  setFieldFeedback(`scenes[${s.scene_idx}].visual_prompt`, next)
                }
              />
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-2 items-center">
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
        {errorMsg && (
          <span className="text-sm text-red-400">{errorMsg}</span>
        )}
      </div>
    </div>
  );
}
