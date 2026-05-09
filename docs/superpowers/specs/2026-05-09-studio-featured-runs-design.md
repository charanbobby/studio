# Sri Studio: Featured Runs on the Homepage

**Date:** 2026-05-09
**Author:** Sricharan Sunkara, with Claude Code as thinking partner
**Status:** Approved by user; ready for implementation plan
**Touches:** `studio.sshub.dev` homepage (`/`), backend `/api/featured-runs` (new), frontend `FeaturedRuns` component (new)

---

## 1. Goal

Surface a small row of "good runs" at the top of the studio.sshub.dev homepage so first-time visitors see what the system actually produces before they land on the prompt form. One slot is reserved for a permanently-pinned introduction reel (run `05821f3a380d`); the other two slots auto-fill with the newest runs the user has marked `would_ship=true`.

**Out of scope.**
- Changes to the existing `/runs` (list) or `/runs/[id]` (detail) pages.
- New rating UI; uses the existing `reel_feedback.json` shape unchanged.
- Backend persistence changes; reads existing files only.
- Inline social/share affordances on tiles.
- Any change to the auth or basic-auth setup.

## 2. User-visible behavior

The homepage gains a new section above the existing "New Reel" prompt form:

```
┌── Featured runs ────────────────────────┐
│ [PIN reel]   [run B reel]  [run C reel] │
│ "Sri Studio: AI tool ..."  "Sur La ..." │
│ "..."                       "..."       │
└─────────────────────────────────────────┘

   New Reel
   Type a brief; review the plan...
   [ prompt form ]
```

**Pin tile (slot 0).** Always shows run `05821f3a380d` if it qualifies (status completed, `would_ship=true`). Visually marked with a subtle blue border and a small "Pinned" badge top-left. Same vertical 9:16 video, same brief caption shape as live tiles.

**Live tiles (slots 1-2).** The two newest runs (by `completed_at` descending) where `state.status == "completed"` AND `reel_feedback.would_ship == true`, excluding the pin run.

**Tile contents.** Vertical 9:16 `<video>` with native HTML5 controls (preload metadata only, click to play). Below the video, the brief from `intent.json.topic`, truncated to two lines (`-webkit-line-clamp: 2`).

**Click behavior.** Inline play with native controls. No navigation, no modal.

**Empty / partial states.**
- Pin qualifies, 0 other shipped runs: section renders 1 centered tile (the pin).
- Pin qualifies, 1 other shipped run: section renders 2 tiles (pin + 1).
- Pin qualifies, 2+ other shipped runs: section renders 3 tiles (pin + 2 newest).
- Pin does not qualify (file missing / would_ship false / not on disk): pin is dropped silently. Slots fill with the 3 newest non-pin shipped runs. If none, section returns `null` and the homepage falls back to its current shape.

**Mobile.** At viewport `<= 640px`, the 3-column grid collapses to 1 column; tiles stack with 16px gap. The pin keeps its border and badge. Section title stays.

## 3. Architecture

```
  Browser                                            
   │                                                 
   │ GET /                                           
   ▼                                                 
  ┌────────────────────┐                             
  │ Next.js homepage   │                             
  │   page.tsx         │                             
  │   <FeaturedRuns/>  │ ──── server fetch ──┐       
  │   <PromptForm/>    │                     │       
  └────────────────────┘                     ▼       
                                ┌──────────────────┐ 
                                │ FastAPI backend  │ 
                                │ GET /api/featured│ 
                                │      -runs       │ 
                                └────────┬─────────┘ 
                                         │ scan disk  
                                         ▼            
                                ┌──────────────────┐ 
                                │ runs/<id>/       │ 
                                │   state.json     │ 
                                │   intent.json    │ 
                                │   reel_feedback  │ 
                                │   reel.mp4       │ 
                                └──────────────────┘ 
```

The frontend hits the new endpoint server-side (Next.js Server Component). Tiles' `<video src>` points at the existing `GET /api/runs/{id}/reel.mp4` so we reuse the auth and caching that endpoint already has.

## 4. Backend

### 4.1 New endpoint

```
GET /api/featured-runs?pin=<run_id>&limit=3

Response 200:
[
  {
    "run_id": "05821f3a380d",
    "brief": "Sri Studio: AI tool that transforms one sentence into a narrated vertical reel",
    "reel_url": "/api/runs/05821f3a380d/reel.mp4",
    "completed_at": "2026-05-09T16:32:06.334493+00:00",
    "pinned": true
  },
  {
    "run_id": "<live_run_id>",
    "brief": "...",
    "reel_url": "/api/runs/<live_run_id>/reel.mp4",
    "completed_at": "2026-05-09T15:10:00.000000+00:00",
    "pinned": false
  },
  ...
]
```

