"use client";

import Link from "next/link";

import type { RunSnapshot } from "@/lib/types";

export function RunCard({ run }: { run: RunSnapshot }) {
  return (
    <Link
      href={`/runs/${run.run_id}`}
      className="block border border-neutral-800 hover:border-neutral-600 rounded p-4 space-y-2"
    >
      <div className="text-xs font-mono text-neutral-500">{run.run_id}</div>
      <div className="text-sm line-clamp-2">{run.brief}</div>
      <div className="flex justify-between text-xs text-neutral-400">
        <span>{run.duration_s}s</span>
        <span>{run.status}</span>
      </div>
    </Link>
  );
}
