# Helper Service + MCP Wrapper + Extensions Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship sub-projects A (Helper-as-a-Service HTTP API), B (MCP wrapper for Helper), and D (`/extensions` showcase page on studio.sshub.dev) as one coherent release. The hiring-manager-facing page lights up the moment the Helper service is live and the MCP wrapper is installable.

**Architecture:** Three concentric layers. (1) `helper_service/` is a FastAPI app inside a Docker container on the Hetzner VPS, fronting the existing `sri_studio_helper/` CLI pipeline behind an HTTP API. (2) `mcp_server/` is a local-stdio MCP server that maps four tools (`helper_render_silent`, `helper_render_voice`, `helper_render_full`, `helper_skill`) to that HTTP API. (3) Sri Studio's existing Next.js 14 frontend gains a new `/extensions` route (MDX) and a new tile in the existing `FeaturedRuns` grid; the page fetches a new public `GET /helper/samples` endpoint for live samples and falls back to a hand-curated canonical sample (the SANS Find Evil demo) on day zero.

**Tech Stack:**
- **Sub-project A:** FastAPI, Uvicorn, httpx, aiofiles, python-multipart (Python 3.11). Builds on existing `sri_studio_helper/` package (Playwright, ffmpeg, ElevenLabs). Runs in Docker behind nginx on Hetzner VPS.
- **Sub-project B:** Python `mcp` package (Anthropic MCP SDK), httpx. Local stdio transport. Run via `uv run python -m mcp_server`.
- **Sub-project D:** Next.js 14 App Router, MDX (`@next/mdx`), Tailwind, TypeScript. Lives in the existing studio repo at `d:/Python Applications/studio/`.

**Specs:**
- `D:/Python Applications/Sri Studio Helper/docs/superpowers/specs/2026-05-10-helper-as-a-service-design.md` (sub-project A)
- `D:/Python Applications/Sri Studio Helper/docs/superpowers/specs/2026-05-10-mcp-wrapper-design.md` (sub-project B)
- `D:/Python Applications/studio/docs/superpowers/specs/2026-05-10-extensions-page-design.md` (sub-project D)

---

## File Structure

### Helper repo (`D:/Python Applications/Sri Studio Helper/`)

```
sri_studio_helper/        EXISTING; the CLI pipeline. Untouched by this plan.
  Dockerfile              EXISTING; reused as the base of the service image.
  ...

helper_service/           NEW (sub-project A); the FastAPI HTTP service.
  __init__.py
  __main__.py             python -m helper_service entry; just `uvicorn ...` shim.
  api.py                  FastAPI app + route handlers. Imports from runner, auth, budget, samples.
  runner.py               Sequential pipeline orchestrator; shells out to existing scripts.
  auth.py                 X-Helper-Key middleware.
  budget.py               Daily ElevenLabs cap; spend.json reader/writer.
  samples.py              save_as_sample logic + GET /helper/samples handler.
  cleanup.py              Background TTL task that deletes old job workdirs.
  paths.py                Centralized path constants (/data/jobs/, /data/samples/, /data/spend.json).
  models.py               Pydantic request/response models.
  Dockerfile              NEW image that bundles sri_studio_helper + helper_service.
  docker-compose.yml      VPS deploy config.
  nginx-helper.conf       Snippet to merge into studio.sshub.dev nginx server block.
  tests/
    conftest.py           Shared fixtures (tmp_path-based /data dir).
    fixtures/
      tiny_demo.tar.gz    Minimal one-beat project for integration tests.
      canned_voice.mp3    Mocked ElevenLabs response.
    test_estimate.py
    test_spend_log.py
    test_auth.py
    test_disk_guard.py
    test_state_machine.py
    test_samples.py
    test_integration.py

mcp_server/               NEW (sub-project B); the MCP wrapper.
  __init__.py
  __main__.py             python -m mcp_server entry.
  server.py               MCP server registration; tool dispatch.
  tools.py                Four tool functions (render_silent, render_voice, render_full, skill).
  helper_client.py        httpx wrapper over Helper HTTP API.
  tar_project.py          Tar a local dir into a tempfile, with size pre-check.
  config.py               Reads HELPER_BASE_URL, HELPER_AUTH_KEY from env.
  pyproject.toml          mcp_server-specific deps (mcp, httpx).
  tests/
    fixtures/
      tiny_project/       Smallest valid project (config.py + captions.py + scenes/intro.py + probes/check.py).
    test_tools.py
    test_tar.py
    test_config.py
```

### Studio repo (`D:/Python Applications/studio/`)

```
frontend/
  app/
    extensions/
      page.mdx              NEW; the chronological story page.
      _components/
        SampleGrid.tsx      NEW; renders fallback + live samples.
        FeaturedSampleEmbed.tsx  NEW; single-sample embed used in section 2.
        canonical-sample.json    NEW; pinned highlight metadata.
  components/
    FeaturedRuns.tsx        MODIFY; append fixed Extensions tile to the grid.
  next.config.js            MODIFY; enable @next/mdx, add 'mdx' to pageExtensions.
  package.json              MODIFY; add @next/mdx, @mdx-js/react, @types/mdx.
  public/
    samples/
      find-evil-canonical.mp4   NEW; copied from D:/Python Applications/Find Evil - Hackathon/out/Demo_Video.mp4.

playwright/                 EXISTING (assumed; verify in repo). Adds:
  e2e/
    extensions-page.spec.ts NEW; integration test for tile-click-through and section presence.
```

---

# Phase 1 : Helper Service (sub-project A)

## Task 1.1: Scaffold helper_service package and pyproject

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/__init__.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/__main__.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/paths.py`
- Modify: `D:/Python Applications/Sri Studio Helper/pyproject.toml` (add helper_service deps)

- [ ] **Step 1: Create `helper_service/__init__.py`**

```python
"""HTTP service shell over the silent-first sri_studio_helper CLI."""
__version__ = "0.1.0"
```

- [ ] **Step 2: Create `helper_service/__main__.py`**

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "helper_service.api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
```

- [ ] **Step 3: Create `helper_service/paths.py`**

```python
"""Centralized filesystem paths used by the service."""
from pathlib import Path
import os

DATA_DIR    = Path(os.environ.get("HELPER_DATA_DIR", "/data"))
JOBS_DIR    = DATA_DIR / "jobs"
SAMPLES_DIR = DATA_DIR / "samples"
SPEND_FILE  = DATA_DIR / "spend.json"
AUDIT_LOG   = DATA_DIR / "audit.log"

def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id

def sample_dir(job_id: str) -> Path:
    return SAMPLES_DIR / job_id
```

- [ ] **Step 4: Add deps to `pyproject.toml`**

If a `[project]` table doesn't exist yet, add one. Append the helper_service deps:

```toml
[project.optional-dependencies]
service = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "python-multipart>=0.0.9",
    "aiofiles>=23.2",
    "httpx>=0.27",
    "pydantic>=2.6",
]
service-dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
]
```

- [ ] **Step 5: Probe imports in a fresh venv (per CLAUDE.md fail-fast rule)**

Run from `D:/Python Applications/Sri Studio Helper/`:

```bash
uv venv .venv-service --python 3.11
uv pip install --python .venv-service/bin/python -e .[service,service-dev]
.venv-service/bin/python -c "import helper_service; print(helper_service.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add helper_service/ pyproject.toml
git commit -m "feat(helper_service): scaffold package + deps"
```

---

## Task 1.2: Auth middleware (X-Helper-Key)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/auth.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/__init__.py` (empty)
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/conftest.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_auth.py`

- [ ] **Step 1: Write failing test**

`helper_service/tests/test_auth.py`:

```python
import os
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from helper_service.auth import require_helper_key

@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("HELPER_AUTH_KEY", "test-key")
    app = FastAPI()
    @app.get("/secret", dependencies=[Depends(require_helper_key)])
    def secret(): return {"ok": True}
    return TestClient(app)

def test_missing_header_returns_401(app):
    r = app.get("/secret")
    assert r.status_code == 401

def test_wrong_key_returns_401(app):
    r = app.get("/secret", headers={"X-Helper-Key": "nope"})
    assert r.status_code == 401

