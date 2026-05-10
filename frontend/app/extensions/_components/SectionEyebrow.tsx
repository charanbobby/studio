import type { ReactNode } from "react";

export function SectionEyebrow({
  index,
  label,
  children,
}: {
  index: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <header className="mb-10 mt-24">
      <div className="flex items-baseline gap-3 font-mono text-[0.7rem] uppercase tracking-[0.22em] text-amber-400/80">
        <span className="text-amber-300">{index}</span>
        <span className="h-px w-8 bg-amber-400/40" />
        <span className="text-neutral-400">{label}</span>
      </div>
      <h2 className="font-display mt-3 text-4xl font-medium leading-[1.05] tracking-tight text-white sm:text-5xl">
        {children}
      </h2>
    </header>
  );
}
