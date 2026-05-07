"use client";

import { useEffect, useRef, useState } from "react";

import type { RunEvent } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function useRunStream(runId: string | null): RunEvent[] {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;
    const url = `${BASE}/api/runs/${runId}/stream`;
    const es = new EventSource(url);
    sourceRef.current = es;
    const handler = (e: MessageEvent) => {
      try {
        const parsed: RunEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, parsed]);
        if (parsed.event === "run_complete") es.close();
      } catch {
        // ignore malformed events
      }
    };
    es.onmessage = handler;
    es.addEventListener("extract_start", handler);
    es.addEventListener("plan_end", handler);
    es.addEventListener("awaiting_approval", handler);
    es.addEventListener("plan_decision", handler);
    es.addEventListener("execute_start", handler);
    es.addEventListener("tts_done", handler);
    es.addEventListener("image_done", handler);
    es.addEventListener("execute_end", handler);
    es.addEventListener("stitch_start", handler);
    es.addEventListener("stitch_end", handler);
    es.addEventListener("error", handler);
    es.addEventListener("run_complete", handler);
    return () => {
      es.close();
    };
  }, [runId]);

  return events;
}
