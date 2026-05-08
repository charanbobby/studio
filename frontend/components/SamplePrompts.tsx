"use client";

import samples from "@/lib/sample_prompts.json";

export function SamplePrompts({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="text-xs uppercase tracking-wide text-neutral-500">
        Try one to start
      </div>
      <div className="flex flex-wrap gap-2">
        {samples.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() => onPick(s.prompt)}
            className="text-xs px-3 py-1.5 rounded-full border border-neutral-700 hover:border-neutral-500 hover:bg-neutral-800/40 transition text-neutral-300"
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
