"use client";

import { useState } from "react";

import { submitReelFeedback } from "@/lib/api";
import type { ReelFeedback, ReelRating } from "@/lib/types";

const COLORS: Record<NonNullable<ReelRating>, string> = {
  good: "border-emerald-600 text-emerald-400 bg-emerald-950/30",
  partial: "border-amber-600 text-amber-400 bg-amber-950/30",
  bad: "border-red-600 text-red-400 bg-red-950/30",
};

const EMPTY: ReelFeedback = {
  reel_quality: null,
  voice_fidelity: null,
  brand_voice_match: null,
  would_ship: null,
  note: "",
};

function RatingRow({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: ReelRating;
  onChange: (next: ReelRating) => void;
}) {
  function toggle(r: NonNullable<ReelRating>) {
    onChange(value === r ? null : r);
  }

  return (
    <div className="space-y-1.5">
      <div>
        <div className="text-sm text-neutral-200">{label}</div>
        <div className="text-xs text-neutral-500">{description}</div>
      </div>
      <div className="flex gap-1.5">
        {(["good", "partial", "bad"] as const).map((r) => {
          const active = value === r;
          return (
            <button
              key={r}
              type="button"
              onClick={() => toggle(r)}
              className={`text-[10px] uppercase tracking-wider px-2.5 py-1 rounded border transition ${
                active
                  ? COLORS[r]
                  : "border-neutral-800 text-neutral-500 hover:border-neutral-600"
              }`}
            >
              {r}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function ReelFeedbackPanel({ runId }: { runId: string }) {
  const [fb, setFb] = useState<ReelFeedback>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  function set<K extends keyof ReelFeedback>(key: K, value: ReelFeedback[K]) {
    setFb((f) => ({ ...f, [key]: value }));
  }

  async function submit() {
    setBusy(true);
    setErrorMsg(null);
    try {
      await submitReelFeedback(runId, fb);
      setSubmitted(true);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to submit feedback");
    } finally {
      setBusy(false);
    }
  }

  if (submitted) {
    return (
      <div className="border border-emerald-700 bg-emerald-950/30 rounded p-5 text-sm text-emerald-200">
        Thanks for the feedback. Logged to Langfuse for this run.
      </div>
    );
  }

  const hasAnyInput =
    fb.reel_quality !== null ||
    fb.voice_fidelity !== null ||
    fb.brand_voice_match !== null ||
    fb.would_ship !== null ||
    fb.note.trim().length > 0;

  return (
    <div className="border border-neutral-800 bg-neutral-950/60 rounded p-5 space-y-5">
      <div>
        <h3 className="text-base font-semibold text-neutral-100">
          Rate the final reel
        </h3>
        <p className="text-xs text-neutral-500 mt-1">
          One pass on the finished output. Feeds Langfuse and the eval dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <RatingRow
          label="Reel quality"
          description="visuals + voiceover + stitch"
          value={fb.reel_quality}
          onChange={(v) => set("reel_quality", v)}
        />
        <RatingRow
          label="Voice clone fidelity"
          description="does it sound like you?"
          value={fb.voice_fidelity}
          onChange={(v) => set("voice_fidelity", v)}
        />
        <RatingRow
          label="Brand voice match"
          description="does it speak the brief's voice?"
          value={fb.brand_voice_match}
          onChange={(v) => set("brand_voice_match", v)}
        />
      </div>

      <div className="space-y-1.5">
        <div className="text-sm text-neutral-200">Would you ship this?</div>
        <div className="flex gap-1.5">
          {(["yes", "no"] as const).map((opt) => {
            const isYes = opt === "yes";
            const active =
              fb.would_ship === (isYes ? true : false);
            const activeColor = isYes
              ? "border-emerald-600 text-emerald-400 bg-emerald-950/30"
              : "border-red-600 text-red-400 bg-red-950/30";
            return (
              <button
                key={opt}
                type="button"
                onClick={() =>
                  set(
                    "would_ship",
                    fb.would_ship === (isYes ? true : false) ? null : isYes,
                  )
                }
                className={`text-[10px] uppercase tracking-wider px-2.5 py-1 rounded border transition ${
                  active
                    ? activeColor
                    : "border-neutral-800 text-neutral-500 hover:border-neutral-600"
                }`}
              >
                {opt}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-500 mb-1">
          any other notes? (optional)
        </div>
        <input
          type="text"
          value={fb.note}
          onChange={(e) => set("note", e.target.value)}
          placeholder="one-line freetext"
          className="w-full bg-neutral-900 border border-neutral-800 rounded px-3 py-2 text-sm placeholder-neutral-600 focus:outline-none focus:border-neutral-600"
        />
      </div>

      <div className="flex gap-3 items-center">
        <button
          onClick={submit}
          disabled={busy || !hasAnyInput}
          className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-800 disabled:text-neutral-500 px-5 py-2 rounded font-medium text-sm"
        >
          {busy ? "Submitting..." : "Submit feedback"}
        </button>
        {errorMsg && (
          <span className="text-sm text-red-400">{errorMsg}</span>
        )}
      </div>
    </div>
  );
}
