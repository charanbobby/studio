---
name: sri-studio-helper
description: Produce a 5-minute screencast demo (browser scenes + burned captions + voice-clone) using the silent-first pipeline. Use when generating a hackathon submission video, product demo, or any short narrated screencast where the on-screen visuals must precisely match a spoken script. Voice generation is the expensive step and is gated on a human review of the captioned silent cut.
---

# Sri Studio Helper: silent-first screencast pipeline

This skill captures the lessons from building the SANS Find Evil hackathon submission video. Use it when you need to produce a short narrated screencast where what is shown on screen must precisely match what the narrator says, and where voice tokens (ElevenLabs or similar) are the most expensive part of the pipeline.

## The single most important rule

**Generate voice last.** Lock the silent video, lock the burned-in captions, get a human to watch the silent-with-captions cut end to end, ONLY then generate voice. Voice tokens are the only paid cost. Re-cuts before voice are free; re-cuts after voice are not.

## Pipeline phases (in strict order)

| Phase | What | Cost |
|---|---|---|
| A | Pre-record probes (target site reachable, expected DOM state present, locked rule still pending if applicable) | $0 |
| B | Per-beat Playwright recordings, one MP4 each | $0 |
| C | Silent assembly (ffmpeg concat) | $0 |
| D | Caption SRT generation + burn into video | $0 |
| **D.5** | **Human review gate, watch silent + captions end to end** | $0 (BLOCKING) |
| E | ElevenLabs voice generation, one MP3 per beat | TOKENS |
| F | Final mux + export | $0 |

**Never advance to E without explicit human signoff on the D.5 review.**

## Lessons learned (each one cost real time to discover)

### Voice-to-visual sync is the hardest part

When the voiceover says "X", the screen must be POINTING AT X at that exact moment. Generic slow-scrolling past content while the narrator talks is the single biggest mistake. Per-phrase sync (every 5-10 word claim has a matching highlight) is the standard. Hardcode the script so each phrase has a target DOM selector and an annotation type (box, arrow, callout).

### Probe DOM selectors LIVE before scripting them

Do NOT guess at selectors. Use Playwright (the MCP tool, OR a one-off `page.evaluate` call) to inspect the actual rendered DOM of the target site, find the real selectors, then write the scene script. The first attempt at the SANS demo used `[data-finding-card]` which did not exist; the real selector was `.finding.cls-attacker_persistence`. That cost a full re-record.

### Each beat is one MP4, one voiceover, one Playwright scene module

Independent files. Re-cuts touch one beat at a time. Never re-record the whole video to fix one beat. `record_beat.py beat3_case` re-runs only that scene.

### Trim every recording to its target duration via ffmpeg

Recordings overshoot because page load happens inside the recording context. Post-process each scene MP4 with `ffprobe` to get the actual duration, then `ffmpeg -ss <total - target> -t <target>` to trim the LAST `<target>` seconds. This preserves the final stable frame and drops the load preamble.

### Kill the chromium white-flash

Inject a dark default body color via `context.add_init_script` so the browser's white background never shows during navigation gaps. Use `documentElement.style.backgroundColor = '#0b1020'`, NOT `!important` (so the page's own stylesheet still wins after load).

```python
await context.add_init_script(
    "document.documentElement.style.backgroundColor = '#0b1020';"
    "document.documentElement.style.color = '#f8fafc';"
)
```

### Pin Playwright python to the base image's chromium

The `mcr.microsoft.com/playwright/python:v1.49.0-jammy` image bundles chromium for v1.49.0. If you `uv pip install playwright` you get the latest (e.g. 1.59.0) and `BrowserType.launch` fails with a version-mismatch error. Always pin: `uv pip install playwright==1.49.0`.

### ffmpeg subtitles filter PlayResX/PlayResY

By default, the ffmpeg `subtitles` filter assumes PlayResY=288. So `Fontsize=18` renders as 18 units of 288 (~67 physical pixels at 1080p). Pin `PlayResX=1920,PlayResY=1080` in `force_style` so Fontsize maps 1:1 to physical pixels.

```bash
ffmpeg -i video.mp4 -vf \
  "subtitles=captions.srt:force_style='PlayResX=1920,PlayResY=1080,Fontname=IBM Plex Sans,Fontsize=22,...'" \
  -c:a copy out.mp4
```

### Single-page-app sites: don't reload, use the app's own navigation

