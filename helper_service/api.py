import asyncio, os, json
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

from .auth import require_helper_key
from .jobs import create_job, load_job, set_status
from .extract import extract_project, ExtractError
from .runner import run_silent_phases, run_voice_phases
from .budget import gate_voice, remaining_today, estimate
from .samples import save_sample, list_samples
from .disk import refuse_if_low
from .paths import DATA_DIR, JOBS_DIR, SAMPLES_DIR, sample_dir
from .cleanup import cleanup_loop

app = FastAPI(title="Sri Studio Helper Service", version="0.1.0")

@app.on_event("startup")
async def _start_cleanup():
    asyncio.create_task(cleanup_loop())

# --- Public endpoints (no auth) ---

@app.get("/helper/skill", response_class=PlainTextResponse)
def get_skill():
    """Return SKILL.md content."""
    p = Path(os.environ.get("HELPER_SKILL_PATH", "/app/SKILL.md"))
    if not p.exists():
        raise HTTPException(404, "SKILL.md not found")
    return p.read_text()

@app.get("/helper/samples")
def get_samples():
    return list_samples()

@app.get("/helper/samples/{job_id}/final.mp4")
def get_sample_final(job_id: str):
    p = sample_dir(job_id) / "final.mp4"
    if not p.exists():
        raise HTTPException(404, "sample not found")
    return FileResponse(p, media_type="video/mp4")

# --- Authed endpoints ---

@app.get("/helper/health", dependencies=[Depends(require_helper_key)])
def health():
    return {
        "ok": True,
        "version": "0.1.0",
        "daily_budget_remaining_usd": remaining_today(),
        "queue_depth": 0,  # sequential; always 0 for v1
    }

@app.post("/helper/jobs", dependencies=[Depends(require_helper_key)])
async def post_job(
    background: BackgroundTasks,
    project: UploadFile = File(...),
    auto_approve: bool = False,
):
    refuse_if_low(DATA_DIR)
    tar = await project.read()
    jid = create_job()
    job = load_job(jid)
    try:
        extract_project(tar, job.workdir)
    except ExtractError as e:
        set_status(jid, "failed", error=str(e))
        raise HTTPException(400, f"unsafe tarball: {e}")
    # Read beats from extracted captions.py
    beats = _load_beats(job.workdir)
    # Run silent phases inline (blocks; spec A section 1 says POST blocks)
    run_silent_phases(jid, beats)
    refreshed = load_job(jid)
    response = {
        "job_id": jid,
        "preview_url": f"/helper/jobs/{jid}/preview.mp4",
        "estimate_usd": refreshed.estimate_usd,
        "status": refreshed.status,
    }
    if auto_approve:
        gate_voice(beats)
        run_voice_phases(jid, beats)
        final_status = load_job(jid)
        response["final_url"] = f"/helper/jobs/{jid}/final.mp4"
        response["status"] = final_status.status
    return response

@app.post("/helper/jobs/{job_id}/voice", dependencies=[Depends(require_helper_key)])
def post_voice(job_id: str, save_as_sample: bool = False,
               goal: str = "", target_url: str = ""):
    job = load_job(job_id)
    if job.status != "awaiting_review":
        raise HTTPException(409, f"job not awaiting_review (current: {job.status})")
    beats = _load_beats(job.workdir)
    gate_voice(beats)
    run_voice_phases(job_id, beats)
    refreshed = load_job(job_id)
    if save_as_sample:
        save_sample(job_id, job.workdir, goal=goal,
                    target_url=target_url,
                    beats_summary=[b["name"] for b in beats])
    return {
        "job_id": job_id,
        "final_url": f"/helper/jobs/{job_id}/final.mp4",
        "status": refreshed.status,
    }

@app.get("/helper/jobs/{job_id}", dependencies=[Depends(require_helper_key)])
def get_job(job_id: str):
    return load_job(job_id).model_dump()

@app.get("/helper/jobs/{job_id}/log", dependencies=[Depends(require_helper_key)])
def get_job_log(job_id: str):
    p = load_job(job_id).workdir / "log.txt"
    if not p.exists(): raise HTTPException(404, "no log")
    return PlainTextResponse(p.read_text())

@app.get("/helper/jobs/{job_id}/preview.mp4",
         dependencies=[Depends(require_helper_key)])
def get_preview(job_id: str):
    p = load_job(job_id).workdir / "preview.mp4"
    if not p.exists(): raise HTTPException(404, "preview not ready")
    return FileResponse(p, media_type="video/mp4")

@app.get("/helper/jobs/{job_id}/final.mp4",
         dependencies=[Depends(require_helper_key)])
def get_final(job_id: str):
    p = load_job(job_id).workdir / "final.mp4"
    if not p.exists(): raise HTTPException(404, "final not ready")
    return FileResponse(p, media_type="video/mp4")

@app.delete("/helper/jobs/{job_id}", dependencies=[Depends(require_helper_key)])
def delete_job(job_id: str):
    import shutil
    job = load_job(job_id)
    shutil.rmtree(job.workdir, ignore_errors=True)
    return {"deleted": job_id}

def _load_beats(workdir: Path) -> list[dict]:
    """Import captions.py from the workdir and return its BEATS list as dicts."""
    import importlib.util, sys
    captions = workdir / "captions.py"
    spec = importlib.util.spec_from_file_location("project_captions", captions)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(workdir))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return [{"name": b["name"], "voiceover": b["voiceover"]} for b in mod.BEATS]
