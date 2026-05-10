type Metric = { label: string; value: string; sub?: string };

const METRICS: Metric[] = [
  { label: "Source",  value: "tarball",      sub: "config + scenes + captions" },
  { label: "Output",  value: "MP4",          sub: "1080×1920, voiced, captioned" },
  { label: "Loop",    value: "silent first", sub: "human reviews before voice fires" },
  { label: "Re-runs", value: "free",         sub: "until the voice phase" },
];

export function MetricsBlock() {
  return (
    <dl className="my-10 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-neutral-800 bg-neutral-800 sm:grid-cols-4">
      {METRICS.map((m) => (
        <div key={m.label} className="bg-neutral-950 px-5 py-6">
          <dt className="font-mono text-[0.65rem] uppercase tracking-[0.22em] text-neutral-500">
            {m.label}
          </dt>
          <dd className="font-display mt-2 text-3xl leading-none text-amber-300">
            {m.value}
          </dd>
          {m.sub && (
            <div className="mt-2 text-xs text-neutral-500 leading-snug">
              {m.sub}
            </div>
          )}
        </div>
      ))}
    </dl>
  );
}
