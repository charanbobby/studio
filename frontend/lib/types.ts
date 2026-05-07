export type Tone = "energetic" | "warm" | "informative" | "promotional" | "neutral";
export type Motion = "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static";

export interface Scene {
  scene_idx: number;
  duration_s: number;
  visual_prompt: string;
  voiceover_excerpt: string;
  motion: Motion;
}

export interface ScriptPlan {
  hook: string;
  scenes: Scene[];
  voiceover_text: string;
  voice_style: string;
  music_mood: string | null;
  aspect_ratio: "9:16";
}

export interface RunSnapshot {
  run_id: string;
  brief: string;
  duration_s: number;
  with_music: boolean;
  status: "pending" | "running" | "awaiting_approval" | "completed" | "rejected" | "error";
  plan?: ScriptPlan | null;
  reel_path?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunEvent {
  event: string;
  [key: string]: unknown;
}
