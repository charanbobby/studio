"use client";

import { useEffect, useState } from "react";

import { RunCard } from "@/components/RunCard";
import { listRuns } from "@/lib/api";
import type { RunSnapshot } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSnapshot[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    listRuns()
      .then(setRuns)
      .catch((e) => setErr((e as Error).message));
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Past runs</h2>
      {err && <div className="text-red-400 text-sm mb-4">{err}</div>}
      {runs === null && !err ? (
        <div className="text-neutral-400">Loading...</div>
      ) : runs && runs.length === 0 ? (
        <div className="text-neutral-400">No runs yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {(runs || []).map((r) => (
            <RunCard key={r.run_id} run={r} />
          ))}
        </div>
      )}
    </div>
  );
}
