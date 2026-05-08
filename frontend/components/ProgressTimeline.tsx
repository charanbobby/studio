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
  // The "active" step is the FIRST step in STEPS whose key is NOT in seen.
  // If all steps are done, no active dot.
  const activeKey = STEPS.find((s) => !seen.has(s.key))?.key ?? null;
  return (
    <ol className="border-l border-neutral-700 pl-5 space-y-2 text-sm">
      {STEPS.map((s) => {
        const done = seen.has(s.key);
        const active = !done && s.key === activeKey;
        let dotClass = "bg-neutral-700";
        if (done) dotClass = "bg-emerald-400";
        else if (active) dotClass = "bg-indigo-500 animate-pulse ring-2 ring-indigo-500/40";
        let textClass = "text-neutral-500";
        if (done) textClass = "text-neutral-100";
        else if (active) textClass = "text-indigo-200";
        return (
          <li key={s.key} className="relative">
            <span
              className={`absolute -left-[26px] top-1 w-3 h-3 rounded-full ${dotClass}`}
            />
            <span className={textClass}>{s.label}</span>
            {active && (
              <span
                className="ml-2 inline-block text-indigo-300 animate-pulse"
                aria-label="in progress"
              >
                ...
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