def test_correct_key_returns_200(app):
    r = app.get("/secret", headers={"X-Helper-Key": "test-key"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run test, verify it fails**

```bash
.venv-service/bin/pytest helper_service/tests/test_auth.py -v
```

Expected: ImportError on `helper_service.auth`.

- [ ] **Step 3: Implement `helper_service/auth.py`**

```python
import os
from fastapi import Header, HTTPException, status

def require_helper_key(x_helper_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("HELPER_AUTH_KEY")
    if not expected:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "HELPER_AUTH_KEY not configured")
    if not x_helper_key or x_helper_key != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "missing or invalid X-Helper-Key")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv-service/bin/pytest helper_service/tests/test_auth.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add helper_service/auth.py helper_service/tests/
git commit -m "feat(helper_service): X-Helper-Key auth middleware"
```

---

## Task 1.3: Budget tracker (daily ElevenLabs cap)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/budget.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_budget.py`

- [ ] **Step 1: Write failing tests**

`helper_service/tests/test_budget.py`:

```python
import json, os
import pytest
from helper_service.budget import estimate, remaining_today, gate_voice, record_spend
from fastapi import HTTPException

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_BUDGET_USD", "1.0")
    monkeypatch.setenv("ELEVENLABS_USD_PER_CHAR", "0.001")  # 1000 chars = $1
    yield

def test_estimate_sums_voiceover_chars():
    beats = [{"voiceover": "abc"}, {"voiceover": "defgh"}]
    assert estimate(beats) == pytest.approx(0.008)  # 8 chars * 0.001

def test_remaining_today_starts_at_full_budget():
    assert remaining_today() == pytest.approx(1.0)

def test_record_spend_decrements_remaining():
    record_spend("job1", chars=500, actual_usd=0.5)
    assert remaining_today() == pytest.approx(0.5)

def test_gate_voice_raises_402_if_estimate_exceeds_remaining():
    record_spend("job1", chars=900, actual_usd=0.9)
    with pytest.raises(HTTPException) as exc:
        gate_voice([{"voiceover": "x" * 200}])  # 200 chars = $0.2; remaining = $0.1
    assert exc.value.status_code == 402
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
.venv-service/bin/pytest helper_service/tests/test_budget.py -v
```

Expected: ImportError on `helper_service.budget`.

- [ ] **Step 3: Implement `helper_service/budget.py`**

```python
import json
import os
from datetime import date
from fastapi import HTTPException
from .paths import SPEND_FILE

def _usd_per_char() -> float:
    return float(os.environ.get("ELEVENLABS_USD_PER_CHAR", "0.00044"))

def _daily_budget() -> float:
    return float(os.environ["DAILY_BUDGET_USD"])

def _today() -> str:
    return date.today().isoformat()

def _load() -> dict:
    if not SPEND_FILE.exists():
        return {"date": _today(), "spent_usd": 0.0, "by_job": {}}
    s = json.loads(SPEND_FILE.read_text())
    if s.get("date") != _today():
        return {"date": _today(), "spent_usd": 0.0, "by_job": {}}
    return s

def _save(s: dict) -> None:
    SPEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    SPEND_FILE.write_text(json.dumps(s, indent=2))

def estimate(beats: list[dict]) -> float:
    chars = sum(len(b["voiceover"]) for b in beats)
    return chars * _usd_per_char()

def remaining_today() -> float:
    return _daily_budget() - _load()["spent_usd"]

def gate_voice(beats: list[dict]) -> None:
    est = estimate(beats)
    rem = remaining_today()
    if est > rem:
        raise HTTPException(
            402,
            detail={"reason": "would_exceed_daily_cap",
                    "remaining": rem, "needed": est},
        )

def record_spend(job_id: str, chars: int, actual_usd: float) -> None:
    s = _load()
    s["spent_usd"] = round(s["spent_usd"] + actual_usd, 6)
    s["by_job"][job_id] = {"chars": chars, "actual_usd": actual_usd}
    _save(s)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv-service/bin/pytest helper_service/tests/test_budget.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add helper_service/budget.py helper_service/tests/test_budget.py
git commit -m "feat(helper_service): daily ElevenLabs budget gate + spend log"
```

---

## Task 1.4: Disk guard

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/disk.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_disk.py`

- [ ] **Step 1: Write failing tests**

`helper_service/tests/test_disk.py`:

```python
import pytest
from helper_service.disk import bytes_free, refuse_if_low

def test_bytes_free_returns_positive_int(tmp_path):
    assert bytes_free(tmp_path) > 0

def test_refuse_if_low_passes_when_room(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_MIN_FREE_BYTES", "1")
    refuse_if_low(tmp_path)  # no raise

def test_refuse_if_low_raises_503_when_low(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_MIN_FREE_BYTES", str(10**18))  # impossibly large
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        refuse_if_low(tmp_path)
    assert exc.value.status_code == 503
```

- [ ] **Step 2: Run, verify fail**

```bash
.venv-service/bin/pytest helper_service/tests/test_disk.py -v
```

- [ ] **Step 3: Implement `helper_service/disk.py`**

```python
import os, shutil
from pathlib import Path
from fastapi import HTTPException

DEFAULT_MIN_FREE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB

def bytes_free(path: Path) -> int:
    return shutil.disk_usage(path).free

def refuse_if_low(path: Path) -> None:
    minimum = int(os.environ.get("HELPER_MIN_FREE_BYTES", DEFAULT_MIN_FREE_BYTES))
    free = bytes_free(path)
    if free < minimum:
        raise HTTPException(503, detail={"reason": "low_disk", "free": free, "min": minimum})
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add helper_service/disk.py helper_service/tests/test_disk.py
git commit -m "feat(helper_service): disk-guard middleware"
```

---

## Task 1.5: Job state model + workdir layout

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/models.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/jobs.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_jobs.py`

- [ ] **Step 1: Write failing tests**

`helper_service/tests/test_jobs.py`:

```python
import pytest
from helper_service.jobs import create_job, load_job, set_status

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

def test_create_job_returns_id_and_creates_workdir():
    jid = create_job()
    assert isinstance(jid, str) and len(jid) >= 8
    job = load_job(jid)
    assert job.status == "queued"
    assert job.workdir.exists()

def test_set_status_persists():
    jid = create_job()
    set_status(jid, "recording")
    assert load_job(jid).status == "recording"
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/models.py`**

```python
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

JobStatus = Literal[
    "queued", "recording", "captioning", "awaiting_review",
    "voice_generating", "muxing", "done", "failed", "voice_failed",
]

class Job(BaseModel):
    job_id: str
    status: JobStatus
    workdir: Path
    created_at: datetime
    error: str | None = None
    estimate_usd: float | None = None
    actual_usd: float | None = None

    class Config:
        arbitrary_types_allowed = True
```

- [ ] **Step 4: Implement `helper_service/jobs.py`**

```python
import json, secrets
from datetime import datetime, timezone
from .paths import JOBS_DIR, job_dir
from .models import Job, JobStatus

def _state_file(jid: str):
    return job_dir(jid) / "state.json"

def create_job() -> str:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    jid = secrets.token_hex(6)  # 12-char hex
    wd = job_dir(jid)
    wd.mkdir()
    job = Job(job_id=jid, status="queued", workdir=wd,
              created_at=datetime.now(timezone.utc))
    _state_file(jid).write_text(job.model_dump_json(indent=2))
    return jid

def load_job(jid: str) -> Job:
    return Job.model_validate_json(_state_file(jid).read_text())

def set_status(jid: str, status: JobStatus, **fields) -> None:
    job = load_job(jid)
    data = job.model_dump()
    data["status"] = status
    data.update(fields)
    _state_file(jid).write_text(Job(**data).model_dump_json(indent=2))
```

- [ ] **Step 5: Run, verify pass**

- [ ] **Step 6: Commit**

```bash
git add helper_service/models.py helper_service/jobs.py helper_service/tests/test_jobs.py
git commit -m "feat(helper_service): job state model + workdir layout"
```

---

## Task 1.6: Project tarball extraction

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/extract.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_extract.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/fixtures/__init__.py` (empty)

- [ ] **Step 1: Write failing test**

`helper_service/tests/test_extract.py`:

```python
import io, tarfile, pytest
from helper_service.extract import extract_project, ExtractError

def make_tar(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, content in files.items():
            ti = tarfile.TarInfo(name); ti.size = len(content)
            tf.addfile(ti, io.BytesIO(content))
    return buf.getvalue()

def test_extracts_files_into_workdir(tmp_path):
    tar = make_tar({"config.py": b"X = 1\n", "scenes/a.py": b"# a\n"})
    extract_project(tar, tmp_path)
    assert (tmp_path / "config.py").read_text() == "X = 1\n"
    assert (tmp_path / "scenes" / "a.py").read_text() == "# a\n"

def test_rejects_path_traversal(tmp_path):
    tar = make_tar({"../escape.py": b"x"})
    with pytest.raises(ExtractError):
        extract_project(tar, tmp_path)

def test_rejects_absolute_paths(tmp_path):
    tar = make_tar({"/etc/passwd": b"x"})
    with pytest.raises(ExtractError):
        extract_project(tar, tmp_path)
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/extract.py`**

```python
import io, tarfile
from pathlib import Path

class ExtractError(Exception):
    pass

def extract_project(tarball: bytes, dest: Path) -> None:
    """Extract a gzipped tarball into dest. Refuses absolute paths and ..-traversal."""
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tf:
        for member in tf.getmembers():
            name = member.name
            if name.startswith("/") or ".." in Path(name).parts:
                raise ExtractError(f"unsafe path in tarball: {name}")
        tf.extractall(dest, filter="data")
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add helper_service/extract.py helper_service/tests/test_extract.py
git commit -m "feat(helper_service): safe tarball extraction"
```

---

## Task 1.7: Pipeline orchestrator (silent phases A–D)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/runner.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_runner.py`

This task wires existing scripts (`assemble_silent.sh`, `burn_captions.sh`, `record_beat.py`) into a sequential orchestrator. Each phase has a clear failure semantic per spec A section 5 ("Failure semantics").

- [ ] **Step 1: Write failing test**

`helper_service/tests/test_runner.py`:

```python
import pytest
from unittest.mock import patch
from helper_service.runner import run_silent_phases

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

@patch("helper_service.runner._run_probes", return_value=None)
@patch("helper_service.runner._record_beats", return_value=None)
@patch("helper_service.runner._concat_silent", return_value=None)
@patch("helper_service.runner._burn_captions", return_value=None)
def test_silent_phases_set_status_to_awaiting_review(probes, rec, concat, burn, tmp_path):
    from helper_service.jobs import create_job, load_job
    jid = create_job()
    run_silent_phases(jid, beats=[{"name": "intro", "voiceover": "hi"}])
    assert load_job(jid).status == "awaiting_review"
    assert load_job(jid).estimate_usd is not None
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/runner.py`**

```python
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
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add helper_service/runner.py helper_service/tests/test_runner.py
git commit -m "feat(helper_service): pipeline orchestrator (silent + voice phases)"
```

---

## Task 1.8: Samples support (`save_as_sample` + `GET /helper/samples`)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/samples.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_samples.py`

- [ ] **Step 1: Write failing tests**

`helper_service/tests/test_samples.py`:

```python
import pytest, json
from helper_service.samples import save_sample, list_samples
from helper_service.paths import SAMPLES_DIR

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))

def test_save_sample_writes_manifest_and_copies_final(tmp_path):
    workdir = tmp_path / "workdir"; workdir.mkdir()
    (workdir / "final.mp4").write_bytes(b"fake-mp4")
    save_sample("job123", workdir, goal="demo X", target_url="https://x.example",
                beats_summary=["intro", "x"])
    assert (SAMPLES_DIR / "job123" / "final.mp4").read_bytes() == b"fake-mp4"
    manifest = json.loads((SAMPLES_DIR / "job123" / "manifest.json").read_text())
    assert manifest["goal"] == "demo X"

def test_list_samples_returns_each_manifest():
    save_sample("a", _make_workdir(b"a"), goal="A", target_url="u", beats_summary=[])
    save_sample("b", _make_workdir(b"b"), goal="B", target_url="u", beats_summary=[])
    out = list_samples()
    assert {s["job_id"] for s in out} == {"a", "b"}

def _make_workdir(content):
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "final.mp4").write_bytes(content)
    return d
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/samples.py`**

```python
import json, shutil
from datetime import datetime, timezone
from pathlib import Path
from .paths import SAMPLES_DIR, sample_dir

def save_sample(job_id: str, workdir: Path, goal: str,
                target_url: str, beats_summary: list[str]) -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    sd = sample_dir(job_id); sd.mkdir(exist_ok=True)
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
    if not SAMPLES_DIR.exists():
        return []
    out = []
    for d in sorted(SAMPLES_DIR.iterdir()):
        m = d / "manifest.json"
        if m.exists():
            out.append(json.loads(m.read_text()))
    return out
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add helper_service/samples.py helper_service/tests/test_samples.py
git commit -m "feat(helper_service): save_sample + list_samples"
```

---

## Task 1.9: FastAPI app (all endpoints)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/api.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_api.py`

This task wires everything from tasks 1.2–1.8 into FastAPI routes per spec A section 1 (revised).

- [ ] **Step 1: Write failing test (smoke test for each endpoint)**

`helper_service/tests/test_api.py`:

```python
import pytest, io, tarfile, json
from fastapi.testclient import TestClient
from helper_service.api import app

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HELPER_AUTH_KEY", "test-key")
    monkeypatch.setenv("DAILY_BUDGET_USD", "5.0")

@pytest.fixture
def client(): return TestClient(app)

@pytest.fixture
def auth(): return {"X-Helper-Key": "test-key"}

def test_health_returns_ok_status(client, auth):
    r = client.get("/helper/health", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "daily_budget_remaining_usd" in body

def test_skill_returns_markdown(client, auth, tmp_path, monkeypatch):
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text("# Test SKILL\n")
    monkeypatch.setenv("HELPER_SKILL_PATH", str(skill_path))
    r = client.get("/helper/skill", headers=auth)
    assert r.status_code == 200
    assert "Test SKILL" in r.text

def test_samples_returns_empty_list_initially(client):
    # public endpoint, no auth header
    r = client.get("/helper/samples")
    assert r.status_code == 200
    assert r.json() == []

def test_post_jobs_requires_auth(client):
    r = client.post("/helper/jobs", files={"project": ("p.tar.gz", b"x")})
    assert r.status_code == 401
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/api.py`**

```python
import os, json
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

app = FastAPI(title="Sri Studio Helper Service", version="0.1.0")

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
```

- [ ] **Step 4: Run, verify pass**

```bash
.venv-service/bin/pytest helper_service/tests/test_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add helper_service/api.py helper_service/tests/test_api.py
git commit -m "feat(helper_service): FastAPI app wires all endpoints"
```

---

## Task 1.10: TTL cleanup background task

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/cleanup.py`
- Modify: `D:/Python Applications/Sri Studio Helper/helper_service/api.py` (start cleanup task on startup)
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_cleanup.py`

- [ ] **Step 1: Write failing test**

`helper_service/tests/test_cleanup.py`:

```python
import time, pytest
from helper_service.cleanup import sweep_expired
from helper_service.paths import JOBS_DIR

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JOB_TTL_DAYS", "0")  # immediate expiry

def test_sweep_deletes_expired_jobs(tmp_path):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    old = JOBS_DIR / "old"; old.mkdir()
    (old / "x").write_text("x")
    sweep_expired()
    assert not old.exists()
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `helper_service/cleanup.py`**

```python
import asyncio, os, shutil, time
from pathlib import Path
from .paths import JOBS_DIR

async def cleanup_loop(interval_s: int = 3600):
    while True:
        try:
            sweep_expired()
        except Exception as e:
            print(f"[cleanup] error: {e}")
        await asyncio.sleep(interval_s)

def sweep_expired() -> None:
    if not JOBS_DIR.exists(): return
    ttl_days = float(os.environ.get("JOB_TTL_DAYS", "7"))
    cutoff = time.time() - ttl_days * 86400
    for d in JOBS_DIR.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
```

- [ ] **Step 4: Wire into FastAPI startup**

In `helper_service/api.py`, add at the top (after `app = FastAPI(...)`):

```python
import asyncio
from .cleanup import cleanup_loop

@app.on_event("startup")
async def _start_cleanup():
    asyncio.create_task(cleanup_loop())
```

- [ ] **Step 5: Run, verify pass**

- [ ] **Step 6: Commit**

```bash
git add helper_service/cleanup.py helper_service/api.py helper_service/tests/test_cleanup.py
git commit -m "feat(helper_service): TTL cleanup background sweep"
```

---

## Task 1.11: Dockerfile for the service

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/Dockerfile`

- [ ] **Step 1: Write the Dockerfile**

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Existing deps from sri_studio_helper/Dockerfile
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
      ffmpeg fonts-ibm-plex \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --quiet uv

# NEW: service deps via uv (per project rule)
RUN uv pip install --system --no-cache \
      fastapi "uvicorn[standard]" python-multipart aiofiles httpx pydantic

# Ship the existing CLI package + the new service package
COPY sri_studio_helper/ /app/sri_studio_helper/
COPY helper_service/    /app/helper_service/
COPY SKILL.md           /app/SKILL.md

RUN mkdir -p /data/jobs /data/samples

WORKDIR /app
ENV HELPER_SKILL_PATH=/app/SKILL.md
EXPOSE 8000
CMD ["python", "-m", "helper_service"]
```

- [ ] **Step 2: Probe build (per CLAUDE.md fail-fast for committed Dockerfiles)**

Run from `D:/Python Applications/Sri Studio Helper/`:

```bash
docker build -f helper_service/Dockerfile -t sri-studio-helper:dev .
docker run --rm sri-studio-helper:dev python -c "from helper_service.api import app; print('app ok')"
```

Expected: `app ok` printed.

- [ ] **Step 3: Commit**

```bash
git add helper_service/Dockerfile
git commit -m "feat(helper_service): Dockerfile bundles FastAPI + sri_studio_helper + SKILL.md"
```

---

## Task 1.12: docker-compose + nginx snippet

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/docker-compose.yml`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/nginx-helper.conf`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/.env.example`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  helper:
    build:
      context: ..
      dockerfile: helper_service/Dockerfile
    image: sri-studio-helper:latest
    restart: unless-stopped
    ports: ["127.0.0.1:8001:8000"]
    volumes:
      - ./data:/data
    environment:
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - HELPER_AUTH_KEY=${HELPER_AUTH_KEY}
      - DAILY_BUDGET_USD=${DAILY_BUDGET_USD:-5}
      - JOB_TTL_DAYS=${JOB_TTL_DAYS:-7}
      - ELEVENLABS_USD_PER_CHAR=${ELEVENLABS_USD_PER_CHAR:-0.00044}
      - HELPER_SKILL_PATH=/app/SKILL.md
      - HELPER_DATA_DIR=/data
    deploy:
      resources:
        limits: { cpus: "2", memory: "3G" }
```

- [ ] **Step 2: Write `nginx-helper.conf`**

```nginx
# Append to /etc/nginx/sites-available/studio.sshub.dev inside the existing
# server block. Routes /helper/* to the helper container on 127.0.0.1:8001.

location /helper/ {
    proxy_pass         http://127.0.0.1:8001;
    proxy_http_version 1.1;
    proxy_request_buffering off;
    client_max_body_size 50m;
    proxy_read_timeout 600s;
    proxy_set_header   Host $host;
    proxy_set_header   X-Real-IP $remote_addr;
    proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
}
```

- [ ] **Step 3: Write `.env.example`**

```
ELEVENLABS_API_KEY=
HELPER_AUTH_KEY=
DAILY_BUDGET_USD=5
JOB_TTL_DAYS=7
ELEVENLABS_USD_PER_CHAR=0.00044
```

- [ ] **Step 4: Probe compose validity**

```bash
cd helper_service && docker compose config > /dev/null && echo "compose ok"
```

Expected: `compose ok`

- [ ] **Step 5: Commit**

```bash
git add helper_service/docker-compose.yml helper_service/nginx-helper.conf helper_service/.env.example
git commit -m "feat(helper_service): docker-compose + nginx snippet for VPS deploy"
```

---

## Task 1.13: Integration test (tiny end-to-end project)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/fixtures/tiny_demo/config.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/fixtures/tiny_demo/captions.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/fixtures/tiny_demo/scenes/intro.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/fixtures/tiny_demo/probes/check.py`
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/tests/test_integration.py`

- [ ] **Step 1: Write the tiny project fixture**

`fixtures/tiny_demo/config.py`:
```python
SITE_URL = "about:blank"
DURATIONS = {"intro": 2}
```

`fixtures/tiny_demo/captions.py`:
```python
BEATS = [
    {"name": "intro", "start_s": 0, "duration_s": 2, "voiceover": "Hello world."},
]
```

`fixtures/tiny_demo/scenes/intro.py`:
```python
async def record(page):
    await page.goto("about:blank")
    await page.wait_for_timeout(2000)
```

`fixtures/tiny_demo/probes/check.py`:
```python
print("probe ok")
```

- [ ] **Step 2: Write integration test**

`helper_service/tests/test_integration.py`:

```python
import io, tarfile, pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from helper_service.api import app

FIX = Path(__file__).parent / "fixtures" / "tiny_demo"

def make_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(FIX, arcname=".")
    return buf.getvalue()

@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("HELPER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HELPER_AUTH_KEY", "k")
    monkeypatch.setenv("DAILY_BUDGET_USD", "5")

@patch("helper_service.runner._run_probes")
@patch("helper_service.runner._record_beats")
@patch("helper_service.runner._concat_silent")
@patch("helper_service.runner._burn_captions")
@patch("helper_service.runner._generate_voice", return_value=0.0044)
@patch("helper_service.runner._final_mux")
def test_happy_path_silent_then_voice(mux, voice, burn, concat, rec, probes):
    client = TestClient(app)
    auth = {"X-Helper-Key": "k"}
    r = client.post("/helper/jobs", files={"project": ("p.tar.gz", make_tar())},
                    headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "awaiting_review"
    assert "estimate_usd" in body
    jid = body["job_id"]

    r2 = client.post(f"/helper/jobs/{jid}/voice", headers=auth)
    assert r2.status_code == 200
    assert r2.json()["status"] == "done"
```

- [ ] **Step 3: Run, verify pass**

```bash
.venv-service/bin/pytest helper_service/tests/test_integration.py -v
```

- [ ] **Step 4: Commit**

```bash
git add helper_service/tests/fixtures/ helper_service/tests/test_integration.py
git commit -m "test(helper_service): tiny end-to-end project fixture + integration test"
```

---

## Task 1.14: Deploy to VPS

This is a one-shot operational task; tests are in `Task 1.13`. Execution requires SSH access to the Hetzner VPS (the user has it; an executing agent does not).

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/helper_service/deploy.md`

- [ ] **Step 1: Write the runbook**

`helper_service/deploy.md`:

````markdown
# Deploying the Helper service to the Hetzner VPS

Prerequisites: SSH access to the studio.sshub.dev VPS as user `sri`. The studio.sshub.dev nginx + Sri Studio app are already deployed (see studio repo's deploy notes).

```bash
# 1. From local repo, build and save the image as a tarball
cd "D:/Python Applications/Sri Studio Helper"
docker build -f helper_service/Dockerfile -t sri-studio-helper:latest .
docker save sri-studio-helper:latest | gzip > /tmp/helper-image.tar.gz

# 2. Copy artifacts to VPS
scp /tmp/helper-image.tar.gz sri@studio.sshub.dev:/tmp/
scp helper_service/docker-compose.yml sri@studio.sshub.dev:/srv/helper/
scp helper_service/.env.example       sri@studio.sshub.dev:/srv/helper/

# 3. SSH in and finish setup
ssh sri@studio.sshub.dev
sudo mkdir -p /srv/helper && sudo chown sri /srv/helper
cd /srv/helper
docker load < /tmp/helper-image.tar.gz
cp .env.example .env
# Edit .env: set ELEVENLABS_API_KEY (from 1Password) and HELPER_AUTH_KEY (random hex; save in 1Password)
nano .env
docker compose up -d
docker compose logs --tail=20

# 4. Wire nginx
sudo cat helper_service/nginx-helper.conf  # paste into /etc/nginx/sites-available/studio.sshub.dev inside the existing server block
sudo nginx -t && sudo systemctl reload nginx

# 5. Smoke test from VPS
curl -H "X-Helper-Key: $(grep HELPER_AUTH_KEY /srv/helper/.env | cut -d= -f2)" \
  http://127.0.0.1:8001/helper/health

# 6. Smoke test from external
curl -H "X-Helper-Key: ..." https://studio.sshub.dev/helper/health
```
````

- [ ] **Step 2: Commit**

```bash
git add helper_service/deploy.md
git commit -m "docs(helper_service): VPS deploy runbook"
```

- [ ] **Step 3: User executes the runbook (manual gate; not subagent-executable)**

This task is COMPLETE only when the user has run the deploy steps and `curl https://studio.sshub.dev/helper/health` returns `{"ok": true, ...}` from outside the VPS.

---

# Phase 2 : MCP wrapper (sub-project B)

## Task 2.1: Scaffold mcp_server package

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/__init__.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/__main__.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/config.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/pyproject.toml`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/__init__.py`

- [ ] **Step 1: Create `mcp_server/__init__.py`**

```python
"""Local-stdio MCP server wrapping the Sri Studio Helper HTTP API."""
__version__ = "0.1.0"
```

- [ ] **Step 2: Create `mcp_server/config.py`**

```python
"""Env config for the MCP server. Exits 1 with stderr message if missing."""
import os, sys

def _required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"[mcp_server] missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return v

def base_url() -> str:
    return os.environ.get("HELPER_BASE_URL", "https://studio.sshub.dev").rstrip("/")

def auth_key() -> str:
    return _required("HELPER_AUTH_KEY")
```

- [ ] **Step 3: Create `mcp_server/pyproject.toml`**

```toml
[project]
name = "sri-studio-helper-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
]
```

- [ ] **Step 4: Create `mcp_server/__main__.py`**

```python
import asyncio
from .server import serve

if __name__ == "__main__":
    asyncio.run(serve())
```

- [ ] **Step 5: Probe import**

```bash
cd "D:/Python Applications/Sri Studio Helper"
uv venv .venv-mcp --python 3.11
uv pip install --python .venv-mcp/bin/python -e ./mcp_server[dev]
.venv-mcp/bin/python -c "from mcp_server.config import base_url; print(base_url())"
```

Expected: prints `https://studio.sshub.dev` (default).

- [ ] **Step 6: Commit**

```bash
git add mcp_server/__init__.py mcp_server/__main__.py mcp_server/config.py mcp_server/pyproject.toml mcp_server/tests/__init__.py
git commit -m "feat(mcp_server): scaffold package + env config"
```

---

## Task 2.2: helper_client (httpx wrapper over Helper HTTP API)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/helper_client.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/test_helper_client.py`

- [ ] **Step 1: Write failing tests**

`mcp_server/tests/test_helper_client.py`:

```python
import pytest, respx, httpx
from mcp_server.helper_client import HelperClient

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HELPER_BASE_URL", "http://test.local")
    monkeypatch.setenv("HELPER_AUTH_KEY", "k")
    return HelperClient()

@respx.mock
def test_post_jobs_sends_auth_header(client):
    route = respx.post("http://test.local/helper/jobs").mock(
        return_value=httpx.Response(200, json={"job_id": "abc",
                                                "preview_url": "/p", "estimate_usd": 0.05,
                                                "status": "awaiting_review"}))
    out = client.post_silent(b"fake-tar")
    assert route.called
    assert route.calls[0].request.headers["X-Helper-Key"] == "k"
    assert out["job_id"] == "abc"

@respx.mock
def test_post_voice_returns_final_url(client):
    respx.post("http://test.local/helper/jobs/abc/voice").mock(
        return_value=httpx.Response(200, json={"final_url": "/f", "status": "done"}))
    out = client.post_voice("abc")
    assert out["final_url"] == "/f"

@respx.mock
def test_get_skill_returns_text(client):
    respx.get("http://test.local/helper/skill").mock(
        return_value=httpx.Response(200, text="# SKILL"))
    assert "SKILL" in client.get_skill()

@respx.mock
def test_402_raises_BudgetExceeded(client):
    from mcp_server.helper_client import BudgetExceeded
    respx.post("http://test.local/helper/jobs/abc/voice").mock(
        return_value=httpx.Response(402, json={"detail": {"reason": "would_exceed_daily_cap",
                                                            "remaining": 0.1, "needed": 0.5}}))
    with pytest.raises(BudgetExceeded) as e:
        client.post_voice("abc")
    assert e.value.remaining == 0.1
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `mcp_server/helper_client.py`**

```python
import httpx
from .config import base_url, auth_key

class HelperError(Exception): pass
class BudgetExceeded(HelperError):
    def __init__(self, remaining: float, needed: float):
        self.remaining = remaining; self.needed = needed
        super().__init__(f"would exceed daily cap; need ${needed:.4f}, have ${remaining:.4f}")
class HelperUnreachable(HelperError): pass

class HelperClient:
    def __init__(self):
        self._base = base_url()
        self._headers = {"X-Helper-Key": auth_key()}
        self._client = httpx.Client(timeout=600)

    def post_silent(self, tarball: bytes, auto_approve: bool = False) -> dict:
        try:
            r = self._client.post(
                f"{self._base}/helper/jobs",
                params={"auto_approve": str(auto_approve).lower()},
                files={"project": ("project.tar.gz", tarball, "application/gzip")},
                headers=self._headers,
            )
        except httpx.HTTPError as e:
            raise HelperUnreachable(str(e))
        if r.status_code == 200:
            return r.json()
        raise HelperError(f"helper {r.status_code}: {r.text[:200]}")

    def post_voice(self, job_id: str) -> dict:
        r = self._client.post(f"{self._base}/helper/jobs/{job_id}/voice",
                              headers=self._headers)
        if r.status_code == 402:
            d = r.json()["detail"]
            raise BudgetExceeded(d["remaining"], d["needed"])
        if r.status_code == 200:
            return r.json()
        raise HelperError(f"helper {r.status_code}: {r.text[:200]}")

    def get_skill(self) -> str:
        r = self._client.get(f"{self._base}/helper/skill")
        r.raise_for_status()
        return r.text

    def get_job(self, job_id: str) -> dict:
        r = self._client.get(f"{self._base}/helper/jobs/{job_id}",
                             headers=self._headers)
        r.raise_for_status()
        return r.json()
```

- [ ] **Step 4: Run, verify pass**

- [ ] **Step 5: Commit**

```bash
git add mcp_server/helper_client.py mcp_server/tests/test_helper_client.py
git commit -m "feat(mcp_server): httpx wrapper over Helper HTTP API"
```

---

## Task 2.3: tar_project (tar a local dir into a tempfile, with size guard)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tar_project.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/test_tar.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/fixtures/tiny_project/config.py` (one-line)
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/fixtures/tiny_project/captions.py`

- [ ] **Step 1: Create the fixture**

`mcp_server/tests/fixtures/tiny_project/config.py`:
```python
SITE_URL = "about:blank"
```

`mcp_server/tests/fixtures/tiny_project/captions.py`:
```python
BEATS = [{"name": "intro", "voiceover": "hi"}]
```

- [ ] **Step 2: Write failing tests**

`mcp_server/tests/test_tar.py`:

```python
import io, tarfile, pytest
from pathlib import Path
from mcp_server.tar_project import tar_dir, TooLargeError

FIX = Path(__file__).parent / "fixtures" / "tiny_project"

def test_tar_dir_returns_gzip_bytes():
    out = tar_dir(FIX)
    assert out.startswith(b"\x1f\x8b")  # gzip magic

def test_tar_contains_expected_entries():
    out = tar_dir(FIX)
    with tarfile.open(fileobj=io.BytesIO(out), mode="r:gz") as tf:
        names = {m.name for m in tf.getmembers()}
    assert "config.py" in names
    assert "captions.py" in names

def test_size_guard_refuses_oversize(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * (26 * 1024 * 1024))
    with pytest.raises(TooLargeError):
        tar_dir(tmp_path, max_bytes=25 * 1024 * 1024)
```

- [ ] **Step 3: Run, verify fail**

- [ ] **Step 4: Implement `mcp_server/tar_project.py`**

```python
import io, tarfile
from pathlib import Path

class TooLargeError(Exception):
    def __init__(self, size: int, limit: int):
        self.size = size; self.limit = limit
        super().__init__(f"project is {size} bytes; limit is {limit}")

DEFAULT_MAX_BYTES = 25 * 1024 * 1024  # 25 MB matches nginx upload cap

def tar_dir(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """Tar+gzip a directory tree. Raises TooLargeError if total > max_bytes."""
    total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    if total > max_bytes:
        raise TooLargeError(total, max_bytes)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(path, arcname=".", filter=lambda ti: ti)
    return buf.getvalue()
```

- [ ] **Step 5: Run, verify pass**

- [ ] **Step 6: Commit**

```bash
git add mcp_server/tar_project.py mcp_server/tests/test_tar.py mcp_server/tests/fixtures/
git commit -m "feat(mcp_server): tar a local project dir with size guard"
```

---

## Task 2.4: MCP tools (server registration + four tool functions)

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tools.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/server.py`
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

`mcp_server/tests/test_tools.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_server.tools import (helper_render_silent, helper_render_voice,
                              helper_render_full, helper_skill)

FIX = Path(__file__).parent / "fixtures" / "tiny_project"

@patch("mcp_server.tools.HelperClient")
def test_render_silent_passes_tar_to_client(MockClient, tmp_path):
    inst = MockClient.return_value
    inst.post_silent.return_value = {"job_id": "j", "preview_url": "/p",
                                       "estimate_usd": 0.05, "status": "awaiting_review"}
    out = helper_render_silent({"project_dir": str(FIX)})
    assert out["job_id"] == "j"
    args, kwargs = inst.post_silent.call_args
    assert isinstance(args[0], bytes)

@patch("mcp_server.tools.HelperClient")
def test_render_voice_returns_final_url(MockClient):
    MockClient.return_value.post_voice.return_value = {"final_url": "/f", "status": "done"}
    out = helper_render_voice({"job_id": "abc"})
    assert out == {"final_url": "/f", "status": "done"}

@patch("mcp_server.tools.HelperClient")
def test_skill_returns_markdown(MockClient):
    MockClient.return_value.get_skill.return_value = "# SKILL"
    out = helper_skill({})
    assert "SKILL" in out

def test_render_silent_returns_error_when_dir_missing():
    out = helper_render_silent({"project_dir": "/nonexistent"})
    assert "error" in out and out["error"] == "project_dir_not_found"
```

- [ ] **Step 2: Run, verify fail**

- [ ] **Step 3: Implement `mcp_server/tools.py`**

```python
from pathlib import Path
from .helper_client import HelperClient, BudgetExceeded, HelperUnreachable, HelperError
from .tar_project import tar_dir, TooLargeError

def _err(error: str, **fields) -> dict:
    return {"error": error, **fields}

def helper_render_silent(args: dict) -> dict:
    pd = args.get("project_dir")
    if not pd or not Path(pd).is_dir():
        return _err("project_dir_not_found", path=pd)
    try:
        tar = tar_dir(Path(pd))
    except TooLargeError as e:
        return _err("project_too_large", size_bytes=e.size, limit_bytes=e.limit)
    try:
        return HelperClient().post_silent(tar)
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_render_voice(args: dict) -> dict:
    jid = args.get("job_id")
    if not jid:
        return _err("missing_job_id")
    try:
        return HelperClient().post_voice(jid)
    except BudgetExceeded as e:
        return _err("would_exceed_daily_cap", remaining=e.remaining, needed=e.needed,
                    suggest="shorten beats voiceover, or wait until daily reset")
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_render_full(args: dict) -> dict:
    pd = args.get("project_dir")
    if not pd or not Path(pd).is_dir():
        return _err("project_dir_not_found", path=pd)
    try:
        tar = tar_dir(Path(pd))
    except TooLargeError as e:
        return _err("project_too_large", size_bytes=e.size, limit_bytes=e.limit)
    try:
        return HelperClient().post_silent(tar, auto_approve=True)
    except BudgetExceeded as e:
        return _err("would_exceed_daily_cap", remaining=e.remaining, needed=e.needed)
    except HelperUnreachable as e:
        return _err("helper_unreachable", detail=str(e))
    except HelperError as e:
        return _err("helper_error", detail=str(e))

def helper_skill(args: dict) -> str:
    try:
        return HelperClient().get_skill()
    except HelperError as e:
        return f"# SKILL fetch failed\n\n{e}"
```

- [ ] **Step 4: Implement `mcp_server/server.py`**

```python
"""MCP server registration. Maps four tools to mcp_server.tools."""
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from . import tools

server = Server("sri-studio-helper")

@server.list_tools()
async def _list_tools() -> list[Tool]:
    return [
        Tool(name="helper_render_silent",
             description="Render the silent preview of a Helper screencast. "
                         "Submit a project_dir; returns preview_url + estimate_usd. "
                         "Pause for human review of the preview before calling helper_render_voice.",
             inputSchema={"type": "object",
                          "properties": {"project_dir": {"type": "string"}},
                          "required": ["project_dir"]}),
        Tool(name="helper_render_voice",
             description="Approve a silent preview and render the voiced final. "
                         "Costs ElevenLabs tokens; check estimate_usd from helper_render_silent first.",
             inputSchema={"type": "object",
                          "properties": {"job_id": {"type": "string"}},
                          "required": ["job_id"]}),
        Tool(name="helper_render_full",
             description="Render silent + voice in one call (skips review gate). "
                         "ONLY use when the project is a known-good template; otherwise prefer helper_render_silent.",
             inputSchema={"type": "object",
                          "properties": {"project_dir": {"type": "string"}},
                          "required": ["project_dir"]}),
        Tool(name="helper_skill",
             description="Fetch the Sri Studio Helper SKILL.md (silent-first lessons, beat structure, "
                         "scene authoring, anti-patterns). Call this once at session start to load "
                         "best-practices guidance before constructing a project.",
             inputSchema={"type": "object", "properties": {}}),
    ]

@server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    fn = {
        "helper_render_silent": tools.helper_render_silent,
        "helper_render_voice":  tools.helper_render_voice,
        "helper_render_full":   tools.helper_render_full,
        "helper_skill":         tools.helper_skill,
    }[name]
    result = fn(arguments)
    payload = result if isinstance(result, str) else json.dumps(result)
    return [TextContent(type="text", text=payload)]

async def serve() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())
```

- [ ] **Step 5: Run, verify pass**

```bash
.venv-mcp/bin/pytest mcp_server/tests/ -v
```

- [ ] **Step 6: Smoke probe : server boots and lists tools**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
  HELPER_AUTH_KEY=test .venv-mcp/bin/python -m mcp_server | head -20
```

Expected: JSON-RPC response listing the four tool names.

- [ ] **Step 7: Commit**

```bash
git add mcp_server/tools.py mcp_server/server.py mcp_server/tests/test_tools.py
git commit -m "feat(mcp_server): four tools wired into stdio MCP server"
```

---

## Task 2.5: Claude Code installation snippet

**Files:**
- Create: `D:/Python Applications/Sri Studio Helper/mcp_server/INSTALL.md`

- [ ] **Step 1: Write the install doc**

````markdown
# Installing the Sri Studio Helper MCP server

## In Claude Code

Edit `~/.claude/mcp.json` (or per-project `.claude/mcp.json`):

```json
{
  "mcpServers": {
    "sri-studio-helper": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "D:/Python Applications/Sri Studio Helper",
        "python", "-m", "mcp_server"
      ],
      "env": {
        "HELPER_BASE_URL": "https://studio.sshub.dev",
        "HELPER_AUTH_KEY": "<paste from 1Password>"
      }
    }
  }
}
```

Restart Claude Code. The four tools (`helper_render_silent`, `helper_render_voice`, `helper_render_full`, `helper_skill`) appear in the tool list.

## Local-loopback testing

For testing against a Helper service running on localhost (no VPS required), set `HELPER_BASE_URL` to `http://127.0.0.1:8001`.
````

- [ ] **Step 2: Commit**

```bash
git add mcp_server/INSTALL.md
git commit -m "docs(mcp_server): Claude Code installation snippet"
```

---

# Phase 3 : Extensions Page (sub-project D, in studio repo)

> All file paths in Phase 3 are relative to `D:/Python Applications/studio/`.

## Task 3.1: Enable @next/mdx in Next.js config

**Files:**
- Modify: `frontend/next.config.js`
- Modify: `frontend/package.json`

- [ ] **Step 1: Add MDX deps to package.json**

In `frontend/package.json`, add to `dependencies`:

```json
  "@next/mdx": "^14.2.0",
  "@mdx-js/loader": "^3.0.0",
  "@mdx-js/react": "^3.0.0",
  "@types/mdx": "^2.0.13"
```

- [ ] **Step 2: Update `frontend/next.config.js`**

Wrap the existing config with `withMDX`:

```javascript
const withMDX = require('@next/mdx')();

/** @type {import('next').NextConfig} */
const nextConfig = {
  pageExtensions: ['ts', 'tsx', 'mdx'],
  // ... existing config preserved here
};

module.exports = withMDX(nextConfig);
```

- [ ] **Step 3: Install + verify**

```bash
cd frontend && npm install
npm run build  # should still build without errors
```

Expected: build succeeds; no MDX-related errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/next.config.js
git commit -m "feat(extensions): enable @next/mdx for /extensions page"
```

---

## Task 3.2: Copy canonical sample MP4 + manifest

**Files:**
- Create: `frontend/public/samples/find-evil-canonical.mp4` (binary copy)
- Create: `frontend/app/extensions/_components/canonical-sample.json`

- [ ] **Step 1: Copy the MP4**

```bash
cp "D:/Python Applications/Find Evil - Hackathon/out/Demo_Video.mp4" \
   "D:/Python Applications/studio/frontend/public/samples/find-evil-canonical.mp4"
```

Verify size:
```bash
ls -la "D:/Python Applications/studio/frontend/public/samples/find-evil-canonical.mp4"
```

If > 25 MB, instead host on the VPS at `/srv/static/` and reference by URL; do NOT commit it to the repo.

- [ ] **Step 2: Create the manifest**

`frontend/app/extensions/_components/canonical-sample.json`:

```json
{
  "job_id": "find-evil-canonical",
  "generated_at": "2026-05-09T00:00:00Z",
  "goal": "Walkthrough of the SANS Find Evil hackathon submission",
  "target_url": "https://findevil.sshub.dev",
  "final_url": "/samples/find-evil-canonical.mp4",
  "is_highlight": true,
  "highlight_caption": "This video was generated by the Helper, end-to-end. No editor, no voice actor."
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/public/samples/find-evil-canonical.mp4 frontend/app/extensions/_components/canonical-sample.json
git commit -m "feat(extensions): pin canonical Find Evil demo video as v1 highlight"
```

---

## Task 3.3: SampleGrid component (live + fallback)

**Files:**
- Create: `frontend/app/extensions/_components/SampleGrid.tsx`

- [ ] **Step 1: Implement `SampleGrid.tsx`**

```tsx
import canonical from './canonical-sample.json';

type Sample = {
  job_id: string;
  generated_at: string;
  goal: string;
  target_url: string;
  final_url: string;
  is_highlight?: boolean;
  highlight_caption?: string;
};

async function fetchLiveSamples(): Promise<Sample[]> {
  const base = process.env.HELPER_BASE_URL ?? 'https://studio.sshub.dev';
  try {
    const r = await fetch(`${base}/helper/samples`, { next: { revalidate: 60 } });
    if (!r.ok) return [];
    return (await r.json()) as Sample[];
  } catch {
    return [];
  }
}

export default async function SampleGrid() {
  const live = await fetchLiveSamples();
  const all: Sample[] = [canonical as Sample, ...live.filter(s => s.job_id !== canonical.job_id)];
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {all.map(s => (
        <figure key={s.job_id} className="rounded-lg border border-neutral-800 p-4">
          <video controls preload="metadata" className="w-full rounded">
            <source src={s.final_url} type="video/mp4" />
          </video>
          <figcaption className="mt-2 text-sm text-neutral-300">
            {s.is_highlight ? <strong>{s.highlight_caption}</strong> : s.goal}
            <div className="text-xs text-neutral-500 mt-1">{s.target_url}</div>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Build, verify no TS errors**

```bash
cd frontend && npm run typecheck
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/extensions/_components/SampleGrid.tsx
git commit -m "feat(extensions): SampleGrid server component (canonical + live fetch)"
```

---

## Task 3.4: The `/extensions` MDX page

**Files:**
- Create: `frontend/app/extensions/page.mdx`

- [ ] **Step 1: Write the MDX page**

`frontend/app/extensions/page.mdx`:

```mdx
import SampleGrid from './_components/SampleGrid';

# Extensions

**Demo videos as code. Configurable, repeatable, cheap to re-cut.**

---

## 1. The assignment

[Replace this paragraph with the take-home prompt and constraints. Keep it factual: what was asked, what existed before, what the deliverable was supposed to be. 100 to 200 words.]

## 2. What I built (Sri Studio)

Sri Studio is the baseline app: a text brief becomes a vertical short-form video. Claude Haiku extracts intent, Claude Sonnet drafts a script plan, the user approves in the browser before any paid call fires. On approve, Flux Schnell renders 9:16 scenes, ElevenLabs produces voice-cloned narration with alignment-driven captions, ffmpeg stitches a 1080x1920 MP4. LangGraph orchestrates, Langfuse traces, a daily cost cap is the hard wall. (See [the homepage](/) for live runs.)

## 3. What I extended on my own

**Source:** a project tarball.
**Output:** a finished video.
**Cost:** $0.05.
**Re-runs:** free until the voice phase.

Three extensions, in the order I built them:

- **Sri Studio Helper.** A silent-first screencast pipeline. Records browser scenes via Playwright, burns captions in BEFORE generating voice, and only fires the expensive ElevenLabs call after a human-reviewed silent cut. Re-cuts are cheap; voice tokens are not.
- **Helper as a Service.** The pipeline above, fronted by an HTTP API on `studio.sshub.dev/helper/`. One POST submits a project, returns a silent preview + a cost estimate; one POST approves and renders the final.
- **MCP wrapper.** A local stdio MCP server that maps four tools to the HTTP API, so an LLM agent (Claude Code) can call the pipeline directly without curl.

The video below was generated by the Helper, end to end. No editor, no voice actor.

<SampleGrid />

## 4. Critique / what I'd do differently

[Replace this paragraph with your honest reflection on the design. What constraint forced an awkward choice? What would you change with a clean slate? Confident voice, not undermining. 150 to 300 words.]

## 5. Tech notes

- Helper service spec: [`docs/superpowers/specs/2026-05-10-helper-as-a-service-design.md`](https://github.com/charanbobby/sri-studio-helper/blob/master/docs/superpowers/specs/2026-05-10-helper-as-a-service-design.md)
- MCP wrapper spec: [`docs/superpowers/specs/2026-05-10-mcp-wrapper-design.md`](https://github.com/charanbobby/sri-studio-helper/blob/master/docs/superpowers/specs/2026-05-10-mcp-wrapper-design.md)
- Extensions page spec (this page): [`docs/superpowers/specs/2026-05-10-extensions-page-design.md`](https://github.com/charanbobby/studio/blob/main/docs/superpowers/specs/2026-05-10-extensions-page-design.md)
- Helper repo: [github.com/charanbobby/sri-studio-helper](https://github.com/charanbobby/sri-studio-helper)
- Studio repo: [github.com/charanbobby/studio](https://github.com/charanbobby/studio)
```

- [ ] **Step 2: Build, verify the page compiles**

```bash
cd frontend && npm run build
```

Expected: `/extensions` route appears in the build output.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/extensions/page.mdx
git commit -m "feat(extensions): MDX page with chronological six-section structure"
```

---

## Task 3.5: Add Extensions tile to FeaturedRuns

**Files:**
- Modify: `frontend/components/FeaturedRuns.tsx`

- [ ] **Step 1: Read the current file**

```bash
cat frontend/components/FeaturedRuns.tsx | head -80
```

Locate the `<div className="grid ...">` (or equivalent) where `FeaturedTile`s are rendered.

- [ ] **Step 2: Append the Extensions tile**

After the last live `<FeaturedTile />` in the grid (and BEFORE the closing `</div>` of the grid), insert:

```tsx
import Link from "next/link";

// ... inside the grid, after the last live tile:
<Link href="/extensions" className="block">
  <div className="rounded-lg border border-neutral-800 p-4 hover:border-neutral-600 transition">
    <div className="text-xs uppercase tracking-wide text-neutral-500">Extensions</div>
    <div className="mt-2 text-lg font-semibold">The extension story</div>
    <div className="mt-1 text-sm text-neutral-400">Helper API, MCP, sample videos</div>
    <div className="mt-4 text-xs text-neutral-500">Read &rarr;</div>
  </div>
</Link>
```

(Adapt class names to match the rest of the file's Tailwind conventions; the above is the structural target.)

- [ ] **Step 3: Build, verify the tile appears**

```bash
cd frontend && npm run build && npm run dev
```

Open `http://localhost:3000`. Verify the Extensions tile appears in the FeaturedRuns row. Click it; verify navigation to `/extensions`.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/FeaturedRuns.tsx
git commit -m "feat(extensions): tile in FeaturedRuns links to /extensions"
```

---

## Task 3.6: Playwright e2e test for the extensions page

**Files:**
- Create: `playwright/e2e/extensions-page.spec.ts` (path may vary; check existing studio Playwright setup)

- [ ] **Step 1: Identify the existing Playwright config**

```bash
find . -name "playwright.config.*" -not -path "*/node_modules/*"
```

If the studio repo has no Playwright setup yet, this task creates a minimal one alongside the test. If it does, this task adds one spec file there.

- [ ] **Step 2: Write the spec**

`playwright/e2e/extensions-page.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

const BASE = process.env.STUDIO_BASE_URL ?? 'http://localhost:3000';

test('Extensions tile on home page navigates to /extensions', async ({ page }) => {
  await page.goto(BASE);
  const tile = page.getByRole('link', { name: /the extension story/i });
  await expect(tile).toBeVisible();
  await tile.click();
  await expect(page).toHaveURL(/\/extensions$/);
});

test('/extensions page has all six sections', async ({ page }) => {
  await page.goto(`${BASE}/extensions`);
  await expect(page.getByRole('heading', { name: 'Extensions' })).toBeVisible();
  await expect(page.getByRole('heading', { name: /the assignment/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /what i built/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /what i extended/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /critique/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /tech notes/i })).toBeVisible();
});

test('canonical sample video is rendered on /extensions', async ({ page }) => {
  await page.goto(`${BASE}/extensions`);
  const video = page.locator('video').first();
  await expect(video).toBeVisible();
  const src = await video.locator('source').getAttribute('src');
  expect(src).toMatch(/find-evil-canonical\.mp4$/);
});
```

- [ ] **Step 3: Run the tests against `npm run dev`**

```bash
cd frontend && npm run dev &
npx playwright test playwright/e2e/extensions-page.spec.ts
```

Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add playwright/e2e/extensions-page.spec.ts
git commit -m "test(extensions): playwright e2e for tile + sections + canonical sample"
```

---

## Task 3.7: Deploy studio with the extensions page

**Files:**
- (None new; this is a deploy operation.)

- [ ] **Step 1: Build and deploy via the existing studio deploy mechanism**

The studio repo already has a `deploy/` directory with a tar-over-ssh script (per its README). Run that script as you normally would for a studio change.

```bash
cd "D:/Python Applications/studio"
# Whatever the existing deploy command is (e.g. ./deploy/deploy.sh)
./deploy/deploy.sh
```

- [ ] **Step 2: Smoke test from outside**

```bash
curl -I https://studio.sshub.dev/extensions
# Expected: 200 OK
```

Open `https://studio.sshub.dev/` in a browser, click the Extensions tile, scroll the page, click play on the canonical sample video.

- [ ] **Step 3: User executes (manual gate; not subagent-executable)**

This task is COMPLETE only when `https://studio.sshub.dev/extensions` is live and the canonical video plays.

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by task |
|---|---|
| A.1 API surface (POST /jobs, POST /voice, GET /jobs/:id, GET /log, GET /skill, GET /samples, DELETE) | 1.9, 1.8 |
| A.2 Data flow (sequence + workdir + concurrency + failure semantics + cost guard) | 1.5, 1.7, 1.3, 1.9 |
| A.3 Container architecture | 1.11, 1.12 |
| A.4 Routing + auth | 1.2, 1.12 |
| A.5 Cost discipline + persistence (PRE/POST log lines, daily cap, TTL) | 1.3, 1.7 (PRE/POST), 1.10 |
| A.6 Testing + verification | 1.13 (integration), unit tests in 1.2-1.10 |
| A spec-A addendum (`/helper/samples` public, no auth) | 1.8, 1.9 (public route) |
| B.tools (4 MCP tools mapped to HTTP) | 2.4 |
| B.tar handling | 2.3 |
| B.config (env vars) | 2.1 |
| B.failure modes (structured errors) | 2.4 (per-tool error wrapping) |
| B.testing (mocked httpx, fixture project) | 2.2, 2.3, 2.4 |
| B.distribution (Claude Code MCP snippet) | 2.5 |
| D.discovery (FeaturedRuns tile) | 3.5 |
| D.URL (/extensions Next.js route) | 3.4 |
| D.sections (six sections in MDX) | 3.4 |
| D.MDX setup | 3.1 |
| D.SampleGrid (live + fallback) | 3.3 |
| D.canonical sample bridge | 3.2 |
| D.tests | 3.6 |
| D.visual style (matches existing Tailwind) | 3.3, 3.5 (uses existing class vocabulary) |
| D.deploy | 3.7 |
| Spec D's spec-A addendum (samples endpoint public) | 1.8, 1.9 |

No gaps detected.

**Placeholder scan:**
- Task 3.4 has `[Replace this paragraph with ...]` for the Assignment and Critique sections. **Intentional**: these are editorial sections the user must write; the plan cannot fabricate the content. Flagged as user-fill-in, not as plan-time TODO.
- Task 3.5 says "Adapt class names to match the rest of the file's Tailwind conventions". **Acceptable**: the existing file's exact class names cannot be predicted at plan-time without re-reading the file at task time, which is the intent.
- Task 3.7 references "the existing deploy mechanism (e.g. `./deploy/deploy.sh`)". **Acceptable**: the exact deploy command lives in the studio repo's `deploy/` and is not in scope for this plan to redefine.

**Type / API consistency:**
- `JobStatus` literals match across `models.py`, `jobs.py`, `runner.py`, `api.py` (all use the same set: queued, recording, captioning, awaiting_review, voice_generating, muxing, done, failed, voice_failed).
- `BEATS` shape (`{name, voiceover, ...}`) consistent between `_load_beats` (1.9) and `estimate` (1.3) and `gate_voice` (1.3) and `_generate_voice` (1.7).
- `Sample` shape consistent between Helper's `samples.py` (1.8) and SampleGrid's TypeScript interface (3.3).
- HTTP endpoint URLs match between `helper_service/api.py` (1.9) and `mcp_server/helper_client.py` (2.2).

No inconsistencies found.

---

## Execution Handoff

**Plan complete and saved to `D:/Python Applications/Sri Studio Helper/docs/superpowers/plans/2026-05-10-helper-service-mcp-extensions-page.md`. Two execution options:**

1. **Subagent-Driven (recommended)** : dispatch a fresh subagent per task; review between tasks; fast iteration. Best for this plan because tasks 1.1-1.10 and 2.1-2.5 are fully subagent-executable, while 1.14, 3.7 are manual gates.
2. **Inline Execution** : execute tasks in the current session using executing-plans; batch with checkpoints.

**Which approach?**
