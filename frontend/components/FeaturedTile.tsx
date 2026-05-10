export interface FeaturedRun {
  run_id: string;
  brief: string;
  reel_url: string;
  completed_at: string | null;
  pinned: boolean;
}

export function FeaturedTile({ run }: { run: FeaturedRun }) {
  const borderClass = run.pinned
    ? "border-amber-500 ring-1 ring-amber-500/20"
    : "border-neutral-800";

  return (
    <div
      className="flex flex-col gap-2"
      data-testid="featured-tile"
      data-pinned={run.pinned}
    >
      <div
        className={`relative aspect-[9/16] bg-black rounded-md overflow-hidden border ${borderClass}`}
      >
        {run.pinned && (
          <span className="absolute top-1.5 left-1.5 z-10 bg-amber-500/90 text-neutral-950 font-mono text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-sm">
            Pinned
          </span>
        )}
        <video
          src={run.reel_url}
          controls
          preload="metadata"
          playsInline
          className="absolute inset-0 w-full h-full object-contain bg-black"
        />
      </div>
      <p className="text-xs text-neutral-400 line-clamp-2 leading-snug">
        {run.brief}
      </p>
    </div>
  );
}
