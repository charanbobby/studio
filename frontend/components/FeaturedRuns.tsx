import { FeaturedTile, type FeaturedRun } from "./FeaturedTile";

const PINNED_RUN_ID = "05821f3a380d";
const LIMIT = 3;

function backendUrl(): string {
  return process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";
}

async function fetchFeatured(): Promise<FeaturedRun[]> {
  try {
    const res = await fetch(
      `${backendUrl()}/api/featured-runs?pin=${PINNED_RUN_ID}&limit=${LIMIT}`,
      { cache: "no-store" },
    );
    if (!res.ok) return [];
    return (await res.json()) as FeaturedRun[];
  } catch {
    return [];
  }
}

export async function FeaturedRuns() {
  const runs = await fetchFeatured();
  if (runs.length === 0) return null;

  // Tailwind cannot generate dynamic class strings via interpolation; spell
  // each layout out so the JIT picks them up. Mobile (<sm) collapses to one
  // column in every case.
  const layoutClass =
    runs.length === 1
      ? "grid grid-cols-1 max-w-[200px] mx-auto gap-4"
      : runs.length === 2
        ? "grid grid-cols-1 sm:grid-cols-2 max-w-[420px] mx-auto gap-4"
        : "grid grid-cols-1 sm:grid-cols-3 gap-4";

  return (
    <section className="mb-10" data-testid="featured-runs">
      <h3 className="text-xs uppercase tracking-wider text-neutral-500 mb-4">
        Featured runs
      </h3>
      <div className={layoutClass}>
        {runs.map((r) => (
          <FeaturedTile key={r.run_id} run={r} />
        ))}
      </div>
    </section>
  );
}
