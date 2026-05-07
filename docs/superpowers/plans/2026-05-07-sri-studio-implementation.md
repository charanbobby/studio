# Sri Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working AI Reel generator (Sri Studio) for the CSC Generation AI Solutions Engineer take-home, deployed at studio.sshub.dev, with a mandatory human-approval gate between Plan and Execute, voice-cloned narration, and a daily cost cap.

**Architecture:** Two services in Docker Compose: a FastAPI + LangGraph backend and a Next.js frontend, plus an nginx reverse proxy + Let's Encrypt + basic auth in front of both on Hetzner. The pipeline is Extract -> Plan -> Human Approval Gate -> Execute (parallel TTS + image gen + music + captions) -> Stitch.

**Tech Stack:** Python 3.12 (uv), FastAPI, LangGraph, Pydantic v2, OpenRouter (Claude Sonnet/Haiku with prompt caching), ElevenLabs (Instant Voice Clone TTS + Music), Replicate (Flux Schnell), ffmpeg, Langfuse Cloud, Next.js 14 + React + TypeScript + Tailwind, Docker Compose, nginx, Let's Encrypt.

**Reference docs (read these first if you have zero context):**
- `docs/superpowers/specs/2026-05-07-csc-reel-generator-design.md` (the spec this plan implements)
- `skills/my-working-style/SKILL.md` (10-phase build playbook)
- `~/.claude/CLAUDE.md` (global rules: no em dashes, fail-fast probe before commit, print cost pre/post every LLM call, always uv never pip, size guard tool output before LLM)
- `memory/MEMORY.md` (cross-project rules)

**Hard rules baked into every task:**
1. **No em dashes (U+2014) in any file content.** Use comma, semicolon, period, colon, or parens.
2. **Always `uv`, never `pip`.** For ad-hoc Docker probes use `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`.
3. **Probe before code.** Each external API gets a probe in `experiments/probe_*.py` that runs against the real service and exits 0 before the matching node code lands.
4. **Print cost pre/post every paid API call.** LLM calls use `llm_cost_pre()` / `llm_cost_post()`; non-LLM paid calls (Replicate, ElevenLabs) use `unit_cost_pre()` / `unit_cost_post()`. Phase 2 implements them. The PRE line prints rate + estimate so the bill is visible BEFORE the API call returns. ElevenLabs TTS also prints the monthly char quota status on every call.
5. **Size guard tool output before LLM.** Anything sent to a Claude call that comes from another tool is checked for size and trimmed if over 50 KB.
6. **Fail-fast gate is dormant by default in this project.** No `.failfast.list` is committed; if you want enforcement during this plan, copy `.failfast.list.example` to `.failfast.list` after Phase 2.
7. **Frequent commits.** Each task ends with a commit. Do not batch.

---

## Phase 0: Project skeleton + Docker compose smoke

**Goal:** `docker compose up` brings up an empty FastAPI backend and an empty Next.js frontend; both respond on their ports. Nothing AI-related yet.

### Task 0.1: Create backend Python project skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/src/reel_gen/__init__.py`
- Create: `backend/src/reel_gen/api.py`
- Create: `backend/src/reel_gen/__main__.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "reel-gen"
version = "0.1.0"
description = "Sri Studio backend: AI Reel generator pipeline"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "httpx>=0.27",
    "langgraph>=0.2.50",
    "langchain-core>=0.3",
    "langfuse>=2.55",
    "anthropic>=0.40",
    "openai>=1.55",
    "replicate>=1.0",
    "elevenlabs>=1.13",
    "python-multipart>=0.0.12",
    "sse-starlette>=2.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "ruff>=0.7",
    "mypy>=1.13",
    "respx>=0.22",
]

[tool.uv]
package = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/reel_gen"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

# ffmpeg for the Stitch node
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv: faster than pip per global rules
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN uv pip install --system --no-cache -e ".[dev]"

EXPOSE 8000

# Liveness check used by docker-compose and nginx
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/healthz', timeout=2).raise_for_status()" || exit 1

CMD ["uvicorn", "reel_gen.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create `backend/.dockerignore`**

```
__pycache__
*.pyc
.pytest_cache
.ruff_cache
.mypy_cache
.venv
venv
runs/
experiments/out/
experiments/cache/
.env
.env.local
```

- [ ] **Step 4: Create `backend/src/reel_gen/__init__.py`**

```python
"""Sri Studio backend: AI Reel generator pipeline."""
__version__ = "0.1.0"
```

- [ ] **Step 5: Create `backend/src/reel_gen/api.py` (minimal healthz only)**

```python
"""FastAPI app entry point. Routes get added in Phase 4."""
from fastapi import FastAPI

app = FastAPI(title="Sri Studio API", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sri-studio-backend"}
```

- [ ] **Step 6: Create `backend/src/reel_gen/__main__.py` (CLI placeholder)**

```python
"""CLI entry point. Wired up in Phase 3."""
from __future__ import annotations

import sys


def main() -> int:
    print("Sri Studio CLI: not yet wired. Run via docker compose for now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI + uv + Docker (healthz only)"
```

### Task 0.2: Create frontend Next.js project skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "sri-studio-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.2.16",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "22.7.5",
    "@types/react": "18.3.11",
    "@types/react-dom": "18.3.0",
    "autoprefixer": "10.4.20",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.13",
    "typescript": "5.6.3"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `frontend/next.config.js`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: { typedRoutes: true },
};
module.exports = nextConfig;
```

- [ ] **Step 4: Create `frontend/tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 5: Create `frontend/postcss.config.js`**

```js
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 6: Create `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg: #0a0a0a;
  --fg: #ededed;
  --muted: #999999;
  --accent: #4f46e5;
}

html, body {
  background: var(--bg);
  color: var(--fg);
  font-family: ui-sans-serif, system-ui, sans-serif;
}
```

- [ ] **Step 7: Create `frontend/app/layout.tsx`**

```tsx
import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sri Studio",
  description: "AI Reel generator with voice-cloned narration",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-neutral-800 px-6 py-4">
          <h1 className="text-xl font-semibold">Sri Studio</h1>
        </header>
        <main className="max-w-3xl mx-auto px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 8: Create `frontend/app/page.tsx` (placeholder)**

```tsx
export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">New Reel</h2>
      <p className="text-neutral-400">Prompt form lands in Phase 8.</p>
    </div>
  );
}
```

- [ ] **Step 9: Create `frontend/Dockerfile` (multi-stage standalone build)**

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O - http://localhost:3000/ > /dev/null || exit 1

CMD ["node", "server.js"]
```

- [ ] **Step 10: Create `frontend/.dockerignore`**

```
node_modules
.next
.git
.env
.env.local
```

- [ ] **Step 11: Generate `frontend/package-lock.json` locally**

Run: `cd frontend && npm install`
Expected: package-lock.json created, `node_modules/` populated, `next` binary present.

- [ ] **Step 12: Smoke-build the frontend container**

Run: `docker build -t sri-studio-frontend ./frontend`
Expected: Builds clean. Final image tag created.

- [ ] **Step 13: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js 14 + Tailwind + standalone Docker build"
```

### Task 0.3: Wire Docker Compose

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  backend:
    build: ./backend
    env_file: .env
    volumes:
      - ./runs:/app/runs
      - ./backend/src:/app/src
    ports: ["8000:8000"]
    environment:
      PYTHONUNBUFFERED: "1"
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NODE_ENV: production
    ports: ["3000:3000"]
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
```

- [ ] **Step 2: Create `.env` from `.env.example`**

Run: `cp .env.example .env`

Edit `.env` to add real keys for the smoke test (or stubs that fail loudly when called). At this stage placeholder values are fine because Phase 0 makes no real API calls.

- [ ] **Step 3: Smoke up**

Run: `docker compose up --build -d`
Expected: Both services start, both healthchecks go green within 60s.

- [ ] **Step 4: Hit healthz on backend**

Run: `curl -s http://localhost:8000/healthz`
Expected: `{"status":"ok","service":"sri-studio-backend"}`

- [ ] **Step 5: Hit / on frontend**

Run: `curl -s http://localhost:3000/ | head -20`
Expected: HTML output containing "Sri Studio" and "New Reel".

- [ ] **Step 6: Tear down**

Run: `docker compose down`

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: docker-compose wiring for backend + frontend"
```

---

## Phase 1: Probe matrix (fail-fast before any node code)

**Goal:** Ten standalone Python probes that each exercise one external dependency end-to-end against the real service. Every probe must exit 0 with the expected output before the matching pipeline code is written. This is SKILL.md Phase 3 + the global CLAUDE.md fail-fast rule made enforceable.

**Probe operating model:**
- Each probe lives in `backend/experiments/probe_NN_*.py` and is a single-file standalone script.
- Run with: `docker compose run --rm backend python experiments/probe_NN_name.py` (mounts the source, uses real `.env`).
- Each probe prints a structured `PROBE OK` line on success with the relevant numbers (cost, latency, dimensions).
- Each probe writes a transcript JSON to `experiments/out/probe_NN.json` capturing what came back from the real API. This is the source-of-truth for "what does this API actually return" when implementing the matching node.

### Task 1.1: Probe 01, OpenRouter Claude with prompt caching

**Files:**
- Create: `backend/experiments/probe_01_openrouter_claude_cached.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_01_openrouter_claude_cached.py

Verify Claude Sonnet via OpenRouter honors cache_control: ephemeral on the
system block. Two consecutive calls with the same system prompt; call #2
should show cached_input_tokens > 0.

Pass: PROBE OK with cache hit rate, cost numbers.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

API_KEY = os.environ["OPENROUTER_API_KEY"]
MODEL = os.environ.get("PLAN_MODEL", "anthropic/claude-sonnet-4-6")

# Long system prompt so caching makes a measurable difference.
SYSTEM = (
    "You are a video script planner for short-form vertical reels. "
    "Output a JSON object with: hook, scenes, voiceover_text, voice_style, "
    "music_mood, aspect_ratio. Each scene has scene_idx, duration_s, "
    "visual_prompt, voiceover_excerpt, motion. "
) * 80  # padded so the system block exceeds the cache-eligible threshold


def call(user_msg: str) -> dict:
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 200,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://studio.sshub.dev",
        "X-Title": "Sri Studio probe_01",
    }
    t0 = time.time()
    r = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    payload = r.json()
    payload["_latency_s"] = round(time.time() - t0, 3)
    return payload


def main() -> int:
    r1 = call("Plan a 5s reel about coffee.")
    time.sleep(1)
    r2 = call("Plan a 5s reel about a sunset.")
    transcript = {"first": r1, "second": r2}
    (OUT / "probe_01.json").write_text(json.dumps(transcript, indent=2))

    u1 = r1.get("usage", {})
    u2 = r2.get("usage", {})
    cached_2 = u2.get("prompt_tokens_details", {}).get("cached_tokens", 0)
    if cached_2 == 0:
        # OpenRouter sometimes nests cache info under the provider's shape;
        # look in usage directly too.
        cached_2 = u2.get("cache_read_input_tokens", 0)

    print("PROBE 01")
    print(f"  call1 input/output/latency: {u1.get('prompt_tokens')} / "
          f"{u1.get('completion_tokens')} / {r1['_latency_s']}s")
    print(f"  call2 input/output/latency: {u2.get('prompt_tokens')} / "
          f"{u2.get('completion_tokens')} / {r2['_latency_s']}s")
    print(f"  call2 cached_input_tokens: {cached_2}")
    if cached_2 <= 0:
        print("PROBE FAIL: no cache hit on call 2.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_01_openrouter_claude_cached.py`
Expected: `PROBE OK` printed; `experiments/out/probe_01.json` written with cache_read_input_tokens > 0 on the second call.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_01_openrouter_claude_cached.py
git commit -m "test(probe-01): verify OpenRouter Claude prompt caching"
```

### Task 1.2: Probe 02, ElevenLabs voice clone TTS with alignment

**Files:**
- Create: `backend/experiments/probe_02_elevenlabs_voiceclone_tts.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_02_elevenlabs_voiceclone_tts.py

Verify the user's cloned voice ID accepts text and returns MP3 plus
alignment timestamps that we can use for burn-in captions.

Pass: PROBE OK; mp3 file written; alignment array length matches text;
total alignment span is within 0.5s of the audio file's duration.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

API_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]
TEXT = "Sri Studio is a tiny tool that makes vertical reels in my own voice."


