# CSC Generation submission checklist

A runbook for assembling the take-home submission. Walk top-to-bottom; tick as you go.

## 1. Code repo

The submission usually wants a GitHub link or zip. Two clean options:

### Option A: Private GitHub repo (preferred)
- [ ] Create a private repo (e.g. `sricharan/sri-studio-csc`).
- [ ] Push the local `main` branch:
  ```
  cd "D:/Python Applications/CSC"
  git remote add origin git@github.com:<you>/sri-studio-csc.git
  git push -u origin main
  ```
- [ ] Add the assessor's GitHub username as a collaborator (or share the repo link with read access via the cover note).

### Option B: Zip
- [ ] Run from project root (excludes secrets, runs, build artifacts):
  ```
  cd "D:/Python Applications/CSC"
  tar -czf ../sri-studio-csc-submission.tar.gz \
    --exclude='./.git' --exclude='./runs' \
    --exclude='./frontend/node_modules' --exclude='./frontend/.next' \
    --exclude='./frontend/tsconfig.tsbuildinfo' \
    --exclude='./.env' --exclude='./_resume.md' \
    --exclude='./.playwright-mcp' --exclude='./e2e-success-*' \
    --exclude='./.claude' \
    .
  ```
- [ ] Verify the tarball: `tar -tzf ../sri-studio-csc-submission.tar.gz | head -30`
- [ ] Upload to wherever (Drive / Dropbox) and share the link.

## 2. Repo hygiene

- [ ] `.env` is NOT in git (verify: `git ls-files | grep '^.env$'` returns empty).
- [ ] `samples/` IS in git (3 reels + their plan/cost/intent).
- [ ] `docs/` IS in git: ADRs (12), spec, plan, walkthrough script, diagrams.html, questionnaire-draft.md, build-journal.md.
- [ ] `nginx/`, `deploy/`, `Dockerfile`s, `docker-compose.yml` IS in git.
- [ ] `.gitignore` excludes the personal application materials (`Application*/`, the assessment PDF).
- [ ] Verify with `git status` that nothing important is untracked.

## 3. README at the repo root

- [ ] Write `README.md` (one page) covering:
  - One-liner: what Sri Studio is.
  - Live URL: https://studio.sshub.dev/ + credentials line: `username: csc, password: csc2026`.
  - Quick local-run: `cp .env.example .env && fill keys && docker compose up --build`.
  - Where to find the design (link to `docs/superpowers/specs/...`), plan, ADRs, walkthrough script.
  - Sample outputs at `samples/`.

## 4. Walkthrough video

- [ ] Read `docs/walkthrough-script.md` once end-to-end. Edit anything that doesn't match what shipped.
- [ ] Open `docs/diagrams.html` in a side tab for the architecture sections.
- [ ] Open https://studio.sshub.dev/ in another tab for the live demo.
- [ ] Recording rules:
  - Your real voice (matches the cloned voice in the demo reels = continuity hook).
  - 1080p capture; OBS or QuickTime fine.
  - 12-14 minutes target.
  - Show one Approve flow + one Reject flow on tape (Reject demonstrates the cost-cap saving).
  - Show the Langfuse dashboard once: https://us.cloud.langfuse.com/project/cmovxs7vc0577ad07xqxobvdx/sessions filtered to the demo's run_id.
- [ ] Upload to Loom or YouTube (unlisted). Save the URL for the cover note.

## 5. Questionnaire (Component C)

- [ ] Open `docs/questionnaire-draft.md`. Walk through each `[POLISH]` marker. Fill in:
  - Q1: hours/week (your honest number).
  - Q4: prior most-complex production (Find Evil DFIR pipeline if you used it; the Sri Studio deploy at studio.sshub.dev also counts).
  - Q5: prior manual-process translation (Fair Play document-to-DB if applicable).
  - Q9: how you stay current.
- [ ] Save as `docs/questionnaire-final.md`.
- [ ] Optional: convert to PDF or just share the .md.

## 6. Cover note to send to CSC

- [ ] Use `docs/cover-note-template.md` as the starting point. Fill in the bracketed fields.

## 7. Submission package

The final submission contains:
- Repo link (or zip download link)
- Walkthrough video link (Loom or YouTube unlisted)
- Live URL: https://studio.sshub.dev/ + credentials (`csc / csc2026`)
- Questionnaire response (`docs/questionnaire-final.md` or PDF)
- Cover note

Put all of it in one email or web form per CSC's instructions in the assessment packet.

## 8. Pre-send sanity check

- [ ] Click your own GitHub repo link in an incognito tab; verify it loads / 404 doesn't show (collaborator has access).
- [ ] Click the walkthrough video link; verify it plays.
- [ ] Open https://studio.sshub.dev/ in incognito with `csc / csc2026`; submit a 5s prompt; verify the full Approve flow ships a reel.
- [ ] Verify the daily cost cap is set (`DAILY_COST_CAP_USD=5.00` in `/opt/sri-studio/.env` on the host).
- [ ] Verify `csc` user exists in `/etc/nginx/conf.d/studio.sshub.dev.htpasswd` (so the assessor can actually log in).

## 9. Day-of submission

- [ ] Send the email.
- [ ] Note the submission timestamp.
- [ ] Bookmark the Langfuse dashboard so you can reference it during the Solution Review interview.
- [ ] Plan a small follow-up: 24 hours after sending, confirm via the Langfuse dashboard that the assessor accessed the site (look for new sessions under `csc`).

## 10. After the interview

- [ ] Revoke the `csc` basic-auth user once they're done:
  ```
  ssh -i ~/.ssh/id_hetzner sri@46.62.255.66
  sudo htpasswd -D /etc/nginx/conf.d/studio.sshub.dev.htpasswd csc
  sudo systemctl reload nginx
  ```
- [ ] Optionally rotate `STUDIO_PASS_OWNER` if you used a weak demo password.