Both query params are optional. Defaults: `pin=None`, `limit=3`. The endpoint always returns at most `limit` items.

### 4.2 Selection logic

Pseudocode in `api.py` (real implementation goes in a small helper, e.g., `featured.py`, to keep `api.py` lean):

```python
def list_featured_runs(pin: str | None, limit: int) -> list[FeaturedRun]:
    candidates = []
    for run_dir in sorted(_runs_dir().iterdir()):
        if not run_dir.is_dir():
            continue
        state = _load_json(run_dir / "state.json", default={})
        if state.get("status") != "completed":
            continue
        feedback = _load_json(run_dir / "reel_feedback.json", default=None)
        if not feedback or not feedback.get("would_ship"):
            continue
        intent = _load_json(run_dir / "intent.json", default={})
        candidates.append(FeaturedRun(
            run_id=run_dir.name,
            brief=intent.get("topic", ""),
            reel_url=f"/api/runs/{run_dir.name}/reel.mp4",
            completed_at=feedback.get("submitted_at"),
            pinned=False,
        ))

    # Newest-first.
    candidates.sort(key=lambda r: r.completed_at or "", reverse=True)

    pin_item = None
    if pin:
        pin_item = next((c for c in candidates if c.run_id == pin), None)
        if pin_item:
            pin_item = pin_item.model_copy(update={"pinned": True})
            candidates = [c for c in candidates if c.run_id != pin]

    out = []
    if pin_item:
        out.append(pin_item)
    out.extend(candidates[: max(0, limit - len(out))])
    return out
```

`_load_json` is a small safe loader that returns `default` on `FileNotFoundError` or `json.JSONDecodeError`.

### 4.3 Pydantic model

```python
class FeaturedRun(BaseModel):
    run_id: str
    brief: str
    reel_url: str
    completed_at: str | None
    pinned: bool
```

### 4.4 Cost / size considerations

- Endpoint reads only small JSON files (state, intent, reel_feedback) for each run dir; no images, audio, or mp4 are opened.
- Worst case: O(N) directory walk where N is total runs on disk. At a few hundred runs this is < 50ms; if it ever becomes a concern we add a tiny cache or an index file.
- No LLM calls; no third-party API hits; nothing to budget.

## 5. Frontend

### 5.1 New component

`frontend/components/FeaturedRuns.tsx` (Server Component):

```tsx
const PINNED_RUN_ID = "05821f3a380d";
const LIMIT = 3;

interface FeaturedRun {
  run_id: string;
  brief: string;
  reel_url: string;
  completed_at: string | null;
  pinned: boolean;
}

async function fetchFeatured(): Promise<FeaturedRun[]> {
  const res = await fetch(
    `${process.env.BACKEND_INTERNAL_URL}/api/featured-runs?pin=${PINNED_RUN_ID}&limit=${LIMIT}`,
    { cache: "no-store" },
  );
  if (!res.ok) return [];
  return res.json();
}

export async function FeaturedRuns() {
  const runs = await fetchFeatured();
  if (runs.length === 0) return null;

  // NB: Tailwind cannot generate dynamic class strings via template
  // interpolation. Spell out each layout class statically so the JIT picks
  // them up. Mobile (<640px) collapses to a single column in every case.
  const layoutClass =
    runs.length === 1
      ? "grid grid-cols-1 max-w-[200px] mx-auto gap-4"
      : runs.length === 2
      ? "grid grid-cols-1 sm:grid-cols-2 max-w-[420px] mx-auto gap-4"
      : "grid grid-cols-1 sm:grid-cols-3 gap-4";

  return (
    <section className="mb-10">
      <h3 className="text-xs uppercase tracking-wider text-neutral-500 mb-4">
        Featured runs
      </h3>
      <div className={layoutClass}>
        {runs.map((r) => <FeaturedTile key={r.run_id} run={r} />)}
      </div>
    </section>
  );
}

function FeaturedTile({ run }: { run: FeaturedRun }) {
  return (
    <div className="flex flex-col gap-2">
      <div className={`relative aspect-[9/16] bg-black rounded-md overflow-hidden border ${run.pinned ? "border-blue-600 ring-1 ring-blue-600/20" : "border-neutral-800"}`}>
        {run.pinned && (
          <span className="absolute top-1.5 left-1.5 z-10 bg-blue-600/85 text-white text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-sm">
            Pinned
          </span>
        )}
        <video
          src={run.reel_url}
          controls
          preload="metadata"
          playsInline
          className="absolute inset-0 w-full h-full object-contain bg-black"
        />
      </div>
      <p className="text-xs text-neutral-400 line-clamp-2 leading-snug">{run.brief}</p>
    </div>
  );
}
```

