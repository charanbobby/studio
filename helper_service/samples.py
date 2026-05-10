import json, shutil, os
from datetime import datetime, timezone
from pathlib import Path

def _samples_dir() -> Path:
    """Lazily resolve SAMPLES_DIR to pick up HELPER_DATA_DIR env var on each call."""
    data_dir = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
    return data_dir / "samples"

def _sample_dir(job_id: str) -> Path:
    """Lazily resolve sample_dir path."""
    return _samples_dir() / job_id

def save_sample(job_id: str, workdir: Path, goal: str,
                target_url: str, beats_summary: list[str]) -> None:
    samples_dir = _samples_dir()
    samples_dir.mkdir(parents=True, exist_ok=True)
    sd = _sample_dir(job_id)
    sd.mkdir(exist_ok=True)
    shutil.copy(workdir / "final.mp4", sd / "final.mp4")
    manifest = {
        "job_id": job_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "goal": goal,
        "target_url": target_url,
        "beats_summary": beats_summary,
        "final_url": f"/helper/samples/{job_id}/final.mp4",
    }
    (sd / "manifest.json").write_text(json.dumps(manifest, indent=2))

def list_samples() -> list[dict]:
    samples_dir = _samples_dir()
    if not samples_dir.exists():
        return []
    out = []
    for d in sorted(samples_dir.iterdir()):
        m = d / "manifest.json"
        if m.exists():
            out.append(json.loads(m.read_text()))
    return out
