"use client";

import { useState } from "react";

export type Rating = "good" | "partial" | "bad" | null;

export interface FieldFeedback {
  rating: Rating;
  note: string;
}

const COLORS: Record<NonNullable<Rating>, string> = {
  good: "border-emerald-600 text-emerald-400 bg-emerald-950/30",
  partial: "border-amber-600 text-amber-400 bg-amber-950/30",
  bad: "border-red-600 text-red-400 bg-red-950/30",
};

export function RatingControl({
  value,
  onChange,
}: {
  value: FieldFeedback;
  onChange: (next: FieldFeedback) => void;
}) {
  const [showNote, setShowNote] = useState(value.note.length > 0);

  function setRating(r: Rating) {
    const next: Rating = value.rating === r ? null : r;
    onChange({ ...value, rating: next });
  }

  return (
    <div className="flex flex-col gap-1.5 mt-1.5">
      <div className="flex gap-1.5 items-center">
        {(["good", "partial", "bad"] as const).map((r) => {
          const active = value.rating === r;
          return (
            <button
              key={r}
              type="button"
              onClick={() => setRating(r)}
              className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border transition ${
                active
                  ? COLORS[r]
                  : "border-neutral-800 text-neutral-500 hover:border-neutral-600"
              }`}
            >
              {r}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setShowNote((s) => !s)}
          className="text-[10px] text-neutral-500 hover:text-neutral-300 ml-2"
        >
          {showNote ? "hide note" : "+ note"}
        </button>
      </div>
      {showNote && (
        <input
          type="text"
          value={value.note}
          onChange={(e) => onChange({ ...value, note: e.target.value })}
          placeholder="why? (optional)"
          className="text-xs bg-neutral-900 border border-neutral-800 rounded px-2 py-1 placeholder-neutral-600"
        />
      )}
    </div>
  );
}