If the target site is an SPA, `?case=X&run=Y` query params do nothing. Find the JS functions the SPA exposes (like `toggleCase('id')` and `loadRun('case','run')`) and call them via `page.evaluate`. Tab switches via `[data-tab="findings"]` clicks.

### Captions are burned IN, not soft tracks

Soft SRT tracks require viewer-side toggling and do not survive re-uploads. Burn captions into the visuals before voice gen so the SRT timing is locked at the same time as the visuals. Voice gets layered on top of an already-captioned video.

### Captions ARE the voice script

The same string that becomes the burned caption becomes the voice line. Edit the script in ONE place (`captions.py BEATS` list). When you change a phrase, it changes both. Cannot drift.

### Side-effect beats run last

Any scene that mutates live state (e.g. a beat that clicks Approve on a real rule) must run AFTER all read-only beats. Otherwise re-recording other beats requires resetting the live state.

### Voice token budget protocol

Each beat's voiceover gets ONE generation. If the voice is too long, shorten the script TEXT (not the voice; never regenerate). Target: voice should be 1-2 seconds shorter than the beat slot to leave breathing room. Re-burning captions costs 0 tokens; regenerating voice burns tokens.

## File layout the skill expects

```
<project>/
  scripts/demo_video/   (or sri_studio_helper if reusing as a tool)
    config.py           # SITE_URL, beat-specific constants, DURATIONS dict
    captions.py         # BEATS list (name, start_s, duration_s, voiceover) + build_srt()
    record_beat.py      # CLI: python -m ... record_beat <beat_name>
    voice_gen.py        # CLI: python -m ... voice_gen [<beat_name>]
    assemble_silent.sh  # ffmpeg concat
    burn_captions.sh    # ffmpeg subtitle burn (with PlayResX/Y!)
    assemble_final.sh   # final mux
    Dockerfile          # playwright + ffmpeg + uv image
    scenes/             # one .py per beat, exposing async record(page)
    probes/check_site.py
  out/demo_video/       # gitignored: scene<n>.mp4, voice<n>.mp3, captions.srt, final.mp4
```

## Tools required

- Docker (the pipeline runs entirely inside an ephemeral image; do not install Playwright on the host)
- ffmpeg (inside the image, via `apt-get install ffmpeg`)
- IBM Plex fonts (or any sans font available to libass)
- ElevenLabs API key + voice clone ID (only at Phase E)

## How to start a new project with this skill

1. Copy `examples/find_evil_demo/` into your project's `scripts/demo_video/`.
2. Edit `config.py`: set `SITE_URL`, beat-specific constants, durations.
3. Edit `captions.py BEATS`: write voiceover lines per beat. Lock total to your target length (300s for 5-min).
4. PROBE the target site live with Playwright MCP. Find the real DOM selectors. Write them down.
5. Edit `scenes/<beat>.py` files: each one calls real selectors, draws highlight overlays via `page.evaluate`, sleeps for the budgeted duration.
6. Build the image: `cd scripts/demo_video && docker build -t demo-video:latest .`
7. Run probe: `docker run --rm -v "$(pwd)/../..:/work" -w /work demo-video:latest python scripts/demo_video/probes/check_site.py`
8. Record each beat: `... python -m scripts.demo_video.record_beat <beat_name>` (one at a time, side-effect beats last).
9. Assemble silent: `... bash scripts/demo_video/assemble_silent.sh`
10. Generate captions: `... python -m scripts.demo_video.captions`
11. Burn: `... bash scripts/demo_video/burn_captions.sh`
12. **REVIEW GATE**: human watches `out/demo_video/demo_silent_with_captions.mp4` end to end. If anything is off, fix the relevant scene + re-record only that beat + re-stitch. Repeat until approved.
13. ONLY NOW: set `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` and run `... python -m scripts.demo_video.voice_gen`.
14. Final assembly: `... bash scripts/demo_video/assemble_final.sh`
15. Upload final.mp4. Done.

## Anti-patterns

- Do NOT generate voice before D.5 signoff.
- Do NOT slow-scroll a page while the voiceover names specific things; tightly highlight each named element.
- Do NOT use URL query strings on SPAs; use the SPA's JS navigation functions.
- Do NOT install Playwright + ffmpeg on the host; use the Docker image.
- Do NOT use soft SRT tracks; burn captions in.
- Do NOT use `!important` on the dark CSS init script; it clobbers the page's own styling.
- Do NOT re-record the whole video to fix one beat; re-record only the affected beat.
- Do NOT trust default ffmpeg subtitle scaling; pin PlayResX/PlayResY.
