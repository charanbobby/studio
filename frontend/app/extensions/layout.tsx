import type { ReactNode } from "react";

// Fonts are loaded at the root layout (frontend/app/layout.tsx) so the entire
// studio site uses the same family. This per-route layout only adds the
// /extensions-specific dot-grid background overlay.
export default function ExtensionsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="extensions-root relative">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 opacity-[0.04] mix-blend-overlay [background-image:radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] [background-size:24px_24px]"
      />
      {children}
    </div>
  );
}
