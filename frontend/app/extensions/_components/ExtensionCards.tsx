type Extension = {
  ord: string;
  title: string;
  blurb: string;
  api?: string;
  endpoint?: string;
};

const EXTENSIONS: Extension[] = [
  {
    ord: "01",
    title: "Sri Studio Helper",
    blurb:
      "Silent-first screencast pipeline. Records browser scenes via Playwright, burns captions in BEFORE generating voice, and only fires ElevenLabs after a human-reviewed silent cut. Re-cuts are cheap; voice tokens are not.",
    api: "sri_studio_helper/",
    endpoint: "Python package",
  },
  {
    ord: "02",
    title: "Helper as a Service",
    blurb:
      "The pipeline above, fronted by an HTTP API. POST a project tarball, block on the silent-with-captions preview + cost estimate, POST again to approve and render the voiced final.",
    api: "/helper/jobs",
    endpoint: "HTTPS · X-Helper-Key",
  },
  {
    ord: "03",
    title: "MCP wrapper",
    blurb:
      "A local-stdio MCP server that exposes the HTTP API as four typed tools. An LLM agent (Claude Code) can call helper_render_silent / helper_render_voice without curl, and load SKILL.md as system context with helper_skill.",
    api: "helper_render_*",
    endpoint: "MCP · stdio",
  },
];

export function ExtensionCards() {
  return (
    <div className="my-10 grid gap-4 md:grid-cols-3">
      {EXTENSIONS.map((e) => (
        <article
          key={e.ord}
          className="group relative flex flex-col overflow-hidden rounded-md border border-neutral-800 bg-neutral-950/60 p-6 transition-colors hover:border-amber-400/60"
        >
          <div className="absolute right-4 top-4 font-mono text-[0.65rem] uppercase tracking-[0.22em] text-neutral-600 group-hover:text-amber-400/70">
            {e.ord}
          </div>
          <h3 className="font-display text-2xl font-medium leading-tight text-white">
            {e.title}
          </h3>
          <p className="mt-3 flex-1 text-sm leading-relaxed text-neutral-400">
            {e.blurb}
          </p>
          {e.api && (
            <div className="mt-5 border-t border-neutral-800 pt-4">
              <div className="font-mono text-[0.7rem] text-amber-300/90">
                {e.api}
              </div>
              {e.endpoint && (
                <div className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.18em] text-neutral-500">
                  {e.endpoint}
                </div>
              )}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
