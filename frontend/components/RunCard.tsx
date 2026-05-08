"use client";

import Link from "next/link";

import type { RunSnapshot } from "@/lib/types";

const STATUS_STYLES: Record<RunSnapshot["status"], { dot: string; text: string; label: string }> = {
  pending:            { dot: "bg-neutral-500", text: "text-neutral-400", label: "Pending" },
  running:            { dot: "bg-blue-500 animate-pulse", text: "text-blue-300", label: "Running" },
  awaiting_approval:  { dot: "bg-amber-500 animate-pulse", text: "text-amber-300", label: "Awaiting approval" },
  completed:          { dot: "bg-emerald-500", text: "text-emerald-300", label: "Completed" },
  rejected:           { dot: "bg-neutral-600", text: "text-neutral-400", label: "Rejected" },
  error:              { dot: "bg-red-500", text: "text-red-300", label: "Error" },
};

function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const sec = Math.max(1, Math.floor((now - then) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function RunCard({ run }: { run: RunSnapshot }) {
  const status = STATUS_STYLES[run.status] || STATUS_STYLES.pending;
  const hasReel = run.status === "completed";
  return (
    <Link
      href={`/runs/${run.run_id}`}
      className="block border border-neutral-800 hover:border-neutral-600 hover:bg-neutral-900/40 rounded-lg p-5 transition group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          <span className={`uppercase tracking-wide ${status.text}`}>{status.label}</span>
        </div>
        <div className="text-xs text-neutral-500">
          {relativeTime(run.created_at)}
        </div>
      </div>

      <div className="text-base text-neutral-100 leading-relaxed line-clamp-3 mb-4 group-hover:text-white">
        {run.brief}
      </div>

      <div className="flex items-center justify-between text-xs text-neutral-500">
        <div className="flex items-center gap-3">
          <span className="font-medium text-neutral-300">{run.duration_s}s</span>
          {run.with_music && <span>+ music</span>}
          {hasReel && (
            <span className="text-emerald-400 flex items-center gap-1">
              <span>▶</span>
              <span>Reel</span>
            </span>
          )}
        </div>
        <code className="font-mono text-[10px] opacity-50">{run.run_id}</code>
      </div>
    </Link>
  );
}