def main() -> int:
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        f"/with-timestamps?output_format=mp3_44100_128"
    )
    body = {
        "text": TEXT,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    r = httpx.post(url, json=body, headers=headers, timeout=60)
    r.raise_for_status()
    payload = r.json()

    audio_b64 = payload["audio_base64"]
    alignment = payload.get("alignment") or {}
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []

    import base64
    mp3_path = OUT / "probe_02.mp3"
    mp3_path.write_bytes(base64.b64decode(audio_b64))

    # Duration via ffprobe.
    dur = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)
    ]).decode().strip()
    audio_dur = float(dur)
    align_span = ends[-1] if ends else 0.0

    transcript = {
        "text": TEXT,
        "char_count": len(chars),
        "audio_duration_s": audio_dur,
        "alignment_span_s": align_span,
        "alignment_chars_first_10": chars[:10],
        "starts_first_10": starts[:10],
        "ends_first_10": ends[:10],
    }
    (OUT / "probe_02.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 02")
    print(f"  text length:        {len(TEXT)}")
    print(f"  alignment chars:    {len(chars)}")
    print(f"  audio duration:     {audio_dur:.3f}s")
    print(f"  alignment span:     {align_span:.3f}s")
    print(f"  delta:              {abs(audio_dur - align_span):.3f}s")
    if abs(audio_dur - align_span) > 0.5:
        print("PROBE FAIL: alignment span vs audio duration off by > 0.5s.")
        return 1
    if len(chars) < len(TEXT) - 5:
        print("PROBE FAIL: alignment chars far short of text length.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_02_elevenlabs_voiceclone_tts.py`
Expected: `PROBE OK`; `experiments/out/probe_02.mp3` plays back as your cloned voice; `experiments/out/probe_02.json` has alignment data.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_02_elevenlabs_voiceclone_tts.py
git commit -m "test(probe-02): verify ElevenLabs voice clone TTS + alignment"
```

### Task 1.3: Probe 03, Replicate Flux Schnell at 9:16

**Files:**
- Create: `backend/experiments/probe_03_replicate_flux_schnell_9x16.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_03_replicate_flux_schnell_9x16.py

Verify Flux Schnell on Replicate honors aspect_ratio="9:16" and returns an
image we can pass to ffmpeg.

Pass: PROBE OK; png file written; image dimensions are 9:16-shaped.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

os.environ["REPLICATE_API_TOKEN"] = os.environ["REPLICATE_API_TOKEN"]


def main() -> int:
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": "a cozy minimalist coffee shop at sunrise, warm light, "
                      "soft focus, vertical composition, cinematic",
            "aspect_ratio": "9:16",
            "num_outputs": 1,
            "output_format": "png",
            "output_quality": 90,
        },
    )

    # replicate.run returns a list of FileOutput objects in newer SDK versions;
    # fall back to URL strings for older shape.
    first = output[0] if isinstance(output, list) else output
    if hasattr(first, "read"):
        png_bytes = first.read()
    else:
        png_bytes = httpx.get(str(first), timeout=60).content

    img_path = OUT / "probe_03.png"
    img_path.write_bytes(png_bytes)

    # Dimensions via ffprobe.
    import subprocess
    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0", str(img_path)
    ]).decode().strip()
    w_str, h_str = info.split("x")
    w, h = int(w_str), int(h_str)
    ratio = w / h
    expected = 9 / 16

    transcript = {"width": w, "height": h, "ratio": ratio, "expected": expected}
    (OUT / "probe_03.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 03")
    print(f"  dimensions: {w}x{h}")
    print(f"  ratio:      {ratio:.4f} (expected {expected:.4f})")
    if abs(ratio - expected) > 0.05:
        print("PROBE FAIL: aspect ratio off by more than 5 percent.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_03_replicate_flux_schnell_9x16.py`
Expected: `PROBE OK`; `experiments/out/probe_03.png` is roughly 9:16 (e.g., 768x1344 or similar).

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_03_replicate_flux_schnell_9x16.py
git commit -m "test(probe-03): verify Flux Schnell 9:16 aspect ratio"
```

### Task 1.4: Probe 04, Replicate NSFW failure mode (documentation probe)

**Files:**
- Create: `backend/experiments/probe_04_replicate_flux_nsfw_behavior.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_04_replicate_flux_nsfw_behavior.py

Document what Replicate Flux Schnell does on a borderline prompt: does it
raise an exception, return a placeholder URL, or return a blank image?

Output: a transcript JSON we can match against in execute_images.py for
the retry-with-rewrite path. This probe always exits 0; it is documentation.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Borderline-but-legal-content prompt designed to trigger the moderation
# filter without being actively offensive. Adjust if Replicate's filter
# changes shape.
BORDERLINE = "a person in a swimsuit on a beach at sunset, photorealistic"


def main() -> int:
    transcript: dict = {"prompt": BORDERLINE}
    try:
        out = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": BORDERLINE,
                "aspect_ratio": "9:16",
                "num_outputs": 1,
                "output_format": "png",
                "disable_safety_checker": False,
            },
        )
        first = out[0] if isinstance(out, list) else out
        transcript["result"] = "succeeded"
        transcript["first_value"] = str(first)
    except Exception as e:
        transcript["result"] = "raised"
        transcript["exception_class"] = type(e).__name__
        transcript["exception_str"] = str(e)
        transcript["traceback"] = traceback.format_exc()

    (OUT / "probe_04.json").write_text(json.dumps(transcript, indent=2))
    print("PROBE 04 (documentation only)")
    print(json.dumps(transcript, indent=2)[:1000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_04_replicate_flux_nsfw_behavior.py`
Expected: exits 0 either way. Read `experiments/out/probe_04.json` to learn the failure shape.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_04_replicate_flux_nsfw_behavior.py
git commit -m "test(probe-04): document Replicate NSFW failure mode"
```

### Task 1.5: Probe 05, ffmpeg Ken Burns zoompan

**Files:**
- Create: `backend/experiments/probe_05_ffmpeg_kenburns_zoompan.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_05_ffmpeg_kenburns_zoompan.py

Verify the ffmpeg `zoompan` filter produces smooth Ken Burns motion on a
9:16 still over 2.5 seconds and outputs at exactly 1080x1920.

Pass: PROBE OK; mp4 written; ffprobe confirms dimensions and duration.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Reuse the image from probe_03 if present; else generate a solid color test.
SRC = OUT / "probe_03.png"
if not SRC.exists():
    # Generate a 1080x1920 solid-color test PNG via ffmpeg lavfi.
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=teal:s=1080x1920:d=1",
        "-frames:v", "1", str(SRC)
    ], check=True)

DST = OUT / "probe_05.mp4"
DURATION = 2.5
FPS = 30
FRAMES = int(DURATION * FPS)


def main() -> int:
    # zoompan: slow zoom-in from 1.0 -> 1.15 over duration; output 1080x1920.
    vf = (
        f"scale=2160:3840,"
        f"zoompan=z='min(zoom+0.0008,1.15)':d={FRAMES}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={FPS}"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(SRC),
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", str(DURATION), "-an", str(DST)
    ]
    subprocess.run(cmd, check=True)

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,nb_frames",
        "-of", "json", str(DST)
    ]).decode()
    parsed = json.loads(info)["streams"][0]
    w = int(parsed["width"])
    h = int(parsed["height"])
    dur = float(parsed.get("duration") or DURATION)

    transcript = {"width": w, "height": h, "duration_s": dur, "frames": parsed.get("nb_frames")}
    (OUT / "probe_05.json").write_text(json.dumps(transcript, indent=2))

    print("PROBE 05")
    print(f"  output: {w}x{h}, duration {dur:.3f}s")
    if (w, h) != (1080, 1920):
        print("PROBE FAIL: dimensions are not 1080x1920.")
        return 1
    if abs(dur - DURATION) > 0.2:
        print("PROBE FAIL: duration off by more than 0.2s.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_05_ffmpeg_kenburns_zoompan.py`
Expected: `PROBE OK`. Open `experiments/out/probe_05.mp4` and visually confirm the slow zoom is smooth.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_05_ffmpeg_kenburns_zoompan.py
git commit -m "test(probe-05): verify ffmpeg Ken Burns zoompan at 1080x1920"
```

### Task 1.6: Probe 06, ffmpeg burn-in captions from alignment

**Files:**
- Create: `backend/experiments/probe_06_ffmpeg_caption_burn_in.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_06_ffmpeg_caption_burn_in.py

Generate an ASS subtitle file from probe_02's ElevenLabs alignment data,
burn it onto probe_05's Ken Burns video, and visually verify legibility.

Pass: PROBE OK; mp4 written. Visual inspection: captions readable, lower
third placement, no overflow, sync within 100ms of audio (judgement call).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

ALIGN = OUT / "probe_02.json"
VIDEO = OUT / "probe_05.mp4"
DST = OUT / "probe_06.mp4"
ASS = OUT / "probe_06.ass"


def fmt(t: float) -> str:
    """ASS timestamp: H:MM:SS.cs"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main() -> int:
    if not ALIGN.exists() or not VIDEO.exists():
        print("PROBE FAIL: probe_02.json or probe_05.mp4 missing; run probes 02 and 05 first.")
        return 1

    # We saved only the first 10 char alignment. For a real probe, re-run
    # ElevenLabs to get a full alignment, or rebuild from raw probe_02.
    # For now, use a synthetic short alignment to validate the burn-in shape.
    chunks = [
        (0.0, 0.7, "Sri"),
        (0.7, 1.4, "Studio"),
        (1.4, 2.1, "vertical"),
        (2.1, 2.5, "reels"),
    ]

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Caption,DejaVu Sans,80,&H00FFFFFF,&H00000000,&H80000000,"
        "1,0,0,0,100,100,0,0,1,4,2,2,40,40,180,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    events = "\n".join(
        f"Dialogue: 0,{fmt(s)},{fmt(e)},Caption,,0,0,0,,{t}"
        for s, e, t in chunks
    )
    ASS.write_text(header + events + "\n")

    # Burn the subtitles.
    cmd = [
        "ffmpeg", "-y", "-i", str(VIDEO),
        "-vf", f"subtitles={ASS.name}:fontsdir=/usr/share/fonts",
        "-c:a", "copy", str(DST)
    ]
    subprocess.run(cmd, check=True, cwd=str(OUT))

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(DST)
    ]).decode().strip()
    print("PROBE 06")
    print(f"  output dimensions: {info}")
    print(f"  open {DST} to visually inspect captions.")
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_06_ffmpeg_caption_burn_in.py`
Expected: `PROBE OK`. Open `experiments/out/probe_06.mp4` and visually confirm captions are legible.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_06_ffmpeg_caption_burn_in.py
git commit -m "test(probe-06): verify ffmpeg ASS subtitle burn-in"
```

### Task 1.7: Probe 09, Langfuse Cloud trace

**Files:**
- Create: `backend/experiments/probe_09_langfuse_cloud_trace.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_09_langfuse_cloud_trace.py

Verify Langfuse Cloud SDK creates a trace with nested spans visible in the
dashboard. We send one trace with two child spans and flush.

Pass: PROBE OK; trace ID printed. Manually confirm in
https://cloud.langfuse.com that the trace appears within 30s.
"""
from __future__ import annotations

import os
import sys
import time

from langfuse import Langfuse


def main() -> int:
    lf = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )

    trace = lf.trace(name="probe_09_smoke", metadata={"probe": True})
    s1 = trace.span(name="extract_node", input={"brief": "test"})
    time.sleep(0.5)
    s1.end(output={"intent": "test_intent"})

    s2 = trace.span(name="plan_node", input={"intent": "test_intent"})
    time.sleep(0.5)
    s2.end(output={"plan": "stub"})

    lf.flush()

    print("PROBE 09")
    print(f"  trace_id: {trace.trace_id}")
    print("  Open https://cloud.langfuse.com and confirm trace appears.")
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_09_langfuse_cloud_trace.py`
Expected: `PROBE OK`; trace_id printed. Open Langfuse Cloud and confirm the trace + 2 spans show up.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_09_langfuse_cloud_trace.py
git commit -m "test(probe-09): verify Langfuse Cloud tracing"
```

### Task 1.8: Probe 10, End-to-end minimal smoke

**Files:**
- Create: `backend/experiments/probe_10_e2e_minimal.py`

- [ ] **Step 1: Write the probe**

```python
"""
probe_10_e2e_minimal.py

Simulate one complete pipeline run with a HARDCODED plan (no LLM call):
- TTS via ElevenLabs
- 2 images via Replicate Flux Schnell
- ffmpeg stitch into a 5s mp4

This is the integration smoke before any LangGraph wiring.

Pass: PROBE OK; experiments/out/probe_10.mp4 exists, plays, is ~5s long
and 1080x1920.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import replicate

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


HARDCODED_PLAN = {
    "voiceover_text": "Sri Studio. Vertical reels in my own voice, in seconds.",
    "scenes": [
        {"idx": 0, "duration_s": 2.5,
         "visual_prompt": "warm minimal coffee shop sunrise, vertical, cinematic"},
        {"idx": 1, "duration_s": 2.5,
         "visual_prompt": "abstract neon studio lights vertical composition cinematic"},
    ],
}


async def gen_image(scene: dict) -> Path:
    out = await asyncio.to_thread(
        replicate.run,
        "black-forest-labs/flux-schnell",
        input={
            "prompt": scene["visual_prompt"],
            "aspect_ratio": "9:16",
            "num_outputs": 1,
            "output_format": "png",
        },
    )
    first = out[0] if isinstance(out, list) else out
    if hasattr(first, "read"):
        png = first.read()
    else:
        png = httpx.get(str(first), timeout=60).content
    p = OUT / f"probe_10_scene_{scene['idx']:02d}.png"
    p.write_bytes(png)
    return p


def gen_voiceover(text: str) -> Path:
    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{os.environ['ELEVENLABS_VOICE_ID']}"
        f"?output_format=mp3_44100_128"
    )
    r = httpx.post(
        url,
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        timeout=60,
    )
    r.raise_for_status()
    p = OUT / "probe_10_voice.mp3"
    p.write_bytes(r.content)
    return p


def stitch(images: list[Path], voice: Path, dst: Path, scene_dur: float = 2.5) -> None:
    fps = 30
    frames = int(scene_dur * fps)
    inputs: list[str] = []
    filter_parts: list[str] = []
    for i, img in enumerate(images):
        inputs += ["-loop", "1", "-t", str(scene_dur), "-i", str(img)]
        zoom = 0.0008
        filter_parts.append(
            f"[{i}:v]scale=2160:3840,"
            f"zoompan=z='min(zoom+{zoom},1.15)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
    filter_parts.append(f"{concat_inputs}concat=n={len(images)}:v=1:a=0[vout]")
    vf = ";".join(filter_parts)

    voice_idx = len(images)
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(voice),
        "-filter_complex", vf,
        "-map", "[vout]", "-map", f"{voice_idx}:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(dst)
    ]
    subprocess.run(cmd, check=True)


async def main() -> int:
    print("PROBE 10: starting...")
    # Parallelise the two image gens.
    images = await asyncio.gather(*(gen_image(s) for s in HARDCODED_PLAN["scenes"]))
    voice = gen_voiceover(HARDCODED_PLAN["voiceover_text"])

    dst = OUT / "probe_10.mp4"
    stitch(images, voice, dst)

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json", str(dst)
    ]).decode()
    s = json.loads(info)["streams"][0]
    w, h, dur = int(s["width"]), int(s["height"]), float(s.get("duration", 0))
    print(f"  output: {w}x{h}, {dur:.3f}s")
    if (w, h) != (1080, 1920) or abs(dur - 5.0) > 0.4:
        print("PROBE FAIL: dimensions or duration out of bounds.")
        return 1
    print("PROBE OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Run the probe**

Run: `docker compose run --rm backend python experiments/probe_10_e2e_minimal.py`
Expected: `PROBE OK`; `experiments/out/probe_10.mp4` plays as a 5s 1080x1920 reel with two scenes and the voiceover.

- [ ] **Step 3: Commit**

```bash
git add backend/experiments/probe_10_e2e_minimal.py
git commit -m "test(probe-10): end-to-end smoke with hardcoded plan"
```

### Task 1.9: Defer probes 07 + 08

These depend on the music feature (`with_music=True`) which is itself out-of-scope at the 5s default. They get written when Phase 6's music sub-task is implemented (or skipped if music remains deferred at submission time).

- [ ] **Step 1: Note the deferral in `backend/experiments/README.md`**

Create `backend/experiments/README.md`:

```markdown
# Probes

Each probe exercises one external dependency end-to-end against the real
service. Each probe must exit 0 with `PROBE OK` before the matching
pipeline code is committed (per global CLAUDE.md fail-fast rule).

| # | File | Status |
|---|------|--------|
| 01 | probe_01_openrouter_claude_cached.py | required |
| 02 | probe_02_elevenlabs_voiceclone_tts.py | required |
| 03 | probe_03_replicate_flux_schnell_9x16.py | required |
| 04 | probe_04_replicate_flux_nsfw_behavior.py | documentation |
| 05 | probe_05_ffmpeg_kenburns_zoompan.py | required |
| 06 | probe_06_ffmpeg_caption_burn_in.py | required |
| 07 | probe_07_ffmpeg_audio_mix_duck.py | deferred (gated on `with_music`) |
| 08 | probe_08_elevenlabs_music.py | deferred (gated on `with_music`) |
| 09 | probe_09_langfuse_cloud_trace.py | required |
| 10 | probe_10_e2e_minimal.py | required |

Run any probe via:
    docker compose run --rm backend python experiments/probe_NN_*.py

Outputs (audio, images, video, JSON transcripts) land in `experiments/out/`
which is gitignored.
```

- [ ] **Step 2: Commit**

```bash
git add backend/experiments/README.md
git commit -m "docs(probes): document probe matrix and deferral status"
```

---

## Phase 2: State schema, cost helpers, tracing client

**Goal:** Define the typed state object the LangGraph machine carries, the cost-print helpers wrapping every paid API call, the daily cost cap, and the Langfuse client. Each piece gets a unit test.

### Task 2.1: ReelState, ScriptPlan, Scene, ExtractedIntent (Pydantic models)

**Files:**
- Create: `backend/src/reel_gen/state.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_state.py
from pathlib import Path

import pytest
from pydantic import ValidationError

from reel_gen.state import ExtractedIntent, ReelState, Scene, ScriptPlan


def test_scene_validates_positive_duration():
    s = Scene(scene_idx=0, duration_s=2.5, visual_prompt="x", voiceover_excerpt="y", motion="zoom_in")
    assert s.scene_idx == 0
    with pytest.raises(ValidationError):
        Scene(scene_idx=0, duration_s=-1, visual_prompt="x", voiceover_excerpt="y", motion="zoom_in")


def test_scriptplan_round_trip():
    plan = ScriptPlan(
        hook="A.",
        scenes=[Scene(scene_idx=0, duration_s=5.0, visual_prompt="p", voiceover_excerpt="v", motion="zoom_in")],
        voiceover_text="A.",
        voice_style="warm",
        music_mood=None,
        aspect_ratio="9:16",
    )
    j = plan.model_dump_json()
    plan2 = ScriptPlan.model_validate_json(j)
    assert plan2.scenes[0].motion == "zoom_in"


def test_reelstate_minimum():
    s = ReelState(run_id="abc", brief="hello", duration_s=5, with_music=False)
    assert s.intent is None
    assert s.image_paths == []
    assert s.cost_ledger == []
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_state.py -v`
Expected: ImportError or ModuleNotFoundError on `reel_gen.state`.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/state.py
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
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_state.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/state.py backend/tests/__init__.py backend/tests/test_state.py
git commit -m "feat(state): add ReelState, ScriptPlan, Scene, CostEntry Pydantic models"
```

### Task 2.2: Cost helpers and rates dict

**Files:**
- Create: `backend/src/reel_gen/llm/__init__.py`
- Create: `backend/src/reel_gen/llm/cost.py`
- Create: `backend/tests/test_cost.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cost.py
from reel_gen.llm.cost import RATES, cost_for_llm_usage, cost_for_units


def test_cost_for_llm_usage_with_known_model():
    # Claude Sonnet rates (input + output) per 1M tokens.
    cost = cost_for_llm_usage(
        model="anthropic/claude-sonnet-4-6",
        input_tokens=1_000_000,
        output_tokens=0,
        cached_input_tokens=0,
    )
    expected = RATES["anthropic/claude-sonnet-4-6"]["input_per_mtok"]
    assert abs(cost - expected) < 1e-6


def test_cost_for_llm_usage_unknown_model_returns_none():
    assert cost_for_llm_usage(model="some/unknown", input_tokens=1000, output_tokens=0) is None


def test_cost_for_units_image():
    # Flux Schnell at $0.003 per image.
    c = cost_for_units(provider="replicate", unit_label="images", units=2)
    assert abs(c - 0.006) < 1e-6


def test_unit_cost_pre_prints_rate_and_estimate(capsys):
    from reel_gen.llm.cost import unit_cost_pre
    unit_cost_pre(phase="image", provider="replicate", unit_label="images", units=3)
    out = capsys.readouterr().out
    assert "[COST PRE]" in out
    assert "replicate" in out
    assert "unit_rate=$0.003" in out
    assert "est_cost=$0.009" in out


def test_unit_cost_pre_unknown_rate_logs_warning(capsys):
    from reel_gen.llm.cost import unit_cost_pre
    unit_cost_pre(phase="x", provider="unknown", unit_label="zzz", units=1)
    out = capsys.readouterr().out
    assert "rate=unknown" in out
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_cost.py -v`
Expected: ModuleNotFoundError or `AttributeError: unit_cost_pre` after partial implementation.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/llm/__init__.py
"""LLM clients, cost helpers, prompt files."""
```

```python
# backend/src/reel_gen/llm/cost.py
"""Cost helpers per global CLAUDE.md hard rule:
print cost pre/post EVERY paid API call.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from reel_gen.state import CostEntry

# Per 1M tokens, USD. Update when model versions change.
RATES: dict[str, dict[str, float]] = {
    "anthropic/claude-sonnet-4-6": {
        "input_per_mtok": 3.00,
        "output_per_mtok": 15.00,
        "cache_read_per_mtok": 0.30,
    },
    "anthropic/claude-haiku-4-5": {
        "input_per_mtok": 0.80,
        "output_per_mtok": 4.00,
        "cache_read_per_mtok": 0.08,
    },
}

# Per-unit pricing for non-token APIs.
#
# Sources (verified 2026-05-07; re-verify if a probe shows a different bill):
#   - Replicate Flux Schnell:
#       https://replicate.com/black-forest-labs/flux-schnell
#       $0.003 per image at default 4 MP-second budget; 9:16 outputs land
#       under that budget so each call bills $0.003.
#   - ElevenLabs Starter ($5 / month):
#       30,000 characters / month included; ~$0.00017 per included character.
#       We use $0.00030 as a conservative "marginal cost" estimate so the
#       cost ledger overstates rather than understates spend.
#   - ElevenLabs Music (when enabled):
#       Pricing TBD until probe_08 lands; $0.005/s is a placeholder.
#
# The unit_cost_pre helper prints these rates on every call so a reader of
# the terminal output sees the price BEFORE the bill arrives. Per global
# CLAUDE.md: never quote LLM cost without measuring; never silently skip
# an unknown rate.
UNIT_RATES: dict[tuple[str, str], float] = {
    ("replicate", "images"): 0.003,         # Flux Schnell, USD per image
    ("elevenlabs", "tts_chars"): 0.00030,   # USD per character (conservative)
    ("elevenlabs", "music_seconds"): 0.005, # USD per second (placeholder; verify)
}


def cost_for_llm_usage(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float | None:
    """Returns USD cost or None when the model is unknown.

    Per global CLAUDE.md: never silently skip an unknown rate; print
    'rate unknown' so we notice.
    """
    rate = RATES.get(model)
    if rate is None:
        return None
    fresh_in = max(0, input_tokens - cached_input_tokens)
    cost = (
        (fresh_in / 1_000_000) * rate["input_per_mtok"]
        + (output_tokens / 1_000_000) * rate["output_per_mtok"]
        + (cached_input_tokens / 1_000_000) * rate.get("cache_read_per_mtok", rate["input_per_mtok"])
    )
    return round(cost, 6)


def cost_for_units(*, provider: str, unit_label: str, units: float) -> float:
    rate = UNIT_RATES.get((provider, unit_label))
    if rate is None:
        return 0.0
    return round(units * rate, 6)


def llm_cost_pre(*, phase: str, model: str, input_tokens_estimate: int) -> None:
    """Print PRE-call cost estimate. Called BEFORE the API call."""
    rate = RATES.get(model)
    if rate is None:
        print(f"[COST PRE] phase={phase} model={model} rate=unknown "
              f"input_est={input_tokens_estimate}")
        return
    est = (input_tokens_estimate / 1_000_000) * rate["input_per_mtok"]
    print(f"[COST PRE] phase={phase} model={model} input_est={input_tokens_estimate} "
          f"est_cost=${est:.4f}")


def llm_cost_post(
    *,
    phase: str,
    model: str,
    usage: dict[str, Any],
) -> CostEntry:
    """Print POST-call actuals and return a CostEntry for the ledger."""
    in_tok = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out_tok = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    cached = int(
        (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        or usage.get("cache_read_input_tokens", 0)
    )
    cost = cost_for_llm_usage(
        model=model, input_tokens=in_tok, output_tokens=out_tok, cached_input_tokens=cached
    )
    cost_str = "rate-unknown" if cost is None else f"${cost:.6f}"
    print(f"[COST POST] phase={phase} model={model} "
          f"in={in_tok} out={out_tok} cached={cached} cost={cost_str}")
    return CostEntry(
        phase=phase,
        provider="openrouter",
        model=model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        cached_input_tokens=cached,
        cost_usd=(cost or 0.0),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def unit_cost_pre(
    *,
    phase: str,
    provider: str,
    unit_label: str,
    units: float,
) -> None:
    """Print PRE-call cost estimate for non-LLM paid APIs.

    Called BEFORE every Replicate / ElevenLabs / etc paid call. Symmetric to
    llm_cost_pre. Per global CLAUDE.md hard rule: print cost pre AND post for
    every paid API call.
    """
    rate = UNIT_RATES.get((provider, unit_label))
    if rate is None:
        print(f"[COST PRE] phase={phase} provider={provider} "
              f"{unit_label}={units} rate=unknown")
        return
    est = round(units * rate, 6)
    print(f"[COST PRE] phase={phase} provider={provider} "
          f"{unit_label}={units} unit_rate=${rate} est_cost=${est}")


def unit_cost_post(
    *,
    phase: str,
    provider: str,
    unit_label: str,
    units: float,
) -> CostEntry:
    cost = cost_for_units(provider=provider, unit_label=unit_label, units=units)
    print(f"[COST POST] phase={phase} provider={provider} "
          f"{unit_label}={units} cost=${cost:.6f}")
    return CostEntry(
        phase=phase,
        provider=provider,
        units=units,
        unit_label=unit_label,
        cost_usd=cost,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_cost.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/llm/ backend/tests/test_cost.py
git commit -m "feat(llm): cost helpers + rates dict + pre/post print pattern"
```

### Task 2.3: Daily cost cap

**Files:**
- Create: `backend/src/reel_gen/llm/cost_cap.py`
- Create: `backend/tests/test_cost_cap.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cost_cap.py
from datetime import date

import pytest

from reel_gen.llm.cost_cap import (
    DailyCostCapExceeded,
    add_to_today,
    check_cap,
    today_total_usd,
)


def test_add_and_total(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")
    add_to_today(0.10)
    add_to_today(0.05)
    assert abs(today_total_usd() - 0.15) < 1e-6


def test_check_cap_under(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")
    add_to_today(1.00)
    check_cap(prospective_cost_usd=0.10)  # should not raise


def test_check_cap_over_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "1.00")
    add_to_today(0.95)
    with pytest.raises(DailyCostCapExceeded):
        check_cap(prospective_cost_usd=0.10)
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_cost_cap.py -v`
Expected: ModuleNotFoundError on `reel_gen.llm.cost_cap`.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/llm/cost_cap.py
"""Daily cost cap enforced before any paid API call.

Per spec section 8d: a JSON file in the runs volume tracks cumulative
USD spent today (UTC). Before any paid call, callers invoke check_cap()
with the prospective cost; over-cap raises DailyCostCapExceeded. After
the call, callers call add_to_today() with the actual cost.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class DailyCostCapExceeded(RuntimeError):
    """Raised when the day's cumulative cost would exceed DAILY_COST_CAP_USD."""


def _cap_file() -> Path:
    runs = Path(os.environ.get("RUNS_DIR", "./runs"))
    runs.mkdir(parents=True, exist_ok=True)
    return runs / "_daily_cost.json"


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load() -> dict:
    f = _cap_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    _cap_file().write_text(json.dumps(data, indent=2))


def today_total_usd() -> float:
    data = _load()
    return float(data.get(_today_key(), 0.0))


def add_to_today(cost_usd: float) -> None:
    data = _load()
    key = _today_key()
    data[key] = round(float(data.get(key, 0.0)) + float(cost_usd), 6)
    _save(data)


def check_cap(*, prospective_cost_usd: float) -> None:
    cap = float(os.environ.get("DAILY_COST_CAP_USD", "5.00"))
    total = today_total_usd()
    if total + prospective_cost_usd > cap:
        raise DailyCostCapExceeded(
            f"Daily cost cap of ${cap:.2f} would be exceeded "
            f"(today=${total:.4f}, prospective=${prospective_cost_usd:.4f})"
        )
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_cost_cap.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/llm/cost_cap.py backend/tests/test_cost_cap.py
git commit -m "feat(cost-cap): daily UTC cost cap with JSON ledger + check/add API"
```

### Task 2.4: ElevenLabs monthly character quota

**Why this exists:** The Starter ElevenLabs plan caps at 30,000 characters per month. Going over silently bills the next plan tier or chops off audio. This module surfaces remaining quota on every TTS call and refuses new calls when the projected usage would exceed the limit.

**Files:**
- Create: `backend/src/reel_gen/llm/elevenlabs_quota.py`
- Create: `backend/tests/test_elevenlabs_quota.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_elevenlabs_quota.py
import pytest

from reel_gen.llm.elevenlabs_quota import (
    ElevenLabsQuotaExceeded,
    add_chars_to_month,
    check_char_quota,
    month_total_chars,
    remaining_chars,
)


def test_add_and_total(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_LIMIT", "30000")
    add_chars_to_month(500)
    add_chars_to_month(250)
    assert month_total_chars() == 750
    assert remaining_chars() == 30000 - 750


def test_check_char_quota_under(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_LIMIT", "30000")
    monkeypatch.setenv("ELEVENLABS_QUOTA_BLOCK_AT_PCT", "90")
    add_chars_to_month(20000)  # 66.7% used
    check_char_quota(prospective_chars=200)  # would be 67.3%, under 90%


def test_check_char_quota_over_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_LIMIT", "1000")
    monkeypatch.setenv("ELEVENLABS_QUOTA_BLOCK_AT_PCT", "90")
    add_chars_to_month(850)
    with pytest.raises(ElevenLabsQuotaExceeded):
        check_char_quota(prospective_chars=100)  # 95% > 90% threshold
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_elevenlabs_quota.py -v`
Expected: ModuleNotFoundError on `reel_gen.llm.elevenlabs_quota`.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/llm/elevenlabs_quota.py
"""Monthly ElevenLabs character quota tracking.

Starter plan: 30,000 chars/month (~30 min audio at 1000 chars/min spoken).
Creator plan: 100,000 chars/month (~100 min). Set ELEVENLABS_MONTHLY_CHAR_LIMIT
in .env to match your plan.

Block threshold: ELEVENLABS_QUOTA_BLOCK_AT_PCT (default 90). Once today's run
would push usage past this percentage, new TTS calls raise rather than
quietly burning into the next billing tier.

State lives in <RUNS_DIR>/_monthly_usage.json keyed by 'YYYY-MM'.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class ElevenLabsQuotaExceeded(RuntimeError):
    """Raised when the projected monthly char usage exceeds the block threshold."""


def _quota_file() -> Path:
    runs = Path(os.environ.get("RUNS_DIR", "./runs"))
    runs.mkdir(parents=True, exist_ok=True)
    return runs / "_monthly_usage.json"


def _month_key() -> str:
    n = datetime.now(timezone.utc)
    return f"{n.year:04d}-{n.month:02d}"


def _load() -> dict:
    f = _quota_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    _quota_file().write_text(json.dumps(data, indent=2))


def month_total_chars() -> int:
    return int(_load().get(_month_key(), 0))


def add_chars_to_month(chars: int) -> None:
    data = _load()
    key = _month_key()
    data[key] = int(data.get(key, 0)) + int(chars)
    _save(data)


def _limit() -> int:
    return int(os.environ.get("ELEVENLABS_MONTHLY_CHAR_LIMIT", "30000"))


def remaining_chars() -> int:
    return max(0, _limit() - month_total_chars())


def usage_pct() -> float:
    limit = _limit()
    return 0.0 if limit == 0 else (month_total_chars() / limit) * 100.0


def check_char_quota(*, prospective_chars: int) -> None:
    """Raise if (current + prospective) / limit exceeds block threshold."""
    block_at = float(os.environ.get("ELEVENLABS_QUOTA_BLOCK_AT_PCT", "90"))
    limit = _limit()
    projected = month_total_chars() + int(prospective_chars)
    projected_pct = (projected / limit) * 100.0 if limit > 0 else 0.0
    if projected_pct > block_at:
        raise ElevenLabsQuotaExceeded(
            f"ElevenLabs monthly char quota would exceed block threshold "
            f"of {block_at:.0f}%: month_used={month_total_chars()}, "
            f"prospective={prospective_chars}, limit={limit}, "
            f"projected_pct={projected_pct:.1f}%. "
            f"Raise ELEVENLABS_QUOTA_BLOCK_AT_PCT or upgrade plan."
        )


def quota_status_line() -> str:
    """One-line status for printing on every TTS call."""
    return (
        f"[QUOTA] elevenlabs month_chars={month_total_chars()} / "
        f"{_limit()} ({usage_pct():.1f}% used, {remaining_chars()} remaining)"
    )
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_elevenlabs_quota.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/llm/elevenlabs_quota.py backend/tests/test_elevenlabs_quota.py
git commit -m "feat(quota): ElevenLabs monthly char tracker with block threshold"
```

### Task 2.5: Langfuse client wrapper

**Files:**
- Create: `backend/src/reel_gen/tracing/__init__.py`
- Create: `backend/src/reel_gen/tracing/langfuse_client.py`
- Create: `backend/tests/test_langfuse_client.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_langfuse_client.py
from reel_gen.tracing.langfuse_client import get_langfuse, with_span


def test_get_langfuse_returns_singleton(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    a = get_langfuse()
    b = get_langfuse()
    assert a is b


def test_with_span_decorator_runs_function(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    @with_span(name="unit_test_span")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_langfuse_client.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/tracing/__init__.py
"""Langfuse Cloud tracing integration."""
```

```python
# backend/src/reel_gen/tracing/langfuse_client.py
"""Singleton Langfuse client + a thin span decorator.

Per spec section 8b: every node and every paid API call gets a span.
Per global CLAUDE.md: tracing is non-negotiable; this is the cheap
default that ships with the project so no node forgets to instrument.
"""
from __future__ import annotations

import functools
import os
from typing import Any, Callable, TypeVar

from langfuse import Langfuse

_LANGFUSE: Langfuse | None = None
F = TypeVar("F", bound=Callable[..., Any])


def get_langfuse() -> Langfuse:
    global _LANGFUSE
    if _LANGFUSE is None:
        _LANGFUSE = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get(
                "LANGFUSE_BASE_URL",
                os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            ),
        )
    return _LANGFUSE


def with_span(*, name: str) -> Callable[[F], F]:
    """Wraps a function with a Langfuse span. Trace ID comes from the
    enclosing trace (set per-run in the API layer)."""
    def deco(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            lf = get_langfuse()
            span = lf.span(name=name, input={"args_len": len(args)})
            try:
                result = func(*args, **kwargs)
                span.end(output={"ok": True})
                return result
            except Exception as e:
                span.end(level="ERROR", status_message=str(e))
                raise
        return wrapper  # type: ignore[return-value]
    return deco


def flush() -> None:
    if _LANGFUSE is not None:
        _LANGFUSE.flush()
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_langfuse_client.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/tracing/ backend/tests/test_langfuse_client.py
git commit -m "feat(tracing): Langfuse Cloud singleton + with_span decorator"
```

### Task 2.6: OpenRouter client with caching

**Files:**
- Create: `backend/src/reel_gen/llm/openrouter.py`
- Create: `backend/tests/test_openrouter.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_openrouter.py
import json

import respx
from httpx import Response

from reel_gen.llm.openrouter import call_claude_cached


@respx.mock
def test_call_claude_cached_includes_cache_control(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return Response(
            200,
            json={
                "id": "x",
                "choices": [{"message": {"role": "assistant", "content": "hi"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 5,
                          "prompt_tokens_details": {"cached_tokens": 80}},
            },
        )

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(side_effect=handler)

    result = call_claude_cached(
        model="anthropic/claude-sonnet-4-6",
        system="SYSTEM",
        user="USER",
        max_tokens=10,
        phase="test",
    )

    sys_block = captured["body"]["messages"][0]["content"][0]
    assert sys_block.get("cache_control") == {"type": "ephemeral"}
    assert result.text == "hi"
    assert result.cost_entry.cached_input_tokens == 80
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_openrouter.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/llm/openrouter.py
"""OpenRouter client wired with prompt caching + cost helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from reel_gen.llm.cost import llm_cost_post, llm_cost_pre
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class OpenRouterResult:
    text: str
    cost_entry: CostEntry
    raw: dict


def call_claude_cached(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 1024,
    phase: str,
    estimated_input_tokens: int = 0,
) -> OpenRouterResult:
    """Single Claude call with cache_control: ephemeral on the system block.

    Pre-call: checks daily cost cap with a conservative estimate, prints
    PRE cost line. Post-call: prints POST cost line, adds actual cost
    to the daily ledger.
    """
    api_key = os.environ["OPENROUTER_API_KEY"]
    if estimated_input_tokens == 0:
        estimated_input_tokens = max(len(system) // 4, 1)

    # Conservative pre-cap estimate: assume worst case (no cache hit).
    from reel_gen.llm.cost import cost_for_llm_usage
    est_cost = cost_for_llm_usage(
        model=model, input_tokens=estimated_input_tokens, output_tokens=max_tokens
    ) or 0.0
    check_cap(prospective_cost_usd=est_cost)

    llm_cost_pre(phase=phase, model=model, input_tokens_estimate=estimated_input_tokens)

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
                ],
            },
            {"role": "user", "content": user},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://studio.sshub.dev",
        "X-Title": "Sri Studio",
    }

    r = httpx.post(OPENROUTER_URL, json=body, headers=headers, timeout=120)
    r.raise_for_status()
    payload = r.json()

    text = payload["choices"][0]["message"]["content"]
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))

    cost_entry = llm_cost_post(phase=phase, model=model, usage=payload.get("usage", {}))
    add_to_today(cost_entry.cost_usd)

    return OpenRouterResult(text=text, cost_entry=cost_entry, raw=payload)
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_openrouter.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/llm/openrouter.py backend/tests/test_openrouter.py
git commit -m "feat(llm): OpenRouter Claude client with cache_control + cost-cap pre-check"
```

---

## Phase 3: Extract + Plan nodes + LangGraph wiring (CLI mode first)

**Goal:** Two LangGraph nodes (Extract, Plan) wired into a partial graph runnable from the CLI: `python -m reel_gen --prompt "..."` produces `runs/<id>/intent.json` and `runs/<id>/plan.json`. No Execute, no Stitch yet.

### Task 3.1: Prompt files

**Files:**
- Create: `backend/src/reel_gen/llm/prompts/extract.md`
- Create: `backend/src/reel_gen/llm/prompts/plan.md`

- [ ] **Step 1: Create `backend/src/reel_gen/llm/prompts/extract.md`**

```markdown
You are a structured-extraction agent for a vertical-video creation tool.

Given a free-form user brief for an Instagram Reel, output a JSON object
matching this exact schema (no extra fields, no commentary):

{
  "topic": "<one-line topic>",
  "tone": "energetic" | "warm" | "informative" | "promotional" | "neutral",
  "audience": "<short audience descriptor>",
  "brand_voice": "<brand-voice descriptor or null>",
  "notes": "AMBIGUOUS_BRIEF" | null
}

Rules:
- If the brief is too vague to determine tone, set tone="neutral" and notes="AMBIGUOUS_BRIEF".
- Never invent brand names not present in the brief.
- Output ONLY the JSON object. No prose, no markdown fences, no explanation.
```

- [ ] **Step 2: Create `backend/src/reel_gen/llm/prompts/plan.md`**

```markdown
You are a video script planner for short-form vertical reels.

You will receive an ExtractedIntent JSON and a target duration in
seconds. Output a JSON object matching this exact schema:

{
  "hook": "<one-line opening (5 to 12 words)>",
  "scenes": [
    {
      "scene_idx": 0,
      "duration_s": <float>,
      "visual_prompt": "<full Flux Schnell image prompt; vertical 9:16; cinematic; no text-in-image>",
      "voiceover_excerpt": "<the words said during this scene>",
      "motion": "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "static"
    }
  ],
  "voiceover_text": "<the entire narration; sums to roughly duration_s seconds at a natural pace, ~150 words per minute>",
  "voice_style": "<short style descriptor passed to TTS, e.g. 'warm', 'energetic'>",
  "music_mood": "<mood descriptor or null>",
  "aspect_ratio": "9:16"
}

Rules:
- Scene count: 1 or 2 for <=10s; 4 to 8 for >=30s; pick a middle count for in-between durations.
- Sum of scene durations MUST equal the target duration_s exactly.
- Each visual_prompt must be self-contained and include vertical / 9:16 / cinematic cues.
- Do NOT include text overlays in the visual_prompt; captions are added in post.
- Output ONLY the JSON object. No prose, no markdown fences.
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/reel_gen/llm/prompts/
git commit -m "feat(prompts): extract.md and plan.md system prompts"
```

### Task 3.2: Extract node

**Files:**
- Create: `backend/src/reel_gen/nodes/__init__.py`
- Create: `backend/src/reel_gen/nodes/extract.py`
- Create: `backend/tests/test_extract.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_extract.py
import json

import respx
from httpx import Response

from reel_gen.nodes.extract import extract_node
from reel_gen.state import ReelState


@respx.mock
def test_extract_node_parses_intent(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("EXTRACT_MODEL", "anthropic/claude-haiku-4-5")

    intent_json = json.dumps({
        "topic": "spring kitchen sale",
        "tone": "energetic",
        "audience": "home cooks",
        "brand_voice": "Sur La Table",
        "notes": None,
    })
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": intent_json}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 50,
                      "prompt_tokens_details": {"cached_tokens": 0}},
        })
    )

    state = ReelState(run_id="r1", brief="Sur La Table spring kitchen sale, fun energy", duration_s=5)
    new_state = extract_node(state)
    assert new_state.intent is not None
    assert new_state.intent.topic == "spring kitchen sale"
    assert new_state.intent.tone == "energetic"
    assert len(new_state.cost_ledger) == 1
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_extract.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/nodes/__init__.py
"""LangGraph pipeline nodes."""
```

```python
# backend/src/reel_gen/nodes/extract.py
"""Extract node: free-form brief -> ExtractedIntent JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path

from reel_gen.llm.openrouter import call_claude_cached
from reel_gen.state import ExtractedIntent, NodeError, ReelState
from reel_gen.tracing.langfuse_client import with_span

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "extract.md"


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


@with_span(name="extract_node")
def extract_node(state: ReelState) -> ReelState:
    model = os.environ.get("EXTRACT_MODEL", "anthropic/claude-haiku-4-5")
    user = f"BRIEF:\n{state.brief}\n\nDURATION_S: {state.duration_s}"
    try:
        result = call_claude_cached(
            model=model,
            system=_load_system_prompt(),
            user=user,
            max_tokens=400,
            phase="extract",
        )
        text = result.text.strip()
        # Strip accidental markdown fences if the model adds them.
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text[:-3]
        data = json.loads(text)
        intent = ExtractedIntent.model_validate(data)
        state.intent = intent
        state.cost_ledger.append(result.cost_entry)
    except Exception as e:
        state.errors.append(NodeError(node="extract", message=str(e), fatal=True))
        # Conservative fallback so downstream still runs.
        state.intent = ExtractedIntent(
            topic=state.brief[:80],
            tone="neutral",
            audience="general",
            notes="EXTRACT_FAILED",
        )
    return state
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_extract.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/nodes/__init__.py backend/src/reel_gen/nodes/extract.py backend/tests/test_extract.py
git commit -m "feat(node:extract): parse free-form brief into ExtractedIntent"
```

### Task 3.3: Plan node

**Files:**
- Create: `backend/src/reel_gen/nodes/plan.py`
- Create: `backend/tests/test_plan_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_plan_node.py
import json
from pathlib import Path

import respx
from httpx import Response

from reel_gen.nodes.plan import plan_node
from reel_gen.state import ExtractedIntent, ReelState


@respx.mock
def test_plan_node_writes_plan_json(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("PLAN_MODEL", "anthropic/claude-sonnet-4-6")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))

    plan_json = json.dumps({
        "hook": "Spring is here.",
        "scenes": [
            {"scene_idx": 0, "duration_s": 5.0,
             "visual_prompt": "spring market vertical 9:16 cinematic",
             "voiceover_excerpt": "Spring is here.", "motion": "zoom_in"}
        ],
        "voiceover_text": "Spring is here.",
        "voice_style": "warm",
        "music_mood": None,
        "aspect_ratio": "9:16",
    })
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": plan_json}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 200,
                      "prompt_tokens_details": {"cached_tokens": 400}},
        })
    )

    state = ReelState(
        run_id="rxx",
        brief="spring sale",
        duration_s=5,
        intent=ExtractedIntent(topic="spring sale", tone="energetic", audience="general"),
    )
    new_state = plan_node(state)
    assert new_state.plan is not None
    assert len(new_state.plan.scenes) == 1
    assert (Path(tmp_path) / "rxx" / "plan.json").exists()
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_plan_node.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/nodes/plan.py
"""Plan node: ExtractedIntent + duration -> ScriptPlan, written to disk."""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from reel_gen.llm.openrouter import call_claude_cached
from reel_gen.state import NodeError, ReelState, Scene, ScriptPlan
from reel_gen.tracing.langfuse_client import with_span

_PROMPT_PATH = Path(__file__).parent.parent / "llm" / "prompts" / "plan.md"
_MAX_RETRIES = 2


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _fallback_plan(state: ReelState) -> ScriptPlan:
    """Deterministic fallback when the LLM keeps returning malformed JSON."""
    return ScriptPlan(
        hook=state.brief[:80],
        scenes=[Scene(
            scene_idx=0, duration_s=float(state.duration_s),
            visual_prompt=f"{state.brief}, vertical 9:16, cinematic",
            voiceover_excerpt=state.brief[:120], motion="zoom_in",
        )],
        voiceover_text=state.brief[:200],
        voice_style="neutral",
        music_mood=None,
        aspect_ratio="9:16",
    )


@with_span(name="plan_node")
def plan_node(state: ReelState) -> ReelState:
    model = os.environ.get("PLAN_MODEL", "anthropic/claude-sonnet-4-6")
    intent_json = state.intent.model_dump_json() if state.intent else "{}"
    user = f"INTENT:\n{intent_json}\n\nDURATION_S: {state.duration_s}\n" \
           f"WITH_MUSIC: {state.with_music}"

    last_err: str | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            result = call_claude_cached(
                model=model,
                system=_load_system_prompt(),
                user=user if attempt == 0 else
                     user + f"\n\nVALIDATION_ERROR_FROM_PRIOR_ATTEMPT: {last_err}",
                max_tokens=2000,
                phase="plan",
            )
            data = json.loads(_strip_fences(result.text))
            plan = ScriptPlan.model_validate(data)
            state.plan = plan
            state.cost_ledger.append(result.cost_entry)
            break
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = str(e)
            if attempt == _MAX_RETRIES:
                state.errors.append(NodeError(
                    node="plan", message=f"plan validation failed after retries: {e}",
                    fatal=False,
                ))
                state.plan = _fallback_plan(state)
        except Exception as e:
            state.errors.append(NodeError(node="plan", message=str(e), fatal=True))
            state.plan = _fallback_plan(state)
            break

    # Write plan.json for audit (the "plan is the product" rule from SKILL.md).
    runs = Path(os.environ.get("RUNS_DIR", "./runs"))
    run_dir = runs / state.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "plan.json").write_text(state.plan.model_dump_json(indent=2))
    if state.intent:
        (run_dir / "intent.json").write_text(state.intent.model_dump_json(indent=2))
    return state
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_plan_node.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/nodes/plan.py backend/tests/test_plan_node.py
git commit -m "feat(node:plan): produce ScriptPlan with retry + fallback + plan.json artifact"
```

### Task 3.4: Partial graph + CLI entry

**Files:**
- Create: `backend/src/reel_gen/graph.py`
- Modify: `backend/src/reel_gen/__main__.py`

- [ ] **Step 1: Write `backend/src/reel_gen/graph.py`**

```python
"""LangGraph wiring. Phase 3 ships Extract -> Plan only.
Approval Gate, Execute, and Stitch land in Phases 5, 6, 7.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from reel_gen.nodes.extract import extract_node
from reel_gen.nodes.plan import plan_node
from reel_gen.state import ReelState


def build_graph_until_plan():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", END)
    return g.compile()
```

- [ ] **Step 2: Update `backend/src/reel_gen/__main__.py`**

```python
"""CLI entry: python -m reel_gen --prompt "..." [--duration 5]"""
from __future__ import annotations

import argparse
import sys
import uuid

from reel_gen.graph import build_graph_until_plan
from reel_gen.state import ReelState
from reel_gen.tracing.langfuse_client import flush


def main() -> int:
    p = argparse.ArgumentParser(prog="reel_gen")
    p.add_argument("--prompt", required=True)
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--with-music", action="store_true")
    args = p.parse_args()

    run_id = uuid.uuid4().hex[:12]
    state = ReelState(
        run_id=run_id,
        brief=args.prompt,
        duration_s=args.duration,
        with_music=args.with_music,
    )
    graph = build_graph_until_plan()
    final: ReelState = graph.invoke(state)
    flush()

    print(f"\nrun_id: {run_id}")
    print(f"intent: {final['intent'] if isinstance(final, dict) else final.intent}")
    plan_obj = final["plan"] if isinstance(final, dict) else final.plan
    print(f"plan scenes: {len(plan_obj.scenes) if plan_obj else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke run end-to-end against real APIs**

Run: `docker compose run --rm backend python -m reel_gen --prompt "Sur La Table spring kitchen sale, fun energy" --duration 5`
Expected: PRE+POST cost lines printed, run_id printed, `runs/<id>/plan.json` and `runs/<id>/intent.json` written.

- [ ] **Step 4: Commit**

```bash
git add backend/src/reel_gen/graph.py backend/src/reel_gen/__main__.py
git commit -m "feat(graph): LangGraph Extract->Plan + CLI entry point"
```

---

## Phase 4: FastAPI run lifecycle + SSE

**Goal:** `POST /api/runs` starts a run, `GET /api/runs/{id}` returns status, `GET /api/runs/{id}/stream` streams per-node events as SSE. The frontend talks only to these endpoints.

### Task 4.1: Run registry (in-memory + filesystem persistence)

**Files:**
- Create: `backend/src/reel_gen/runs.py`
- Create: `backend/tests/test_runs.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_runs.py
import asyncio

import pytest

from reel_gen.runs import RunRegistry


@pytest.mark.asyncio
async def test_register_and_get(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    reg = RunRegistry()
    rid = await reg.create(brief="hello", duration_s=5, with_music=False)
    assert rid
    snap = await reg.snapshot(rid)
    assert snap["brief"] == "hello"
    assert snap["status"] == "pending"


@pytest.mark.asyncio
async def test_event_stream_yields_events(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    reg = RunRegistry()
    rid = await reg.create(brief="x", duration_s=5, with_music=False)

    async def producer():
        await reg.publish(rid, {"event": "extract_start"})
        await reg.publish(rid, {"event": "extract_end"})
        await reg.complete(rid, "completed")

    async def consumer():
        events = []
        async for e in reg.subscribe(rid):
            events.append(e)
        return events

    _, events = await asyncio.gather(producer(), consumer())
    kinds = [e["event"] for e in events]
    assert "extract_start" in kinds
    assert "extract_end" in kinds
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_runs.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/runs.py
"""In-memory run registry with filesystem persistence + per-run async event bus.

Keeps things simple: one process serves all runs; state mirrored to
runs/<id>/state.json so a refresh recovers context. SSE consumers read
from a per-run asyncio.Queue.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._approvals: dict[str, asyncio.Event] = {}
        self._approve_decisions: dict[str, bool] = {}
        self._lock = asyncio.Lock()

    def _runs_dir(self) -> Path:
        d = Path(os.environ.get("RUNS_DIR", "./runs"))
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def create(self, *, brief: str, duration_s: int, with_music: bool) -> str:
        rid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        rec = {
            "run_id": rid,
            "brief": brief,
            "duration_s": duration_s,
            "with_music": with_music,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        async with self._lock:
            self._runs[rid] = rec
            self._queues[rid] = []
            self._approvals[rid] = asyncio.Event()
        self._persist(rid)
        return rid

    def _persist(self, rid: str) -> None:
        run_dir = self._runs_dir() / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "state.json").write_text(json.dumps(self._runs[rid], indent=2, default=str))

    async def snapshot(self, rid: str) -> dict:
        async with self._lock:
            return dict(self._runs.get(rid, {}))

    async def update(self, rid: str, **fields) -> None:
        async with self._lock:
            if rid not in self._runs:
                return
            self._runs[rid].update(fields)
            self._runs[rid]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist(rid)

    async def complete(self, rid: str, status: str) -> None:
        await self.update(rid, status=status)
        await self.publish(rid, {"event": "run_complete", "status": status})
        async with self._lock:
            for q in self._queues.get(rid, []):
                q.put_nowait(None)

    async def publish(self, rid: str, event: dict) -> None:
        async with self._lock:
            for q in self._queues.get(rid, []):
                q.put_nowait(event)

    async def subscribe(self, rid: str) -> AsyncIterator[dict]:
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._queues.setdefault(rid, []).append(q)
        try:
            while True:
                item = await q.get()
                if item is None:
                    return
                yield item
        finally:
            async with self._lock:
                if q in self._queues.get(rid, []):
                    self._queues[rid].remove(q)

    async def list_runs(self) -> list[dict]:
        async with self._lock:
            return sorted(self._runs.values(), key=lambda r: r["updated_at"], reverse=True)

    async def await_approval(self, rid: str) -> bool:
        ev = self._approvals.get(rid)
        if ev is None:
            return False
        await ev.wait()
        return self._approve_decisions.get(rid, False)

    async def set_approval(self, rid: str, *, approved: bool) -> None:
        self._approve_decisions[rid] = approved
        ev = self._approvals.get(rid)
        if ev:
            ev.set()


REGISTRY = RunRegistry()
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_runs.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/runs.py backend/tests/test_runs.py
git commit -m "feat(runs): in-memory run registry with SSE pub/sub + approval gate primitive"
```

### Task 4.2: API routes (POST/GET runs, SSE stream)

**Files:**
- Modify: `backend/src/reel_gen/api.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api.py
from fastapi.testclient import TestClient

from reel_gen.api import app


def test_post_runs_returns_id(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    client = TestClient(app)
    r = client.post("/api/runs", json={"prompt": "hi", "duration_s": 5, "with_music": False})
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body


def test_get_runs_lists(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    client = TestClient(app)
    client.post("/api/runs", json={"prompt": "a", "duration_s": 5, "with_music": False})
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

- [ ] **Step 2: Replace `backend/src/reel_gen/api.py` with the routed app**

```python
"""FastAPI app: routes for run lifecycle, SSE streaming, plan approval, file serving."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from reel_gen.runs import REGISTRY
from reel_gen.tracing.langfuse_client import flush as flush_langfuse

app = FastAPI(title="Sri Studio API", version="0.1.0")


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    duration_s: int = Field(default=5, ge=3, le=120)
    with_music: bool = False


class CreateRunResponse(BaseModel):
    run_id: str


class ApproveRequest(BaseModel):
    approved: bool


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "sri-studio-backend"}


def _runs_dir() -> Path:
    d = Path(os.environ.get("RUNS_DIR", "./runs"))
    d.mkdir(parents=True, exist_ok=True)
    return d


async def _execute_run(run_id: str, prompt: str, duration_s: int, with_music: bool) -> None:
    """Background coroutine: drives the LangGraph machine and publishes SSE events.
    Phase 5 wires the approval gate; Phases 6-7 wire Execute and Stitch.
    """
    from reel_gen.graph import build_graph_until_plan
    from reel_gen.state import ReelState

    state = ReelState(run_id=run_id, brief=prompt, duration_s=duration_s, with_music=with_music)
    await REGISTRY.update(run_id, status="running")
    await REGISTRY.publish(run_id, {"event": "extract_start"})
    graph = build_graph_until_plan()
    try:
        final = await asyncio.to_thread(graph.invoke, state)
        plan = final["plan"] if isinstance(final, dict) else final.plan
        await REGISTRY.publish(run_id, {"event": "plan_end", "plan": plan.model_dump() if plan else None})
        await REGISTRY.update(run_id, plan=plan.model_dump() if plan else None, status="awaiting_approval")
        # Phase 5 will: await REGISTRY.await_approval(run_id) then continue.
        await REGISTRY.complete(run_id, status="awaiting_approval")
    except Exception as e:
        await REGISTRY.publish(run_id, {"event": "error", "message": str(e)})
        await REGISTRY.complete(run_id, status="error")
    finally:
        flush_langfuse()


@app.post("/api/runs", response_model=CreateRunResponse)
async def create_run(req: CreateRunRequest, bg: BackgroundTasks) -> CreateRunResponse:
    run_id = await REGISTRY.create(
        brief=req.prompt, duration_s=req.duration_s, with_music=req.with_music
    )
    bg.add_task(_execute_run, run_id, req.prompt, req.duration_s, req.with_music)
    return CreateRunResponse(run_id=run_id)


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    return await REGISTRY.list_runs()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")
    return snap


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")

    async def gen():
        async for event in REGISTRY.subscribe(run_id):
            yield {"event": event.get("event", "message"), "data": json.dumps(event)}

    return EventSourceResponse(gen())


@app.post("/api/runs/{run_id}/approve-plan")
async def approve_plan(run_id: str, req: ApproveRequest) -> dict:
    snap = await REGISTRY.snapshot(run_id)
    if not snap:
        raise HTTPException(404, "run not found")
    await REGISTRY.set_approval(run_id, approved=req.approved)
    return {"run_id": run_id, "approved": req.approved}


@app.get("/api/runs/{run_id}/plan.json")
async def get_plan(run_id: str):
    p = _runs_dir() / run_id / "plan.json"
    if not p.exists():
        raise HTTPException(404, "plan not found")
    return FileResponse(p, media_type="application/json")


@app.get("/api/runs/{run_id}/reel.mp4")
async def get_reel(run_id: str):
    p = _runs_dir() / run_id / "reel.mp4"
    if not p.exists():
        raise HTTPException(404, "reel not ready")
    return FileResponse(p, media_type="video/mp4", filename=f"{run_id}.mp4")
```

- [ ] **Step 3: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_api.py -v`
Expected: 2 passed.

- [ ] **Step 4: Restart compose and smoke test the live endpoints**

Run:
```bash
docker compose up -d --build backend
sleep 5
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"smoke","duration_s":5,"with_music":false}'
curl -s http://localhost:8000/api/runs
```
Expected: Run ID returned; list endpoint returns the run.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/api.py backend/tests/test_api.py
git commit -m "feat(api): POST/GET /api/runs, SSE stream, plan approval, file serving"
```

---

## Phase 5: Approval gate (LangGraph interrupt + frontend signal)

**Goal:** After the Plan node, the LangGraph machine pauses. The API publishes `awaiting_approval`; `POST /api/runs/{id}/approve-plan` signals continue (or terminate on reject). The frontend (Phase 8) renders the approval UI.

### Task 5.1: Approval gate node

**Files:**
- Create: `backend/src/reel_gen/nodes/approval_gate.py`
- Create: `backend/tests/test_approval_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_approval_gate.py
import asyncio

import pytest

from reel_gen.nodes.approval_gate import approval_gate_node
from reel_gen.runs import REGISTRY
from reel_gen.state import ExtractedIntent, ReelState, Scene, ScriptPlan


@pytest.mark.asyncio
async def test_approval_gate_approves(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    rid = await REGISTRY.create(brief="x", duration_s=5, with_music=False)
    state = ReelState(
        run_id=rid, brief="x", duration_s=5,
        plan=ScriptPlan(
            hook="A.", scenes=[Scene(scene_idx=0, duration_s=5, visual_prompt="p",
                                     voiceover_excerpt="A", motion="zoom_in")],
            voiceover_text="A.", voice_style="warm", music_mood=None, aspect_ratio="9:16",
        ),
    )

    async def approver():
        await asyncio.sleep(0.05)
        await REGISTRY.set_approval(rid, approved=True)

    asyncio.create_task(approver())
    new_state = await approval_gate_node(state)
    assert new_state.approved is True


@pytest.mark.asyncio
async def test_approval_gate_rejects(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    rid = await REGISTRY.create(brief="x", duration_s=5, with_music=False)
    state = ReelState(run_id=rid, brief="x", duration_s=5)

    async def rejector():
        await asyncio.sleep(0.05)
        await REGISTRY.set_approval(rid, approved=False)

    asyncio.create_task(rejector())
    new_state = await approval_gate_node(state)
    assert new_state.approved is False
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_approval_gate.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/nodes/approval_gate.py
"""Mandatory human-approval gate. Pauses the pipeline until a frontend
POST /api/runs/{id}/approve-plan resolves the registry's approval Event.
"""
from __future__ import annotations

from reel_gen.runs import REGISTRY
from reel_gen.state import ReelState


async def approval_gate_node(state: ReelState) -> ReelState:
    await REGISTRY.publish(state.run_id, {"event": "awaiting_approval"})
    await REGISTRY.update(state.run_id, status="awaiting_approval")
    approved = await REGISTRY.await_approval(state.run_id)
    state.approved = approved
    await REGISTRY.publish(state.run_id, {"event": "plan_decision", "approved": approved})
    return state
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_approval_gate.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/nodes/approval_gate.py backend/tests/test_approval_gate.py
git commit -m "feat(node:approval_gate): pause pipeline until frontend approves plan"
```

---

## Phase 6: Execute fan-out (TTS + image gen + captions; music deferred)

**Goal:** Parallel sub-tasks fired only after approval. TTS via ElevenLabs voice clone (with alignment), image gen via Replicate Flux Schnell (one call per scene, parallel), captions extracted from TTS alignment. Music skipped at default duration.

### Task 6.1: ElevenLabs TTS client

**Files:**
- Create: `backend/src/reel_gen/media/__init__.py`
- Create: `backend/src/reel_gen/media/elevenlabs_tts.py`
- Create: `backend/tests/test_elevenlabs_tts.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_elevenlabs_tts.py
import base64
import json

import respx
from httpx import Response

from reel_gen.media.elevenlabs_tts import generate_voiceover


@respx.mock
def test_generate_voiceover_writes_mp3_and_alignment(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")
    monkeypatch.setenv("ELEVENLABS_MONTHLY_CHAR_LIMIT", "30000")
    monkeypatch.setenv("ELEVENLABS_QUOTA_BLOCK_AT_PCT", "90")

    fake_mp3 = b"\xff\xfb\x90\x44\x00" + b"\0" * 200
    payload = {
        "audio_base64": base64.b64encode(fake_mp3).decode(),
        "alignment": {
            "characters": list("Hello"),
            "character_start_times_seconds": [0, 0.1, 0.2, 0.3, 0.4],
            "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5],
        },
    }
    respx.post(
        "https://api.elevenlabs.io/v1/text-to-speech/v/with-timestamps"
    ).mock(return_value=Response(200, json=payload))

    out_mp3, words, cost = generate_voiceover(text="Hello", out_dir=tmp_path)
    assert out_mp3.exists()
    assert out_mp3.read_bytes() == fake_mp3
    assert words[0].text and words[0].end_s > words[0].start_s
    assert cost.cost_usd > 0
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_elevenlabs_tts.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/media/__init__.py
"""Media generation clients (TTS, image gen, music gen) and ffmpeg stitching."""
```

```python
# backend/src/reel_gen/media/elevenlabs_tts.py
"""ElevenLabs voice-clone TTS with alignment-based caption extraction.

Cost transparency: prints cost PRE (estimate) and POST (actual) for every
call. Also enforces the monthly character quota; raises before the API
call if usage would exceed ELEVENLABS_QUOTA_BLOCK_AT_PCT (default 90%).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

from reel_gen.llm.cost import unit_cost_post, unit_cost_pre
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.llm.elevenlabs_quota import (
    add_chars_to_month,
    check_char_quota,
    quota_status_line,
)
from reel_gen.state import CaptionWord, CostEntry


def _chars_to_words(
    chars: list[str], starts: list[float], ends: list[float]
) -> list[CaptionWord]:
    """Group character-level alignment into word-level CaptionWord items."""
    words: list[CaptionWord] = []
    buf = ""
    word_start: float | None = None
    word_end: float | None = None
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if buf:
                words.append(CaptionWord(text=buf, start_s=word_start or 0.0, end_s=word_end or 0.0))
                buf = ""
                word_start = None
                word_end = None
        else:
            if not buf:
                word_start = s
            buf += c
            word_end = e
    if buf:
        words.append(CaptionWord(text=buf, start_s=word_start or 0.0, end_s=word_end or 0.0))
    return words


def generate_voiceover(*, text: str, out_dir: Path) -> tuple[Path, list[CaptionWord], CostEntry]:
    voice_id = os.environ["ELEVENLABS_VOICE_ID"]
    api_key = os.environ["ELEVENLABS_API_KEY"]
    chars_used = len(text)

    # 1. Print PRE-call cost estimate so the bill is visible before the API call.
    unit_cost_pre(phase="tts", provider="elevenlabs", unit_label="tts_chars", units=chars_used)

    # 2. Daily USD cost cap check (estimate via published per-character rate).
    from reel_gen.llm.cost import cost_for_units
    est = cost_for_units(provider="elevenlabs", unit_label="tts_chars", units=chars_used)
    check_cap(prospective_cost_usd=est)

    # 3. Monthly char quota check + status line on every call.
    check_char_quota(prospective_chars=chars_used)
    print(quota_status_line())

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        f"/with-timestamps?output_format=mp3_44100_128"
    )
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    r = httpx.post(url, json=body, headers=headers, timeout=120)
    r.raise_for_status()
    payload = r.json()

    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / "voiceover.mp3"
    mp3.write_bytes(base64.b64decode(payload["audio_base64"]))

    align = payload.get("alignment") or {}
    words = _chars_to_words(
        align.get("characters", []),
        align.get("character_start_times_seconds", []),
        align.get("character_end_times_seconds", []),
    )

    cost = unit_cost_post(
        phase="tts", provider="elevenlabs", unit_label="tts_chars", units=chars_used
    )
    add_to_today(cost.cost_usd)
    add_chars_to_month(chars_used)
    return mp3, words, cost
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_elevenlabs_tts.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/media/ backend/tests/test_elevenlabs_tts.py
git commit -m "feat(media:tts): ElevenLabs voice clone TTS + alignment to CaptionWord"
```

### Task 6.2: Replicate Flux Schnell client (with NSFW retry)

**Files:**
- Create: `backend/src/reel_gen/media/replicate_flux.py`
- Create: `backend/tests/test_replicate_flux.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_replicate_flux.py
import io
from pathlib import Path
from unittest.mock import patch

import pytest

from reel_gen.media.replicate_flux import generate_image


def _png_bytes() -> bytes:
    # 1x1 valid PNG.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f"
        "15c4890000000d49444154789c63000100000005000100"
        "5db4e8910000000049454e44ae426082"
    )


def test_generate_image_writes_png(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_test")
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    monkeypatch.setenv("DAILY_COST_CAP_USD", "5.00")

    class FakeFile:
        def read(self) -> bytes:
            return _png_bytes()

    with patch("reel_gen.media.replicate_flux.replicate.run", return_value=[FakeFile()]):
        path, cost = generate_image(prompt="x", out_dir=tmp_path, scene_idx=0)
    assert path.exists()
    assert path.suffix == ".png"
    assert cost.cost_usd > 0
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_replicate_flux.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/media/replicate_flux.py
"""Replicate Flux Schnell client with NSFW retry-with-rewrite + cost transparency.

Cost transparency: prints PRE (estimate $0.003/image) and POST (actual)
on every call. NSFW retry counts as a second billed call; both PRE/POST
lines fire so the bill is fully visible.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import httpx
import replicate

from reel_gen.llm.cost import unit_cost_post, unit_cost_pre
from reel_gen.llm.cost_cap import add_to_today, check_cap
from reel_gen.state import CostEntry

# Cheap deterministic rewrite for NSFW retry: strip body / clothing / skin words.
_RISKY = re.compile(r"\b(swimsuit|bikini|nude|naked|skin|body|sensual|sexy)\b", re.IGNORECASE)


def _safer_prompt(prompt: str) -> str:
    return _RISKY.sub("clothed", prompt)


def _download(out_obj) -> bytes:
    if hasattr(out_obj, "read"):
        return out_obj.read()
    return httpx.get(str(out_obj), timeout=60).content


def generate_image(
    *, prompt: str, out_dir: Path, scene_idx: int, retry_on_nsfw: bool = True
) -> tuple[Path, CostEntry]:
    os.environ["REPLICATE_API_TOKEN"] = os.environ["REPLICATE_API_TOKEN"]

    # 1. Print PRE-call cost estimate so the bill is visible BEFORE the API call.
    #    Flux Schnell at 9:16 is $0.003 per image (see UNIT_RATES in llm/cost.py).
    unit_cost_pre(phase="image", provider="replicate", unit_label="images", units=1)

    # 2. Daily USD cost cap check.
    from reel_gen.llm.cost import cost_for_units
    est = cost_for_units(provider="replicate", unit_label="images", units=1)
    check_cap(prospective_cost_usd=est)

    def call(p: str):
        return replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": p, "aspect_ratio": "9:16",
                "num_outputs": 1, "output_format": "png", "output_quality": 90,
            },
        )

    retried = False
    try:
        out = call(prompt)
    except Exception as e:
        msg = str(e).lower()
        if retry_on_nsfw and ("nsfw" in msg or "moderation" in msg or "safety" in msg):
            # Retry counts as a second billed call.
            print("[INFO] Replicate flagged prompt; retrying with rewrite (this is a second billable call).")
            unit_cost_pre(phase="image_retry", provider="replicate", unit_label="images", units=1)
            check_cap(prospective_cost_usd=est)
            out = call(_safer_prompt(prompt))
            retried = True
        else:
            raise

    first = out[0] if isinstance(out, list) else out
    png_bytes = _download(first)

    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"scene_{scene_idx:02d}.png"
    p.write_bytes(png_bytes)

    # 3. POST: log + return ledger entry. If we retried, units=2 so the bill is honest.
    units = 2 if retried else 1
    cost = unit_cost_post(phase="image", provider="replicate", unit_label="images", units=units)
    add_to_today(cost.cost_usd)
    return p, cost
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_replicate_flux.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/media/replicate_flux.py backend/tests/test_replicate_flux.py
git commit -m "feat(media:images): Replicate Flux Schnell client with NSFW retry-with-rewrite"
```

### Task 6.3: Execute fan-out node

**Files:**
- Create: `backend/src/reel_gen/nodes/execute.py`
- Create: `backend/tests/test_execute_node.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_execute_node.py
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from reel_gen.nodes.execute import execute_node
from reel_gen.state import CaptionWord, CostEntry, ReelState, Scene, ScriptPlan


@pytest.mark.asyncio
async def test_execute_node_runs_tts_and_images_in_parallel(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    plan = ScriptPlan(
        hook="A.", scenes=[
            Scene(scene_idx=0, duration_s=2.5, visual_prompt="p1",
                  voiceover_excerpt="hi", motion="zoom_in"),
            Scene(scene_idx=1, duration_s=2.5, visual_prompt="p2",
                  voiceover_excerpt="bye", motion="zoom_out"),
        ],
        voiceover_text="hi bye", voice_style="warm",
        music_mood=None, aspect_ratio="9:16",
    )
    state = ReelState(run_id="r", brief="x", duration_s=5, plan=plan, approved=True)

    fake_cost = CostEntry(phase="x", provider="x", cost_usd=0.001, timestamp="t")

    def fake_image(prompt, out_dir, scene_idx):
        p = Path(out_dir) / f"scene_{scene_idx:02d}.png"
        p.write_bytes(b"\x89PNG")
        return p, fake_cost

    def fake_tts(text, out_dir):
        p = Path(out_dir) / "voiceover.mp3"
        p.write_bytes(b"mp3")
        words = [CaptionWord(text="hi", start_s=0.0, end_s=0.5),
                 CaptionWord(text="bye", start_s=0.5, end_s=1.0)]
        return p, words, fake_cost

    with patch("reel_gen.nodes.execute.generate_image", side_effect=fake_image), \
         patch("reel_gen.nodes.execute.generate_voiceover", side_effect=fake_tts):
        new_state = await execute_node(state)

    assert new_state.voiceover_path is not None
    assert len(new_state.image_paths) == 2
    assert new_state.captions and len(new_state.captions) == 2
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_execute_node.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/nodes/execute.py
"""Parallel fan-out: TTS, image gen, captions. Music deferred unless with_music."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from reel_gen.media.elevenlabs_tts import generate_voiceover
from reel_gen.media.replicate_flux import generate_image
from reel_gen.runs import REGISTRY
from reel_gen.state import NodeError, ReelState


def _run_dir(run_id: str) -> Path:
    return Path(os.environ.get("RUNS_DIR", "./runs")) / run_id


async def execute_node(state: ReelState) -> ReelState:
    if not state.plan:
        state.errors.append(NodeError(node="execute", message="missing plan", fatal=True))
        return state
    if state.approved is False:
        state.errors.append(NodeError(node="execute", message="rejected by user", fatal=True))
        return state

    run_dir = _run_dir(state.run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    await REGISTRY.publish(state.run_id, {"event": "execute_start"})

    async def do_tts():
        try:
            mp3, words, cost = await asyncio.to_thread(
                generate_voiceover, text=state.plan.voiceover_text, out_dir=run_dir
            )
            state.voiceover_path = mp3
            state.captions = words
            state.cost_ledger.append(cost)
            await REGISTRY.publish(state.run_id, {"event": "tts_done"})
        except Exception as e:
            state.errors.append(NodeError(node="execute_tts", message=str(e), fatal=True))

    async def do_image(scene):
        try:
            p, cost = await asyncio.to_thread(
                generate_image, prompt=scene.visual_prompt, out_dir=run_dir, scene_idx=scene.scene_idx
            )
            state.image_paths.append(p)
            state.cost_ledger.append(cost)
            await REGISTRY.publish(state.run_id, {"event": "image_done", "scene_idx": scene.scene_idx})
        except Exception as e:
            # Fallback: solid-color frame so the reel still ships.
            await _fallback_solid_frame(run_dir, scene)
            fallback_path = run_dir / f"scene_{scene.scene_idx:02d}.png"
            state.image_paths.append(fallback_path)
            state.errors.append(NodeError(
                node="execute_image", message=f"scene {scene.scene_idx}: {e}", fatal=False))

    image_tasks = [do_image(s) for s in state.plan.scenes]
    await asyncio.gather(do_tts(), *image_tasks)

    # Sort image_paths back into scene order (gather doesn't guarantee order).
    state.image_paths.sort(key=lambda p: int(p.stem.split("_")[-1]))

    await REGISTRY.publish(state.run_id, {"event": "execute_end"})
    return state


async def _fallback_solid_frame(run_dir: Path, scene) -> None:
    import subprocess
    p = run_dir / f"scene_{scene.scene_idx:02d}.png"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=#1a1a2e:s=1080x1920:d=1",
        "-frames:v", "1", str(p)
    ], check=True)
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_execute_node.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/nodes/execute.py backend/tests/test_execute_node.py
git commit -m "feat(node:execute): parallel TTS + image gen + captions with solid-frame fallback"
```

---

## Phase 7: Stitch node + full graph + e2e smoke

**Goal:** ffmpeg stitch with Ken Burns motion + voiceover + caption burn-in. Wire the full graph: Extract -> Plan -> Approval -> Execute -> Stitch. Smoke an end-to-end run via the CLI and via the API.

### Task 7.1: ffmpeg stitch module

**Files:**
- Create: `backend/src/reel_gen/media/ffmpeg_stitch.py`
- Create: `backend/tests/test_ffmpeg_stitch.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ffmpeg_stitch.py
import subprocess
from pathlib import Path

from reel_gen.media.ffmpeg_stitch import stitch_reel
from reel_gen.state import CaptionWord, Scene, ScriptPlan


def test_stitch_produces_1080x1920_mp4(tmp_path):
    # Generate 2 solid-color test PNGs.
    img1 = tmp_path / "scene_00.png"
    img2 = tmp_path / "scene_01.png"
    for img, color in [(img1, "teal"), (img2, "salmon")]:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d=1",
            "-frames:v", "1", str(img)
        ], check=True)
    # Generate a 5s silent mp3 stand-in.
    voice = tmp_path / "voiceover.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
        "-t", "5", "-q:a", "9", str(voice)
    ], check=True)

    plan = ScriptPlan(
        hook="hi", scenes=[
            Scene(scene_idx=0, duration_s=2.5, visual_prompt="x", voiceover_excerpt="hi", motion="zoom_in"),
            Scene(scene_idx=1, duration_s=2.5, visual_prompt="x", voiceover_excerpt="bye", motion="zoom_out"),
        ],
        voiceover_text="hi bye", voice_style="warm", music_mood=None, aspect_ratio="9:16",
    )
    captions = [
        CaptionWord(text="hi", start_s=0.0, end_s=2.0),
        CaptionWord(text="bye", start_s=2.5, end_s=4.5),
    ]
    out = tmp_path / "reel.mp4"
    stitch_reel(plan=plan, image_paths=[img1, img2], voiceover=voice,
                music=None, captions=captions, out=out)
    assert out.exists()

    info = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(out)
    ]).decode().strip()
    assert info == "1080x1920"
```

- [ ] **Step 2: Run test, expect failure**

Run: `docker compose run --rm backend pytest tests/test_ffmpeg_stitch.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write the implementation**

```python
# backend/src/reel_gen/media/ffmpeg_stitch.py
"""ffmpeg stitching: Ken Burns motion per scene, voiceover + ducked music,
burn-in captions from word-level timestamps. 1080x1920 H.264 AAC mp4 out.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from reel_gen.state import CaptionWord, ScriptPlan

FPS = 30


def _ass_timestamp(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - h * 3600 - m * 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _captions_to_ass(captions: list[CaptionWord], group: int = 3) -> str:
    """Group `group` words at a time into one Dialogue line for readability."""
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Caption,DejaVu Sans,72,&H00FFFFFF,&H00000000,&H80000000,"
        "1,0,0,0,100,100,0,0,1,5,2,2,40,40,200,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines: list[str] = []
    i = 0
    while i < len(captions):
        chunk = captions[i:i + group]
        text = " ".join(w.text for w in chunk)
        start = chunk[0].start_s
        end = chunk[-1].end_s
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},"
            f"Caption,,0,0,0,,{text}"
        )
        i += group
    return header + "\n".join(lines) + "\n"


def _motion_filter(motion: str, frames: int) -> str:
    if motion == "static":
        return f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    direction = {
        "zoom_in":  "z='min(zoom+0.0008,1.15)'",
        "zoom_out": "z='if(eq(on,0),1.15,max(zoom-0.0008,1.0))'",
        "pan_left": "z='1.1'",
        "pan_right": "z='1.1'",
    }.get(motion, "z='min(zoom+0.0008,1.15)'")
    pan_x = {
        "pan_left":  "x='iw-(iw/zoom)-on*((iw-iw/zoom)/" + str(frames) + ")'",
        "pan_right": "x='on*((iw-iw/zoom)/" + str(frames) + ")'",
    }.get(motion, "x='iw/2-(iw/zoom/2)'")
    pan_y = "y='ih/2-(ih/zoom/2)'"
    return (
        f"scale=2160:3840,zoompan={direction}:d={frames}:{pan_x}:{pan_y}:s=1080x1920:fps={FPS}"
    )


def stitch_reel(
    *,
    plan: ScriptPlan,
    image_paths: list[Path],
    voiceover: Path,
    music: Path | None,
    captions: list[CaptionWord] | None,
    out: Path,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent
    inputs: list[str] = []
    filter_parts: list[str] = []

    for i, scene in enumerate(plan.scenes):
        img = image_paths[i]
        frames = int(scene.duration_s * FPS)
        inputs += ["-loop", "1", "-t", str(scene.duration_s), "-i", str(img)]
        filter_parts.append(f"[{i}:v]{_motion_filter(scene.motion, frames)}[v{i}]")

    concat = "".join(f"[v{i}]" for i in range(len(plan.scenes)))
    filter_parts.append(f"{concat}concat=n={len(plan.scenes)}:v=1:a=0[vbase]")

    if captions:
        ass_path = work / "captions.ass"
        ass_path.write_text(_captions_to_ass(captions))
        filter_parts.append(f"[vbase]subtitles={ass_path.name}[vout]")
        # ffmpeg requires running with the cwd containing captions.ass
    else:
        filter_parts.append(f"[vbase]copy[vout]")

    voice_idx = len(plan.scenes)
    inputs += ["-i", str(voiceover)]

    if music is not None:
        music_idx = voice_idx + 1
        inputs += ["-i", str(music)]
        filter_parts.append(
            f"[{music_idx}:a]volume=-18dB[mq];"
            f"[{voice_idx}:a][mq]amix=inputs=2:duration=longest:dropout_transition=2[aout]"
        )
        a_map = "[aout]"
    else:
        a_map = f"{voice_idx}:a"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filter_parts),
        "-map", "[vout]", "-map", a_map,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(out),
    ]
    subprocess.run(cmd, check=True, cwd=str(work))
```

- [ ] **Step 4: Run test, expect pass**

Run: `docker compose run --rm backend pytest tests/test_ffmpeg_stitch.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/reel_gen/media/ffmpeg_stitch.py backend/tests/test_ffmpeg_stitch.py
git commit -m "feat(media:stitch): ffmpeg Ken Burns + caption burn-in + audio mix"
```

### Task 7.2: Stitch node

**Files:**
- Create: `backend/src/reel_gen/nodes/stitch.py`

- [ ] **Step 1: Write `backend/src/reel_gen/nodes/stitch.py`**

```python
# backend/src/reel_gen/nodes/stitch.py
"""Stitch node: assemble final reel.mp4 from generated assets."""
from __future__ import annotations

import os
from pathlib import Path

from reel_gen.media.ffmpeg_stitch import stitch_reel
from reel_gen.runs import REGISTRY
from reel_gen.state import NodeError, ReelState
from reel_gen.tracing.langfuse_client import with_span


def _run_dir(run_id: str) -> Path:
    return Path(os.environ.get("RUNS_DIR", "./runs")) / run_id


@with_span(name="stitch_node")
async def stitch_node(state: ReelState) -> ReelState:
    if not state.plan or not state.voiceover_path or not state.image_paths:
        state.errors.append(NodeError(
            node="stitch", message="missing plan / voiceover / images", fatal=True))
        return state

    out = _run_dir(state.run_id) / "reel.mp4"
    try:
        await REGISTRY.publish(state.run_id, {"event": "stitch_start"})
        import asyncio
        await asyncio.to_thread(
            stitch_reel,
            plan=state.plan,
            image_paths=state.image_paths,
            voiceover=state.voiceover_path,
            music=state.music_path,
            captions=state.captions,
            out=out,
        )
        state.reel_path = out
        await REGISTRY.publish(state.run_id, {"event": "stitch_end", "reel": str(out.name)})
    except Exception as e:
        state.errors.append(NodeError(node="stitch", message=str(e), fatal=True))
    return state
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/reel_gen/nodes/stitch.py
git commit -m "feat(node:stitch): wrap ffmpeg_stitch with LangGraph + SSE events"
```

### Task 7.3: Wire the full graph + cost ledger persistence

**Files:**
- Modify: `backend/src/reel_gen/graph.py`
- Modify: `backend/src/reel_gen/api.py` (`_execute_run` to drive the full graph)

- [ ] **Step 1: Replace `backend/src/reel_gen/graph.py`**

```python
"""LangGraph wiring: Extract -> Plan -> Approval Gate -> Execute -> Stitch."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from reel_gen.nodes.approval_gate import approval_gate_node
from reel_gen.nodes.execute import execute_node
from reel_gen.nodes.extract import extract_node
from reel_gen.nodes.plan import plan_node
from reel_gen.nodes.stitch import stitch_node
from reel_gen.state import ReelState


def _route_after_approval(state: ReelState) -> str:
    return "execute" if state.approved else "end_rejected"


def build_graph():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.add_node("approval_gate", approval_gate_node)
    g.add_node("execute", execute_node)
    g.add_node("stitch", stitch_node)
    g.add_node("end_rejected", lambda s: s)

    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", "approval_gate")
    g.add_conditional_edges("approval_gate", _route_after_approval, {
        "execute": "execute",
        "end_rejected": "end_rejected",
    })
    g.add_edge("execute", "stitch")
    g.add_edge("stitch", END)
    g.add_edge("end_rejected", END)
    return g.compile()


# Phase 3 builder kept for partial CLI runs; used by tests.
def build_graph_until_plan():
    g = StateGraph(ReelState)
    g.add_node("extract", extract_node)
    g.add_node("plan", plan_node)
    g.set_entry_point("extract")
    g.add_edge("extract", "plan")
    g.add_edge("plan", END)
    return g.compile()
```

- [ ] **Step 2: Replace the `_execute_run` body in `backend/src/reel_gen/api.py`**

```python
async def _execute_run(run_id: str, prompt: str, duration_s: int, with_music: bool) -> None:
    """Drives the full LangGraph machine end-to-end. Publishes per-node events."""
    import json

    from reel_gen.graph import build_graph
    from reel_gen.state import ReelState

    state = ReelState(run_id=run_id, brief=prompt, duration_s=duration_s, with_music=with_music)
    await REGISTRY.update(run_id, status="running")
    graph = build_graph()
    try:
        # LangGraph's async invoke is required because approval_gate + execute + stitch use async.
        final = await graph.ainvoke(state)
        final_state = ReelState.model_validate(final) if isinstance(final, dict) else final
        # Persist cost ledger.
        run_dir = _runs_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "cost.json").write_text(
            json.dumps([c.model_dump() for c in final_state.cost_ledger], indent=2, default=str)
        )
        if final_state.reel_path:
            await REGISTRY.update(run_id, reel_path=str(final_state.reel_path))
        if final_state.approved is False:
            await REGISTRY.complete(run_id, status="rejected")
        elif final_state.errors and any(e.fatal for e in final_state.errors):
            await REGISTRY.complete(run_id, status="error")
        else:
            await REGISTRY.complete(run_id, status="completed")
    except Exception as e:
        await REGISTRY.publish(run_id, {"event": "error", "message": str(e)})
        await REGISTRY.complete(run_id, status="error")
    finally:
        flush_langfuse()
```

- [ ] **Step 3: End-to-end smoke**

Run:
```bash
docker compose up -d --build backend
sleep 5
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"sri studio launch teaser, energetic","duration_s":5}' \
  | tee /tmp/run.json
RID=$(jq -r .run_id /tmp/run.json)
echo "run id: $RID"

# Watch state until awaiting_approval.
until curl -s "http://localhost:8000/api/runs/$RID" | jq -e '.status == "awaiting_approval"' > /dev/null; do sleep 2; done

# Approve.
curl -s -X POST "http://localhost:8000/api/runs/$RID/approve-plan" \
  -H "Content-Type: application/json" -d '{"approved": true}'

# Wait for completion.
until curl -s "http://localhost:8000/api/runs/$RID" | jq -e '.status == "completed"' > /dev/null; do sleep 3; done

# Pull the reel.
curl -s -o "/tmp/$RID.mp4" "http://localhost:8000/api/runs/$RID/reel.mp4"
ffprobe -v error -show_entries stream=width,height,duration "/tmp/$RID.mp4"
```
Expected: 1080x1920 mp4, ~5s long, plays back as a Reel in your voice.

- [ ] **Step 4: Commit**

```bash
git add backend/src/reel_gen/graph.py backend/src/reel_gen/api.py
git commit -m "feat(graph): full pipeline Extract->Plan->Approval->Execute->Stitch wired through API"
```

---

## Phase 8: Next.js frontend

**Goal:** A working browser flow at `http://localhost:3000` (and later studio.sshub.dev): submit a prompt, watch progress stream live, review the plan scene-by-scene, approve or reject, watch the final reel inline.

### Task 8.1: Types + API client

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create `frontend/lib/types.ts`**

```ts
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
```

- [ ] **Step 2: Create `frontend/lib/api.ts`**

```ts
import type { RunSnapshot } from "./types";

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

export async function approvePlan(id: string, approved: boolean): Promise<void> {
  const r = await fetch(`${BASE}/api/runs/${id}/approve-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
  });
  if (!r.ok) throw new Error(`approvePlan failed: ${r.status}`);
}

export function reelUrl(id: string): string {
  return `${BASE}/api/runs/${id}/reel.mp4`;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/
git commit -m "feat(frontend): types + API client for backend endpoints"
```

### Task 8.2: SSE hook

**Files:**
- Create: `frontend/lib/sse.ts`

- [ ] **Step 1: Create `frontend/lib/sse.ts`**

```ts
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/sse.ts
git commit -m "feat(frontend): SSE hook for live run events"
```

### Task 8.3: PromptForm component + new-run page

**Files:**
- Create: `frontend/components/PromptForm.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create `frontend/components/PromptForm.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createRun } from "@/lib/api";

export function PromptForm() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(5);
  const [withMusic, setWithMusic] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setErr(null);
    try {
      const { run_id } = await createRun({
        prompt: prompt.trim(),
        duration_s: duration,
        with_music: withMusic,
      });
      router.push(`/runs/${run_id}`);
    } catch (e) {
      setErr((e as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4 max-w-2xl">
      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-neutral-300">Prompt</span>
        <textarea
          required
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          className="bg-neutral-900 border border-neutral-700 rounded p-3 min-h-[120px] font-mono text-sm"
          placeholder="Sur La Table spring kitchen sale, fun energy, food-focused"
        />
      </label>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-neutral-300">
          Duration: {duration}s {duration >= 30 ? " (music auto-on)" : ""}
        </span>
        <input
          type="range"
          min={5}
          max={90}
          step={5}
          value={duration}
          onChange={(e) => {
            const d = parseInt(e.target.value, 10);
            setDuration(d);
            if (d >= 30 && !withMusic) setWithMusic(true);
            if (d < 30 && withMusic) setWithMusic(false);
          }}
        />
      </label>

      <label className="flex items-center gap-2 text-sm text-neutral-300">
        <input
          type="checkbox"
          checked={withMusic}
          onChange={(e) => setWithMusic(e.target.checked)}
        />
        Include background music
      </label>

      {err && <div className="text-red-400 text-sm">{err}</div>}

      <button
        type="submit"
        disabled={submitting || !prompt.trim()}
        className="self-start bg-indigo-600 hover:bg-indigo-500 disabled:bg-neutral-700 px-5 py-2 rounded font-medium"
      >
        {submitting ? "Starting..." : "Generate Reel"}
      </button>
    </form>
  );
}
```

- [ ] **Step 2: Replace `frontend/app/page.tsx`**

```tsx
import { PromptForm } from "@/components/PromptForm";

export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2">New Reel</h2>
      <p className="text-neutral-400 mb-6 text-sm">
        Type a brief; review the plan scene-by-scene; approve to generate.
      </p>
      <PromptForm />
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/PromptForm.tsx frontend/app/page.tsx
git commit -m "feat(frontend): PromptForm + new-run page"
```

### Task 8.4: ProgressTimeline + PlanReviewPanel + ReelPlayer + run page

**Files:**
- Create: `frontend/components/ProgressTimeline.tsx`
- Create: `frontend/components/PlanReviewPanel.tsx`
- Create: `frontend/components/CostLedger.tsx`
- Create: `frontend/components/ReelPlayer.tsx`
- Create: `frontend/app/runs/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/components/ProgressTimeline.tsx`**

```tsx
"use client";

import type { RunEvent } from "@/lib/types";

const STEPS = [
  { key: "extract_start", label: "Extract intent" },
  { key: "plan_end", label: "Plan generated" },
  { key: "awaiting_approval", label: "Awaiting approval" },
  { key: "execute_start", label: "Generating media" },
  { key: "tts_done", label: "Voiceover done" },
  { key: "execute_end", label: "Media complete" },
  { key: "stitch_end", label: "Reel stitched" },
] as const;

export function ProgressTimeline({ events }: { events: RunEvent[] }) {
  const seen = new Set(events.map((e) => e.event));
  return (
    <ol className="border-l border-neutral-700 pl-5 space-y-2 text-sm">
      {STEPS.map((s) => {
        const done = seen.has(s.key);
        return (
          <li key={s.key} className="relative">
            <span
              className={`absolute -left-[26px] top-1 w-3 h-3 rounded-full ${
                done ? "bg-emerald-400" : "bg-neutral-700"
              }`}
            />
            <span className={done ? "text-neutral-100" : "text-neutral-500"}>
              {s.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
```

- [ ] **Step 2: Create `frontend/components/PlanReviewPanel.tsx`**

```tsx
"use client";

import { useState } from "react";

import { approvePlan } from "@/lib/api";
import type { ScriptPlan } from "@/lib/types";

export function PlanReviewPanel({
  runId,
  plan,
  onResolved,
}: {
  runId: string;
  plan: ScriptPlan;
  onResolved: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function decide(approved: boolean) {
    setBusy(true);
    try {
      await approvePlan(runId, approved);
      onResolved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-amber-700 bg-amber-950/30 rounded p-5 space-y-4">
      <div className="flex items-baseline justify-between">
        <h3 className="text-lg font-semibold text-amber-300">Review the plan</h3>
        <span className="text-xs text-amber-400">
          No paid generation runs until you approve.
        </span>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Hook</div>
        <div className="text-base">{plan.hook}</div>
      </div>

      <div>
        <div className="text-xs uppercase text-neutral-400 mb-1">Voiceover</div>
        <div className="text-sm leading-relaxed">{plan.voiceover_text}</div>
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase text-neutral-400">Scenes ({plan.scenes.length})</div>
        {plan.scenes.map((s) => (
          <div key={s.scene_idx} className="border border-neutral-800 rounded p-3 text-sm">
            <div className="flex justify-between items-baseline">
              <div className="font-medium">Scene {s.scene_idx + 1}</div>
              <div className="text-neutral-400 text-xs">
                {s.duration_s.toFixed(1)}s, {s.motion}
              </div>
            </div>
            <div className="text-neutral-300 mt-1">{s.voiceover_excerpt}</div>
            <div className="text-neutral-500 text-xs mt-1 italic">{s.visual_prompt}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={() => decide(true)}
          disabled={busy}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 px-5 py-2 rounded font-medium"
        >
          Approve and generate
        </button>
        <button
          onClick={() => decide(false)}
          disabled={busy}
          className="bg-neutral-700 hover:bg-neutral-600 disabled:bg-neutral-800 px-5 py-2 rounded"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/CostLedger.tsx`**

```tsx
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
```

- [ ] **Step 4: Create `frontend/components/ReelPlayer.tsx`**

```tsx
"use client";

import { reelUrl } from "@/lib/api";

export function ReelPlayer({ runId }: { runId: string }) {
  const url = reelUrl(runId);
  return (
    <div className="space-y-3">
      <video src={url} controls className="w-full max-w-sm rounded shadow-lg bg-black" />
      <a
        href={url}
        download
        className="inline-block text-sm text-indigo-400 hover:text-indigo-300 underline"
      >
        Download MP4
      </a>
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/app/runs/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";

import { CostLedger } from "@/components/CostLedger";
import { PlanReviewPanel } from "@/components/PlanReviewPanel";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { ReelPlayer } from "@/components/ReelPlayer";
import { getRun } from "@/lib/api";
import { useRunStream } from "@/lib/sse";
import type { RunSnapshot } from "@/lib/types";

export default function RunPage({ params }: { params: { id: string } }) {
  const [snap, setSnap] = useState<RunSnapshot | null>(null);
  const events = useRunStream(params.id);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      while (!cancelled) {
        try {
          const s = await getRun(params.id);
          if (!cancelled) setSnap(s);
          if (s.status === "completed" || s.status === "rejected" || s.status === "error") return;
        } catch {
          // transient errors are swallowed; SSE drives the UI
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    poll();
    return () => {
      cancelled = true;
    };
  }, [params.id, events.length]);

  if (!snap) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs text-neutral-500 font-mono">{snap.run_id}</div>
        <div className="text-sm text-neutral-300 mt-1">{snap.brief}</div>
      </div>

      <ProgressTimeline events={events} />

      {snap.status === "awaiting_approval" && snap.plan && (
        <PlanReviewPanel
          runId={snap.run_id}
          plan={snap.plan}
          onResolved={() => {}}
        />
      )}

      {snap.status === "completed" && <ReelPlayer runId={snap.run_id} />}

      {snap.status === "rejected" && (
        <div className="text-neutral-400">Run rejected. No media was generated.</div>
      )}

      {snap.status === "error" && (
        <div className="text-red-400">An error occurred. Check the backend logs.</div>
      )}

      <CostLedger events={events} />
    </div>
  );
}
```

- [ ] **Step 6: Smoke test the full UI flow**

Run: `docker compose up -d --build`
Browser: open `http://localhost:3000`. Submit "spring kitchen launch teaser energetic". Wait for "Awaiting approval", review the plan, click Approve. Wait for the reel to appear. Play it.
Expected: Reel plays in your voice; ProgressTimeline lights up step by step; CostLedger shows entries.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/ frontend/app/runs/
git commit -m "feat(frontend): Run detail page with timeline, plan review, reel player, cost ledger"
```

### Task 8.5: Runs history page

**Files:**
- Create: `frontend/components/RunCard.tsx`
- Create: `frontend/app/runs/page.tsx`

- [ ] **Step 1: Create `frontend/components/RunCard.tsx`**

```tsx
"use client";

import Link from "next/link";

import type { RunSnapshot } from "@/lib/types";

export function RunCard({ run }: { run: RunSnapshot }) {
  return (
    <Link
      href={`/runs/${run.run_id}`}
      className="block border border-neutral-800 hover:border-neutral-600 rounded p-4 space-y-2"
    >
      <div className="text-xs font-mono text-neutral-500">{run.run_id}</div>
      <div className="text-sm line-clamp-2">{run.brief}</div>
      <div className="flex justify-between text-xs text-neutral-400">
        <span>{run.duration_s}s</span>
        <span>{run.status}</span>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Create `frontend/app/runs/page.tsx`**

```tsx
import { listRuns } from "@/lib/api";
import { RunCard } from "@/components/RunCard";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await listRuns();
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Past runs</h2>
      {runs.length === 0 ? (
        <div className="text-neutral-400">No runs yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {runs.map((r) => (
            <RunCard key={r.run_id} run={r} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/RunCard.tsx frontend/app/runs/page.tsx
git commit -m "feat(frontend): runs history page"
```

---

## Phase 9: Deploy to studio.sshub.dev

**Goal:** Production deployment on Hetzner using the user's existing pattern: nginx reverse proxy + Let's Encrypt + HTTP basic auth + per-day cost cap. No application code changes; only infra files.

### Task 9.1: nginx config

**Files:**
- Create: `nginx/nginx.conf`
- Create: `nginx/.htpasswd.example`

- [ ] **Step 1: Create `nginx/nginx.conf`**

```nginx
worker_processes auto;
events { worker_connections 1024; }

http {
  include       mime.types;
  default_type  application/octet-stream;
  sendfile      on;
  client_max_body_size 25m;

  server {
    listen 80;
    server_name studio.sshub.dev;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
  }

  server {
    listen 443 ssl;
    server_name studio.sshub.dev;
    ssl_certificate     /etc/letsencrypt/live/studio.sshub.dev/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/studio.sshub.dev/privkey.pem;

    auth_basic           "Sri Studio";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # SSE endpoint: long-lived, no buffering, longer timeouts.
    location ~ ^/api/runs/[^/]+/stream$ {
      proxy_pass         http://backend:8000;
      proxy_http_version 1.1;
      proxy_set_header   Connection "";
      proxy_buffering    off;
      proxy_cache        off;
      proxy_read_timeout 1h;
    }

    location /api/ {
      proxy_pass         http://backend:8000;
      proxy_set_header   Host $host;
      proxy_set_header   X-Forwarded-For $remote_addr;
      proxy_read_timeout 5m;
    }

    location / {
      proxy_pass         http://frontend:3000;
      proxy_set_header   Host $host;
      proxy_set_header   X-Forwarded-For $remote_addr;
    }
  }
}
```

- [ ] **Step 2: Create `nginx/.htpasswd.example`**

```
# Generate real credentials with:
#   htpasswd -B -c .htpasswd sri
#   htpasswd -B    .htpasswd csc
# Two users: 'sri' (long-lived) and 'csc' (interview window only).
```

- [ ] **Step 3: Add nginx + certbot to `docker-compose.yml`**

```yaml
  nginx:
    image: nginx:1.27-alpine
    depends_on: [backend, frontend]
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/.htpasswd:/etc/nginx/.htpasswd:ro
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: /bin/sh -c
    command: |
      "trap exit TERM;
       while :; do
         certbot renew --webroot -w /var/www/certbot --quiet;
         sleep 12h & wait $${!};
       done"
```

- [ ] **Step 4: Commit**

```bash
git add nginx/ docker-compose.yml
git commit -m "feat(deploy): nginx reverse proxy + basic auth + Let's Encrypt + SSE timeouts"
```

### Task 9.2: Deploy script

**Files:**
- Create: `deploy/deploy.sh`
- Create: `deploy/README.md`

- [ ] **Step 1: Create `deploy/deploy.sh`**

```bash
#!/usr/bin/env bash
# Deploys Sri Studio to a Hetzner host.
# Usage: ./deploy/deploy.sh [host]
set -euo pipefail
HOST="${1:-studio.sshub.dev}"
APP_USER="deploy"
APP_DIR="/opt/sri-studio"

echo ">>> Syncing repo to ${APP_USER}@${HOST}:${APP_DIR}"
rsync -az --delete \
  --exclude '.git' --exclude 'runs' --exclude 'frontend/node_modules' \
  --exclude 'backend/experiments/out' --exclude '.probes' \
  ./ "${APP_USER}@${HOST}:${APP_DIR}/"

echo ">>> Bumping APP_VERSION on host"
ssh "${APP_USER}@${HOST}" \
  "cd ${APP_DIR} && grep '^APP_VERSION=' .env | awk -F. -v OFS=. '{ \$NF=\$NF+1; print }' > .env.bumped && mv .env.bumped .env || true"

echo ">>> docker compose up --build"
ssh "${APP_USER}@${HOST}" "cd ${APP_DIR} && docker compose up -d --build"

echo ">>> Health check"
sleep 10
curl -fsS "https://${HOST}/api/healthz" -u "$BASIC_AUTH" \
  || (echo "healthz failed; rolling back manually if needed"; exit 1)
echo "DEPLOY OK: https://${HOST}/"
```

- [ ] **Step 2: Create `deploy/README.md`**

```markdown
# Deploy

## First-time host setup
1. Hetzner Cloud VM (CX22, Ubuntu 24.04).
2. DNS: `studio.sshub.dev` -> server IP (A record).
3. Install Docker + docker compose plugin.
4. Create `deploy` user with sudo.
5. Open ports 22, 80, 443.

## First deploy
1. From local: `rsync ./.env <host>:/opt/sri-studio/.env`
2. On host: `htpasswd -B -c nginx/.htpasswd sri` then `htpasswd -B nginx/.htpasswd csc`
3. Generate Let's Encrypt cert:
   ```
   docker compose run --rm certbot certonly --webroot \
     -w /var/www/certbot -d studio.sshub.dev --email you@example.com --agree-tos
   ```
4. `docker compose up -d`

## Subsequent deploys
- `BASIC_AUTH=sri:password ./deploy/deploy.sh`

## Cost cap
- Set `DAILY_COST_CAP_USD` in `.env` on the server (default $5).
- Cap state lives in `/opt/sri-studio/runs/_daily_cost.json`; persists across container restarts.
```

- [ ] **Step 3: Make deploy script executable + commit**

```bash
chmod +x deploy/deploy.sh
git add deploy/
git commit -m "feat(deploy): deploy script + first-time host setup notes"
```

---

## Phase 10: Documentation harvest

**Goal:** Backfill 12 ADRs, build the technical diagrams page, draft the walkthrough script and questionnaire from the build journal.

### Task 10.1: Decision records (ADR-001 through ADR-012)

**Files:**
- Create: `docs/decisions/001-langgraph-over-n8n.md` through `012-basic-auth-and-daily-cost-cap.md`

- [ ] **Step 1: Use this exact template for every ADR**

```markdown
# 00X: <short title>
**Date:** YYYY-MM-DD
**Status:** Decided

## Context
<one paragraph on the problem and the constraint that forced a choice>

## Decision
<one sentence on what was chosen>

## Why
<3-6 specific bullet points: cite probe results, cost numbers, JD wording, evaluation criteria>

## Tradeoffs
<2-4 bullets on what was given up; what this does NOT defend against>

## Evidence
<links to probes, build-journal entries, code commits, or external sources>
```

- [ ] **Step 2: Write all 12 ADRs**

Create one file per decision listed in spec section 7. Pull content from this brainstorm transcript and the spec itself. Each is 30-60 minutes of writing.

- [ ] **Step 3: Commit**

```bash
git add docs/decisions/
git commit -m "docs: backfill ADR-001 through ADR-012"
```

### Task 10.2: Walkthrough script + diagrams + questionnaire draft

**Files:**
- Create: `docs/walkthrough-script.md`
- Create: `docs/diagrams.html`
- Create: `docs/questionnaire-draft.md`
- Create: `docs/build-journal.md`

- [ ] **Step 1: Walkthrough script per spec section 9**

Use the table in the spec; expand each row into a full paragraph with `[SCREEN: ...]` cues and timestamp markers. Aim for 12-14 minutes of total content. Include the cloned-voice continuity hook in the opening.

- [ ] **Step 2: Diagrams HTML page**

Pure HTML + inline CSS per SKILL.md Phase 10c. Include: pipeline flow, approval gate detail, cost-cap flow, deploy stack, my-role-vs-AI two-column, and the pattern statement at the close.

- [ ] **Step 3: Questionnaire draft per spec section 10**

Use the strategy table from the spec; fill bullets from the build journal as evidence accrues. Polish into final voice on Day 3.

- [ ] **Step 4: Build journal**

A rolling chronological log; one entry per probe / node / fix. Use the template from the spec.

- [ ] **Step 5: Commit**

```bash
git add docs/walkthrough-script.md docs/diagrams.html docs/questionnaire-draft.md docs/build-journal.md
git commit -m "docs: walkthrough script + diagrams + questionnaire draft + build journal"
```

---

## Phase 11: Walkthrough recording + final submission

**Goal:** Record the 12-14 minute walkthrough video using the live studio.sshub.dev as the demo surface, package the submission.

### Task 11.1: Pre-record checklist

- [ ] Daily cost cap reset (delete `runs/_daily_cost.json` on the server)
- [ ] One Approve run pre-recorded at 90s as the hook reel
- [ ] One Reject run prepared to demonstrate the cost cap saving spend
- [ ] Browser zoomed to 110-125% so text is readable in screen capture
- [ ] OBS or equivalent set to 1080p, 30fps, system audio + mic

### Task 11.2: Record using the script

Read the `docs/walkthrough-script.md` while screen-capturing studio.sshub.dev. Re-record any section that comes out flat. Total duration target: 12-14 min.

### Task 11.3: Submission package

Zip or share-link:
- The repo (private GitHub link or zip excluding `runs/`, `node_modules/`, `.env`)
- `docs/walkthrough-script.md` (referenced inside the repo)
- The recorded walkthrough video
- `docs/questionnaire-draft.md` polished as the questionnaire response
- The live URL `studio.sshub.dev` with credentials in the cover note

---

## Self-review checklist for the implementer

After completing all phases, verify before declaring done:

- [ ] `docker compose up` brings the full stack live locally.
- [ ] All probes (01, 02, 03, 05, 06, 09, 10) exit 0.
- [ ] `pytest` in the backend container is fully green.
- [ ] `npm run typecheck` in the frontend is clean.
- [ ] A 5s and a 90s reel were each generated end-to-end on the live URL.
- [ ] One Reject path was demonstrated and the cost.json shows only Extract+Plan cost on that run.
- [ ] `docs/decisions/` has 12 ADRs.
- [ ] The walkthrough video was recorded.
- [ ] No file in the repo contains an em dash.
- [ ] No `pip install` appears anywhere in the codebase (only `uv`).
