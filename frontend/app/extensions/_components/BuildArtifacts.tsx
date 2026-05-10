import Link from "next/link";

type Artifact = { kind: string; title: string; href: string; note?: string };

const ARTIFACTS: Artifact[] = [
  {
    kind: "repo",
    title: "github.com/charanbobby/studio",
    href: "https://github.com/charanbobby/studio",
    note: "this app + all helper extensions",
  },
  {
    kind: "spec",
    title: "/extensions page design",
    href: "https://github.com/charanbobby/studio/blob/main/docs/superpowers/specs/2026-05-10-extensions-page-design.md",
    note: "this page",
  },
  {
    kind: "spec",
    title: "Helper as a Service",
    href: "https://github.com/charanbobby/studio/blob/main/docs/superpowers/specs/2026-05-10-helper-as-a-service-design.md",
    note: "HTTP service spec",
  },
  {
    kind: "spec",
    title: "MCP wrapper",
    href: "https://github.com/charanbobby/studio/blob/main/docs/superpowers/specs/2026-05-10-mcp-wrapper-design.md",
    note: "tool surface for LLM agents",
  },
  {
    kind: "plan",
    title: "Combined implementation plan",
    href: "https://github.com/charanbobby/studio/blob/main/docs/superpowers/plans/2026-05-10-helper-service-mcp-extensions-page.md",
    note: "~25 tasks, three phases, TDD",
  },
  {
    kind: "skill",
    title: "SKILL.md",
    href: "https://github.com/charanbobby/studio/blob/main/SKILL.md",
    note: "silent-first lessons baked into the container",
  },
];

const KIND_COLOR: Record<string, string> = {
  repo:  "text-amber-300",
  spec:  "text-sky-300",
  plan:  "text-emerald-300",
  skill: "text-rose-300",
};

export function BuildArtifacts() {
  return (
    <ul className="my-8 grid gap-2 border-y border-neutral-800 py-2">
      {ARTIFACTS.map((a) => (
        <li
          key={a.href}
          className="grid grid-cols-[5rem_1fr_auto] items-baseline gap-4 border-b border-neutral-900 px-1 py-3 last:border-b-0 hover:bg-neutral-950/60"
        >
          <span
            className={`font-mono text-[0.65rem] uppercase tracking-[0.22em] ${KIND_COLOR[a.kind]}`}
          >
            {a.kind}
          </span>
          <Link
            href={a.href}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-sm text-white transition-colors hover:text-amber-300"
          >
            {a.title}
            <span aria-hidden="true" className="ml-1 text-neutral-600">
              →
            </span>
          </Link>
          {a.note && (
            <span className="hidden text-xs text-neutral-500 md:inline">
              {a.note}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
