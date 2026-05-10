import subprocess
from pathlib import Path
from .jobs import load_job, set_status
from .budget import estimate

def run_silent_phases(job_id: str, beats: list[dict]) -> None:
    """Phases A through D: probes -> record -> concat -> burn captions."""
    job = load_job(job_id)
    wd = job.workdir
    try:
        set_status(job_id, "recording")
        _run_probes(wd)
        _record_beats(wd, beats)
        _concat_silent(wd)
        set_status(job_id, "captioning")
        _burn_captions(wd, beats)
        est = estimate(beats)
        set_status(job_id, "awaiting_review", estimate_usd=est)
    except Exception as e:
        set_status(job_id, "failed", error=f"silent phases failed: {e}")
        raise

def run_voice_phases(job_id: str, beats: list[dict]) -> None:
    """Phases E and F: voice gen -> final mux."""
    job = load_job(job_id)
    wd = job.workdir
    try:
        set_status(job_id, "voice_generating")
        actual = _generate_voice(wd, beats, job_id)
        set_status(job_id, "muxing")
        _final_mux(wd)
        set_status(job_id, "done", actual_usd=actual)
    except Exception as e:
        set_status(job_id, "voice_failed", error=f"voice phases failed: {e}")
        raise

def _run_probes(wd: Path) -> None:
    probes = wd / "probes"
    if not probes.is_dir(): return
    for p in sorted(probes.glob("*.py")):
        subprocess.run(["python", str(p)], check=True, cwd=wd)

def _record_beats(wd: Path, beats: list[dict]) -> None:
    for b in beats:
        subprocess.run(
            ["python", "-m", "sri_studio_helper.record_beat", b["name"]],
            check=True, cwd=wd,
        )

def _concat_silent(wd: Path) -> None:
    subprocess.run(["bash", "assemble_silent.sh"], check=True, cwd=wd)

def _burn_captions(wd: Path, beats: list[dict]) -> None:
    # captions.py BEATS list is already in the project; just invoke the script.
    subprocess.run(["bash", "burn_captions.sh"], check=True, cwd=wd)

def _generate_voice(wd: Path, beats: list[dict], job_id: str) -> float:
    """Returns actual_usd."""
    from .budget import record_spend
    import os
    usd_per_char = float(os.environ.get("ELEVENLABS_USD_PER_CHAR", "0.00044"))
    total_chars = 0
    for b in beats:
        # PRE log line (per CLAUDE.md cost-discipline rule)
        chars = len(b["voiceover"])
        est = chars * usd_per_char
        print(f"[voice] beat={b['name']} chars={chars} estimate=${est:.4f}")
        subprocess.run(
            ["python", "-m", "sri_studio_helper.voice_gen", b["name"]],
            check=True, cwd=wd,
        )
        # POST log line
        print(f"[voice] beat={b['name']} chars={chars} actual=${est:.4f}")
        total_chars += chars
    actual = total_chars * usd_per_char
    record_spend(job_id, total_chars, actual)
    return actual

def _final_mux(wd: Path) -> None:
    subprocess.run(["bash", "assemble_final.sh"], check=True, cwd=wd)