(Tailwind classes; matches the existing project's styling conventions.)

### 5.2 Homepage wiring

`frontend/app/page.tsx`:

```tsx
import { PromptForm } from "@/components/PromptForm";
import { FeaturedRuns } from "@/components/FeaturedRuns";

export default function Home() {
  return (
    <div>
      <FeaturedRuns />
      <h2 className="text-2xl font-semibold mb-2">New Reel</h2>
      <p className="text-neutral-400 mb-6 text-sm">
        Type a brief; review the plan scene-by-scene; approve to generate.
      </p>
      <PromptForm />
    </div>
  );
}
```

`FeaturedRuns` renders nothing (`return null`) if the section would be empty, so the existing layout is unchanged when there are no qualifying runs.

### 5.3 Backend URL config

`BACKEND_INTERNAL_URL` is the in-cluster URL the Next.js server uses to reach the FastAPI backend (e.g., `http://backend:8000` in docker-compose, where `backend` is the compose service name). The reel mp4 in the `<video src>` uses a relative `/api/runs/...` URL so the browser loads it through nginx; only the JSON metadata fetch goes server-to-server.

## 6. Edge cases and error handling

| Case | Behavior |
|---|---|
| Pin run dir does not exist on disk | Pin is dropped silently; slots fill with newest non-pin shipped runs. |
| Pin run exists but has no `reel_feedback.json` | Same as above. Backend logs a `WARN` once with the missing pin id. |
| Pin run exists, `would_ship=false` | Same as above. |
| Pin run exists, `would_ship=true`, but `reel.mp4` missing | Pin is included in the response (it qualified by feedback); the `<video>` shows a broken media icon. Acceptable for V1; future polish can `HEAD` the mp4 and skip if 404. |
| Backend `/api/featured-runs` returns 500 | `fetchFeatured` returns `[]`; `<FeaturedRuns>` returns `null`; homepage shows current shape. No error UI; the section just isn't there. |
| Backend down entirely | Same as above. Next.js Server Component fetch fails, caught, returns `null`. |
| Mobile width | Grid collapses to single column; tiles stack with 16px gap; pin keeps badge + border. |
| 0 qualifying runs total | Component returns `null`. Homepage = current state. |

## 7. Testing

### 7.1 Backend unit tests (`backend/tests/test_featured_runs.py`)

1. Empty runs dir returns `[]`.
2. One completed + would_ship=true run returns 1 item, `pinned=false`.
3. Pin id passed and matches an existing qualifying run: returns it at slot 0 with `pinned=true`; remaining slots filled newest-first.
4. Pin id passed but no matching run on disk: returns the newest qualifying runs; no pin in output.
5. Mixed runs (some completed-but-not-shipped, some failed, some shipped): only shipped + completed appear.
6. `limit=1` with 3 candidates and a matching pin: returns just the pin.
7. `completed_at` sort: a newer run comes before an older run.

### 7.2 Frontend snapshot / render tests

Jest + React Testing Library. Mock `fetch` to return:
- empty array → component renders `null`.
- 1 pinned run → renders 1 tile, centered, with the badge.
- 2 runs (1 pin + 1 live) → renders 2 tiles.
- 3 runs (1 pin + 2 live) → renders 3 tiles in a row.

### 7.3 E2E (Playwright)

One additional spec under `frontend/e2e/`:
- Visit `/`. Assert at least one tile with `[data-testid="featured-tile"]` is present.
- Assert the pin tile has the "Pinned" badge.
- Click the pin tile's `<video>`; assert it begins playing (`videoElement.paused === false` after a short wait).

## 8. Implementation order

1. Backend helper `featured.py` with `list_featured_runs` and the Pydantic model.
2. Backend route `GET /api/featured-runs` wired in `api.py`.
3. Backend unit tests (7 cases above).
4. Frontend `FeaturedRuns` and `FeaturedTile` components.
5. Homepage wiring in `page.tsx`.
6. Frontend snapshot tests.
7. Playwright e2e spec.
8. Manual smoke check against the local dev stack: confirm the pin appears with the correct brief and plays.
9. Deploy to Hetzner and verify against production data.

## 9. Open questions

None at spec time. The only design choice that may want revisiting after seeing it live: whether the pin's blue accent reads as "branded" (good) or "different" (potentially confusing). Decision deferred to post-deploy review; cheap to tune the CSS later.
