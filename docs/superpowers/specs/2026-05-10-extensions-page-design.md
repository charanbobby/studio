# Sri Studio: /extensions showcase page

**Date:** 2026-05-10
**Author:** Sricharan Sunkara, with Claude Code as thinking partner
**Status:** Approved by user; ready for implementation plan (combined with sub-projects A + B)
**Touches:** `studio.sshub.dev` homepage (`/`, new tile in `FeaturedRuns`), new route `/extensions` (Next.js + MDX), new `studio/public/samples/find-evil-canonical.mp4` (v1 hand-curated bridge), and a small addendum to the Helper-as-a-Service spec (`/helper/samples` endpoint becomes public, no auth)

---

## 1. Goal

A hiring-manager-facing page on `studio.sshub.dev/extensions` that tells a chronological story: take-home assignment, what was built (Sri Studio), what was extended on the user's own initiative (Helper API, MCP, sample videos), with the per-phrase voice-to-visual sync as the headline differentiator. Discovered from the homepage via a tile in the existing `FeaturedRuns` grid; not gated.

The page exists to be stumbled upon. The hiring manager opens `studio.sshub.dev/`, sees a tile that says "Extensions", clicks through, and reads a coherent story that ends with a working demo video.

## 2. Out of scope

- Anything in the Helper service itself (covered by sub-project A's spec; this page consumes A, does not change it). One small spec-A addendum is recorded in section 9.
- The MCP wrapper itself (sub-project B; this page references B but does not contain it).
- The Sentinel page or its embed (sub-project C).
- The Portfolio tile linking back to Sentinel (sub-project E).
- Any change to the existing homepage layout besides the one new tile in `FeaturedRuns`.
- Any change to auth, basic-auth, the prompt form, the runs pipeline, the cost ledger, or any existing route.
- Visual design differentiation; the page matches Sri Studio's existing Tailwind design system. Iteration deferred to post-launch.

## 3. User-visible behavior

A first-time visitor lands on `studio.sshub.dev/`. The existing homepage shows the prompt form and a row of `FeaturedRuns` tiles. **One additional tile is added to that row, slot 3 (rightmost):**

```
+----------- Featured runs --------------+
| [pinned reel] [run B] [run C] [EXTNS] |
+----------------------------------------+
```

The new tile uses the same `FeaturedTile` component vocabulary as the live tiles, but its content reads:

- Title: `Extensions`
- Subtitle: `The extension story`
- Body line: `Helper API, MCP, sample videos`
- Click target: `/extensions`

Clicking through navigates to `/extensions`. The page is six sections in a single vertical scroll, each section a heading + prose + (optionally) embedded components.

```
/extensions

  [Hero]
    Title:   "Extensions"
    Tagline: "Demo videos as code. Configurable, repeatable, cheap to re-cut."

  ## 1. The assignment
    Prose: the take-home prompt and constraints.

  ## 2. What I built (Sri Studio)
    Prose: short summary of the baseline app.
    Optional: <FeaturedSampleEmbed run_id="05821f3a380d" />

  ## 3. What I extended on my own
    Prose with three sub-headers:
      - Sri Studio Helper (silent-first screencast pipeline)
      - Helper as a Service (HTTP API)
      - MCP wrapper
    HEADLINE FRAMING: demo videos as code.
        Source:  a project tarball.
        Output:  a finished video.
        Cost:    $0.05.
        Re-runs: free until the voice phase.
    <SampleGrid />  <- live fetch from /helper/samples (with v1 fallback)

  ## 4. Critique / what I'd do differently
    Prose: editorial reflection.

  ## 5. Tech notes
    Bullet links to spec docs and source repos.
```

## 4. Page placement and routing

**URL:** `/extensions`. Future-proof against additional extension stories (other take-homes); the slug is broad.

**Route file:** `frontend/app/extensions/page.tsx` (Next.js 14 App Router, server component by default; can be marked `"use client"` only if a sub-component needs it).

**nginx:** No new server-block changes. The Next.js frontend already serves `/`; the new path inherits routing automatically.

**Discovery from homepage:** one new tile appended to the `FeaturedRuns` grid in `frontend/components/FeaturedRuns.tsx`. The tile is a fixed entry (not a database run); rendered inline as a sibling of the live `FeaturedTile`s. Visual treatment matches the live tiles to read as native content, not promo.

## 5. Page structure (six sections)

| # | Heading | Content | Components used |
|---|---|---|---|
| H | (Hero, no heading) | Page title `Extensions` + one-sentence tagline | Plain MDX |
| 1 | The assignment | The take-home prompt and constraints; what was asked | Plain MDX prose |
| 2 | What I built (Sri Studio) | Short summary of the baseline app; brief → plan → approval → reel | Plain MDX prose; optional `<FeaturedSampleEmbed run_id="05821f3a380d" />` |
| 3 | What I extended on my own | Three sub-headers: Sri Studio Helper, Helper as a Service, MCP wrapper. **Headline framing: demo videos as code.** Source: a project tarball. Output: a finished video. Cost: $0.05. Re-runs: free until the voice phase. The canonical demo video plays underneath, proving the claim. | `<SampleGrid />` for the sample videos |
| 4 | Critique / what I'd do differently | Editorial reflection | Plain MDX prose |
| 5 | Tech notes | Bullet links to spec docs in the repo, the Helper repo, the MCP server (when it exists) | Plain MDX with hyperlinks |

The "What I extended" section is the load-bearing one. It must lead with the programmability claim (input: tarball, output: video, cost: pennies, re-runs free until voice), not with a list of components. The claim first, the canonical video underneath proving it, the components below as the supporting machinery. Sync, captions, voice cloning are all qualities of the pipeline that make the claim believable; none of them is the headline.

## 6. Editorial format

**Single MDX file:** `frontend/app/extensions/page.mdx`. Markdown for prose, JSX for embedded components. Standard Next.js 14 MDX setup (`@next/mdx` configured in `next.config.js`).

```
frontend/
  app/
    extensions/
      page.mdx          # all prose + section structure + embedded components
      _components/      # local components for this page only
        SampleGrid.tsx
        FeaturedSampleEmbed.tsx
        SectionAnchor.tsx
```

Why MDX, not plain markdown plus a separate TSX page: prose and the live `<SampleGrid />` need to interleave inside the "What I extended" section. With plain markdown the grid can only sit at the end of the prose; with MDX it sits exactly where the narrative places it.

Why a single MDX file, not multiple per-section files: the page is small (six sections, roughly 800-1200 words of prose). Composition adds files without value at this size; revisit if the page grows past 2000 words.

`next.config.js` change: enable MDX support if not already on.

```js
const withMDX = require('@next/mdx')();
module.exports = withMDX({
  pageExtensions: ['ts', 'tsx', 'mdx'],
  // ... existing config
});
```

## 7. Sample embed mechanic

`<SampleGrid />` is a server component that:

1. At request time, fetches `GET https://studio.sshub.dev/helper/samples` (the new public endpoint, see section 9).
2. If the fetch succeeds, renders one tile per sample with `<video controls src={sample.final_url} />` plus the sample's `goal` and `target_url` as caption.
3. If the fetch fails (Helper service down, returns 5xx, or returns empty), renders the v1 fallback (see below) instead.
4. Always shows the v1 fallback at the top of the grid as a "highlight" sample, even when live samples are also present. The Find Evil canonical demo is the founding sample and stays pinned.

**v1 hand-curated bridge** (necessary because the Helper service does not exist on the VPS yet and `/helper/samples` therefore returns nothing on day one):

- Source MP4: `D:/Python Applications/Find Evil - Hackathon/out/Demo_Video.mp4` (locally owned; the SANS Find Evil submission produced by the Helper).
- Destination in this repo: `studio/public/samples/find-evil-canonical.mp4` (committed; under 25 MB per nginx body cap; if larger, host on the VPS at `studio/static/...` and reference by URL).
- A static manifest entry alongside the MDX page:

```json
// frontend/app/extensions/_components/canonical-sample.json
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

`<SampleGrid />` reads this JSON unconditionally and renders it pinned at slot 0; live samples (when `/helper/samples` returns them) fill slots 1+. When the Helper service goes live, this JSON entry remains, ensuring the founding demo never disappears from the page.

## 8. Visual style

Match Sri Studio's existing design system. Tailwind, same nav, same dark aesthetic, same `font-sans` Inter or whatever is already configured. Editorial liberties allowed:

- Wider prose column than the homepage (max-w-2xl or 3xl) for readability.
- Larger video embeds in `<SampleGrid />` than the FeaturedRuns thumbnails (since this page is the dedicated viewing surface).
- Pull-quote treatment on the "sync is the killer feature" framing in section 3.
- All other styling inherits from existing components and Tailwind config.

No new color tokens, no new fonts, no nav changes. Page must read as part of the same site, not a microsite.

## 9. Cross-spec dependencies

This spec consumes one Helper service endpoint that does not yet exist. **Spec-A addendum (apply when implementing A):**

- Add a new endpoint: `GET /helper/samples` returning a JSON array `[ { job_id, generated_at, goal, target_url, final_url }, ... ]`. Lists every job whose `voice` POST included `?save_as_sample=true`.
- This endpoint is **public** (no `X-Helper-Key` required). It exposes only data the user has explicitly chosen to mark as a sample. All other Helper endpoints remain auth-gated.
- Reads the existing `/data/samples/<job_id>/manifest.json` files (already in spec A's persistence section). No new storage.
- nginx config inherits the existing `/helper/` location block; no per-endpoint auth differentiation needed (the FastAPI handler decides which endpoints require the key).

The combined A + B + D implementation plan will fold this addendum into A's task list as a single sub-task.

## 10. Testing

**Unit (in `frontend/`):**

- `SampleGrid.test.tsx`: renders fallback canonical sample when fetch fails (mocked), renders both fallback + live samples when fetch succeeds, renders only fallback when live returns empty array.
- `FeaturedRuns.test.tsx`: existing tests still pass with the new fixed Extensions tile appended (assert tile count + assert Extensions tile is at slot 3).

**Integration (Playwright, matches existing studio test conventions):**

- Visit `https://studio.sshub.dev/`, assert the Extensions tile is visible in the FeaturedRuns row, click it, assert URL is `/extensions`.
- On `/extensions`, assert all six section headings are present (Hero, Assignment, What I built, What I extended, Critique, Tech notes).
- Assert the canonical sample video element is present and has a `src` attribute pointing at `/samples/find-evil-canonical.mp4`.
- Assert at least one `<video>` element is rendered (the canonical fallback is enough).

**Manual review checklist (before merging):**

- Page reads top-to-bottom as a coherent story; no abrupt transitions.
- The "sync is the killer feature" framing appears verbatim or close to it.
- Critique section is honest, not performative; reads as a senior engineer reflecting, not as marketing.
- No broken links to spec docs.
- The canonical sample plays in a real browser (not just headless Playwright).

## 11. Future work (tracked, not in v1)

- More than one editorial story (e.g. for other take-home assignments); the `/extensions` URL is plural for this reason.
- A `<SampleDetail>` page per sample (`/extensions/samples/<job_id>`) showing the full beats list, captions, and runtime cost. v1 just embeds the videos inline.
- RSS feed or social share buttons; not for v1.
- Dark/light mode toggle differentiated from Sri Studio's main aesthetic; deferred to post-launch.
- An analytics hit on the Extensions tile click and on `/extensions` page view (so we know how often hiring managers actually stumble on it). Probably worth adding in v1.5 if a privacy-preserving analytics is already wired into Sri Studio.

## 12. Decisions log

- 2026-05-10: Brainstorm started; decomposed Helper-related work into 5 sub-projects (A through E). This spec is D.
- 2026-05-10: Narrative arc chosen as chronological (origin to extension), over two-column / reverse-chronological / editorial-first.
- 2026-05-10: Six sections chosen (Hero, Assignment, What I built, What I extended, Critique, Tech notes). Critique kept in (rejected the option to drop it as undermining); confidence framing instead.
- 2026-05-10: URL chosen as `/extensions` (broad, future-proof) over `/sri-studio-helper`, `/origin`, `/about`.
- 2026-05-10: Discovery via tile in the existing `FeaturedRuns` grid (over banner CTA / nav link / both).
- 2026-05-10: Sample embed via live fetch from new public `GET /helper/samples` endpoint, with hand-curated canonical sample as fallback + permanent highlight.
- 2026-05-10: Editorial format MDX (prose + inline React) over plain markdown / multi-file / pure TSX.
- 2026-05-10: Visual style matches existing Sri Studio design system (over differentiated editorial style).
- 2026-05-10: Hero and section-3 headline framing chosen as "demo videos as code" (programmability) over time-saved / whole-pipeline-automation / show-don't-tell. Reasoning: hiring-manager audience reads engineering signals best; the framing tees up the source/output/cost/re-runs spec-style summary of what the Helper actually is. Earlier draft had proposed "sync as killer feature"; user corrected (sync is a quality that makes the claim believable, not the value prop itself).
- 2026-05-10: Recorded spec-A addendum (`/helper/samples` becomes public, no auth) for inclusion in the combined A + B + D implementation plan.
- 2026-05-10: Canonical sample video located at `D:/Python Applications/Find Evil - Hackathon/out/Demo_Video.mp4`; will be copied to `studio/public/samples/find-evil-canonical.mp4` as v1 fallback.
