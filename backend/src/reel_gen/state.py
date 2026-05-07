"""Typed state object carried through the LangGraph state machine."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ExtractedIntent(BaseModel):
    topic: str
    tone: Literal["energetic", "warm", "informative", "promotional", "neutral"] = "neutral"
    audience: str = "general"
    brand_voice: str | None = None
    notes: str | None = None  # e.g. "AMBIGUOUS_BRIEF"


class Scene(BaseModel):
    scene_idx: int = Field(ge=0)
    duration_s: float = Field(gt=0)
    visual_prompt: str
    voiceover_excerpt: str
    motion: Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "static"] = "zoom_in"


class ScriptPlan(BaseModel):
    hook: str
    scenes: list[Scene]
    voiceover_text: str
    voice_style: str = "neutral"
    music_mood: str | None = None
    aspect_ratio: Literal["9:16"] = "9:16"


class CostEntry(BaseModel):
    phase: str   # "extract", "plan", "tts", "image", "music"
    provider: str  # "openrouter", "elevenlabs", "replicate"
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    units: float | None = None     # generic units when no token concept (image count, audio seconds)
    unit_label: str | None = None  # "images", "audio_seconds"
    cost_usd: float
    timestamp: str  # ISO8601


class NodeError(BaseModel):
    node: str
    message: str
    fatal: bool = False


class CaptionWord(BaseModel):
    text: str
    start_s: float
    end_s: float


class ReelState(BaseModel):
    run_id: str
    brief: str
    duration_s: int = Field(ge=3, le=120)
    with_music: bool = False

    intent: ExtractedIntent | None = None
    plan: ScriptPlan | None = None

    voiceover_path: Path | None = None
    image_paths: list[Path] = Field(default_factory=list)
    music_path: Path | None = None
    captions: list[CaptionWord] | None = None
    reel_path: Path | None = None

    approved: bool | None = None  # None = awaiting; True = approved; False = rejected

    cost_ledger: list[CostEntry] = Field(default_factory=list)
    errors: list[NodeError] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
