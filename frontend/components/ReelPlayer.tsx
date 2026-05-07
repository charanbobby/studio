"use client";

import { reelUrl } from "@/lib/api";

export function ReelPlayer({ runId }: { runId: string }) {
  const url = reelUrl(runId);
  return (
    <div className="space-y-3">
      <video src={url} controls className="w-full max-w-sm rounded shadow-lg bg-black" />
      <a
        href={url}
        download
        className="inline-block text-sm text-indigo-400 hover:text-indigo-300 underline"
      >
        Download MP4
      </a>
    </div>
  );
}
