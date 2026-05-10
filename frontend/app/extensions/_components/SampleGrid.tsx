import canonical from './canonical-sample.json';

type Sample = {
  job_id: string;
  generated_at: string;
  goal: string;
  target_url: string;
  final_url: string;
  is_highlight?: boolean;
  highlight_caption?: string;
};

async function fetchLiveSamples(): Promise<Sample[]> {
  const base = process.env.HELPER_BASE_URL ?? 'https://studio.sshub.dev';
  try {
    const r = await fetch(`${base}/helper/samples`, { next: { revalidate: 60 } });
    if (!r.ok) return [];
    return (await r.json()) as Sample[];
  } catch {
    return [];
  }
}

export default async function SampleGrid() {
  const live = await fetchLiveSamples();
  const all: Sample[] = [canonical as Sample, ...live.filter(s => s.job_id !== canonical.job_id)];
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {all.map(s => (
        <figure key={s.job_id} className="rounded-lg border border-neutral-800 p-4">
          <video controls preload="metadata" className="w-full rounded">
            <source src={s.final_url} type="video/mp4" />
          </video>
          <figcaption className="mt-2 text-sm text-neutral-300">
            {s.is_highlight ? <strong>{s.highlight_caption}</strong> : s.goal}
            <div className="text-xs text-neutral-500 mt-1">{s.target_url}</div>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
