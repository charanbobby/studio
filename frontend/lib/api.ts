import type { FieldFeedback } from "@/components/RatingControl";

import type { ReelFeedback, RunSnapshot, ScriptPlan } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function createRun(input: {
  prompt: string;
  duration_s: number;
  with_music: boolean;
}): Promise<{ run_id: string }> {
  const r = await fetch(`${BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(`createRun failed: ${r.status}`);
  return r.json();
}

export async function getRun(id: string): Promise<RunSnapshot> {
  const r = await fetch(`${BASE}/api/runs/${id}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`getRun failed: ${r.status}`);
  return r.json();
}

export async function listRuns(): Promise<RunSnapshot[]> {
  const r = await fetch(`${BASE}/api/runs`, { cache: "no-store" });
  if (!r.ok) throw new Error(`listRuns failed: ${r.status}`);
  return r.json();
}

export async function approvePlan(
  id: string,
  approved: boolean,
  edits: ScriptPlan | null = null,
  feedback: Record<string, FieldFeedback> | null = null,
): Promise<void> {
  const r = await fetch(`${BASE}/api/runs/${id}/approve-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, edits, feedback }),
  });
  if (!r.ok) throw new Error(`approvePlan failed: ${r.status}`);
}

export function reelUrl(id: string): string {
  return `${BASE}/api/runs/${id}/reel.mp4`;
}

export async function submitReelFeedback(
  id: string,
  fb: ReelFeedback,
): Promise<void> {
  const r = await fetch(`${BASE}/api/runs/${id}/reel-feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fb),
  });
  if (!r.ok) throw new Error(`submitReelFeedback failed: ${r.status}`);
}
