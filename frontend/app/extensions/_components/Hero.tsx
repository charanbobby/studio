export function Hero() {
  return (
    <header className="relative pt-12 pb-16">
      <div className="font-mono text-[0.7rem] uppercase tracking-[0.28em] text-amber-400/80">
        <span className="text-amber-300">Extensions</span>
        <span className="mx-3 text-neutral-700">/</span>
        <span className="text-neutral-500">a take-home that grew</span>
      </div>
      <h1 className="font-display mt-6 text-[clamp(3rem,8vw,5.5rem)] font-medium leading-[0.95] tracking-tight text-white">
        Demo videos
        <br />
        <span className="italic text-amber-300">as code.</span>
      </h1>
      <p className="font-mono mt-6 max-w-md text-sm text-neutral-400">
        Configurable. Repeatable. Cheap to re-cut. The video below was generated
        end-to-end by a pipeline I built while building this app.
      </p>
      <div className="mt-10 flex items-center gap-4">
        <a
          href="#what-i-extended"
          className="font-mono text-xs uppercase tracking-[0.22em] text-amber-300 underline decoration-amber-700 decoration-1 underline-offset-[6px] transition hover:text-white hover:decoration-amber-300"
        >
          See the extensions ↓
        </a>
      </div>
    </header>
  );
}
