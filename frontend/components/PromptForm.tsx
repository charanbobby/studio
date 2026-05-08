"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createRun } from "@/lib/api";
import { SamplePrompts } from "@/components/SamplePrompts";

export function PromptForm() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(5);
  const [withMusic, setWithMusic] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    try {
      const { run_id } = await createRun({
        prompt: prompt.trim(),
        duration_s: duration,
        with_music: withMusic,
      });
      router.push(`/runs/${run_id}`);
    } catch (e) {
      setErr((e as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4 max-w-2xl">
      <SamplePrompts onPick={(p) => setPrompt(p)} />

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-neutral-300">Prompt</span>
        <textarea
          required
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="bg-neutral-900 border border-neutral-700 rounded p-3 min-h-[120px] font-mono text-sm"
          placeholder="Sur La Table spring kitchen sale, fun energy, food-focused"
        />
      </label>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-neutral-300">
          Duration: {duration}s {duration >= 30 ? " (music auto-on)" : ""}
        </span>
        <input
          type="range"
          min={5}
          max={90}
          step={5}
          value={duration}
          onChange={(e) => {
            const d = parseInt(e.target.value, 10);
            setDuration(d);
            if (d >= 30 && !withMusic) setWithMusic(true);
            if (d < 30 && withMusic) setWithMusic(false);
          }}
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-neutral-300">
        <input
          type="checkbox"
          checked={withMusic}
          onChange={(e) => setWithMusic(e.target.checked)}
        />
        Include background music
      </label>

      {err && <div className="text-red-400 text-sm">{err}</div>}

      <button
        type="submit"
        disabled={submitting || !prompt.trim()}
        className="self-start bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-700 px-5 py-2 rounded font-medium"
      >
        {submitting ? "Starting..." : "Generate Reel"}
      </button>
    </form>
  );
}
