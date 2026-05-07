import { listRuns } from "@/lib/api";
import { RunCard } from "@/components/RunCard";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await listRuns();
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Past runs</h2>
      {runs.length === 0 ? (
        <div className="text-neutral-400">No runs yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {runs.map((r) => (
            <RunCard key={r.run_id} run={r} />
          ))}
        </div>
      )}
    </div>
  );
}
