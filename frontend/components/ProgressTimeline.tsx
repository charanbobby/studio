"use client";

import type { RunEvent } from "@/lib/types";

const STEPS = [
  { key: "extract_start", label: "Extract intent" },
  { key: "plan_end", label: "Plan generated" },
  { key: "awaiting_approval", label: "Awaiting approval" },
  { key: "execute_start", label: "Generating media" },
  { key: "tts_done", label: "Voiceover done" },
  { key: "execute_end", label: "Media complete" },
  { key: "stitch_end", label: "Reel stitched" },
] as const;

export function ProgressTimeline({ events }: { events: RunEvent[] }) {
  const seen = new Set(events.map((e) => e.event));
  return (
    <ol className="border-l border-neutral-700 pl-5 space-y-2 text-sm">
      {STEPS.map((s) => {
        const done = seen.has(s.key);
        return (
          <li key={s.key} className="relative">
            <span
              className={`absolute -left-[26px] top-1 w-3 h-3 rounded-full ${
                done ? "bg-emerald-400" : "bg-neutral-700"
              }`}
            />
            <span className={done ? "text-neutral-100" : "text-neutral-500"}>
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
