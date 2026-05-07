"use client";

import type { RunEvent } from "@/lib/types";

export function CostLedger({ events }: { events: RunEvent[] }) {
  const items = events.filter((e) => typeof (e as Record<string, unknown>).cost_usd === "number");
  if (items.length === 0) return null;
  const total = items.reduce(
    (acc, e) => acc + ((e as Record<string, unknown>).cost_usd as number),
    0
  );
  return (
    <div className="border border-neutral-800 rounded p-3 text-xs font-mono">
      <div className="text-neutral-400 mb-1">Cost ledger (live)</div>
      {items.map((e, i) => (
        <div key={i} className="flex justify-between">
          <span>{(e as Record<string, unknown>).phase as string}</span>
          <span>${((e as Record<string, unknown>).cost_usd as number).toFixed(4)}</span>
        </div>
      ))}
      <div className="flex justify-between border-t border-neutral-800 mt-1 pt-1 font-semibold">
        <span>Total</span>
        <span>${total.toFixed(4)}</span>
      </div>
    </div>
  );
}
