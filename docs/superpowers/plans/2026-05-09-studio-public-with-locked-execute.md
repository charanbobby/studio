# Public Studio with Locked Execute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open the studio.sshub.dev surface to the public so anyone can browse, view past runs, and submit a brief, while keeping the paid Execute pipeline behind HTTP basic auth on the single `POST /api/runs/{id}/approve-plan` endpoint. Add a guest credential pair (`guest` / `make-a-reel`) alongside the existing `admin` and `csc` entries.

**Architecture:** Move the `auth_basic` directive from server-level (covering all routes) to a single regex `location` block in the nginx site config. Add the new htpasswd entry on the production host. Update the source-controlled nginx config in the repo so future deploys preserve the new shape. No backend or frontend code changes; the browser handles the 401 → credential prompt flow natively.

**Tech Stack:** nginx (host-level), Apache htpasswd (bcrypt entries via `-B`), `rsync` over `ssh` (already in deploy/deploy.sh), `docker run` wrapper for `rsync` on the Windows host. No Python, TypeScript, or test framework changes.

**Spec:** `docs/superpowers/specs/2026-05-09-studio-public-with-locked-execute-design.md`

**Production-touching:** Tasks 3 and 4 modify a shared production system (studio.sshub.dev). The implementer MUST ask the user for explicit confirmation before executing Task 3 (the rollout) and MUST follow the rollback procedure in section 10 of the spec if smoke fails.

---

## File map

**Modified (source-controlled):**
- `nginx/studio.sshub.dev.conf`. Full rewrite to remove server-level `auth_basic` and add a single regex `location` block for the approve-plan endpoint. Header comment explains the auth model.

**Modified (out-of-repo documentation):**
- `d:/Python Applications/Hetzner Cloud Setup/.env`. Append one line: `STUDIO_BASIC_AUTH_GUEST=make-a-reel`.

**Modified (production server, via SSH):**
- `/etc/nginx/conf.d/studio.sshub.dev.htpasswd`. Append one bcrypt entry for `guest`.
- `/etc/nginx/sites-available/studio.sshub.dev`. Replace with the new shape from the repo (after backing up to `.bak`).

**Untouched:**
- All FastAPI / Next.js code. Auth lives at nginx; the application is unaware.
- Existing htpasswd entries `admin` and `csc`. Append-only.
- `deploy/deploy.sh`. The existing script handles the rsync and the docker compose up on the host; this plan invokes it.
- TLS certs and certbot config. The live `/etc/nginx/sites-available/studio.sshub.dev` retains its certbot-injected `ssl_*` directives; only the lines we change are touched.

---

## Task 1: Rewrite the source-controlled nginx config

**Files:**
- Modify: `nginx/studio.sshub.dev.conf`

- [ ] **Step 1: Replace the file contents**

Open `nginx/studio.sshub.dev.conf` and replace the ENTIRE contents with:

```nginx
# /etc/nginx/sites-available/studio.sshub.dev
#
# Pattern matches the rest of sshub.dev: host nginx terminates TLS via
# certbot --nginx and reverse-proxies to the Docker containers bound on
# 127.0.0.1.
#
# Auth model: the homepage, Past Runs, brief submission, and Plan
# generation are PUBLIC. Only POST /api/runs/{id}/approve-plan (the gate
# that fires the paid Execute pipeline: Flux + ElevenLabs + ffmpeg) is
# behind basic auth. Three credential pairs live in
# /etc/nginx/conf.d/studio.sshub.dev.htpasswd:
#   admin (Sri), csc (assessor), guest (public-shareable: make-a-reel).

map $http_upgrade $connection_upgrade {
    default upgrade;
    ""      close;
}

server {
    server_name studio.sshub.dev;

    client_max_body_size 25m;

    # Authenticated: only this single endpoint fires Execute (paid APIs).
    # Regex location, declared before /api/ so it wins the match.
    location ~ ^/api/runs/[^/]+/approve-plan$ {
        auth_basic           "Sri Studio: approve reel";
        auth_basic_user_file /etc/nginx/conf.d/studio.sshub.dev.htpasswd;

        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Authorization $http_authorization;
        proxy_read_timeout 5m;
    }

    # Public: SSE stream needs long-lived connection, no buffering, long read timeout.
    location ~ ^/api/runs/[^/]+/stream$ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Connection "";
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 1h;
    }

    # Public: backend API + static reel/plan files.
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 5m;
    }

    # Public: frontend Next.js.
    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_http_version 1.1;
    }

    # Filled in by `sudo certbot --nginx -d studio.sshub.dev`:
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/studio.sshub.dev/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/studio.sshub.dev/privkey.pem;
    # include /etc/letsencrypt/options-ssl-nginx.conf;
    # ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    listen 80;
}
```

- [ ] **Step 2: Verify shape with grep**

```bash
cd "/d/Python Applications/CSC"
# These four assertions must all hold for the file to be correct.
! grep -E "^\s+auth_basic\s+\"Sri Studio\"" nginx/studio.sshub.dev.conf  # old server-level realm gone
grep -q 'location ~ \^/api/runs/\[\^/\]+/approve-plan\$' nginx/studio.sshub.dev.conf  # new locked block
grep -q 'auth_basic\s\+"Sri Studio: approve reel"' nginx/studio.sshub.dev.conf  # new realm string
grep -c 'location ' nginx/studio.sshub.dev.conf  # should be 4 (approve-plan, stream, /api/, /)
```

Expected output: the first command exits 0 (no matches in the negation), the next two grep commands print one matching line each, and the count is `4`.

- [ ] **Step 3: Em-dash check**

```bash
grep -P '\x{2014}' nginx/studio.sshub.dev.conf
```

Expected: no output (no em dashes).

- [ ] **Step 4: Commit**

```bash
cd "/d/Python Applications/CSC"
git add nginx/studio.sshub.dev.conf
git commit -m "feat(nginx): public site, lock only approve-plan endpoint"
```

---

## Task 2: Update local .env documentation

**Files:**
- Modify: `d:/Python Applications/Hetzner Cloud Setup/.env`

This file is documentation only (nothing reads it at runtime); it lives outside the CSC repo. The change is a single new line so the user has one place to look up the guest password.

- [ ] **Step 1: Read the current file**

```bash
cat "/d/Python Applications/Hetzner Cloud Setup/.env"
```

Confirm the existing file ends with:

```
STUDIO_BASIC_AUTH_SRI=admin
STUDIO_BASIC_AUTH_CSC=csc2026
```

If those two lines are not present, STOP and report; the file may have a different shape than the spec assumes.

- [ ] **Step 2: Append the guest line**

Use the Edit tool to add `STUDIO_BASIC_AUTH_GUEST=make-a-reel` immediately after the existing `STUDIO_BASIC_AUTH_CSC=csc2026` line. Both prior lines stay byte-identical.

After:

```
STUDIO_BASIC_AUTH_SRI=admin
STUDIO_BASIC_AUTH_CSC=csc2026
STUDIO_BASIC_AUTH_GUEST=make-a-reel
```

- [ ] **Step 3: Verify**

```bash
grep STUDIO_BASIC_AUTH "/d/Python Applications/Hetzner Cloud Setup/.env"
```

Expected: three lines, in the order shown above.

- [ ] **Step 4: Commit (separate repo)**

The Hetzner Cloud Setup folder is its own git repo. Check if it has uncommitted state and commit there:

```bash
cd "/d/Python Applications/Hetzner Cloud Setup"
git status --short
git add .env
git commit -m "docs: add guest credential pair for studio.sshub.dev"
```

If the repo's git status shows other unrelated changes, stage ONLY `.env` (the `git add .env` command above does this). Do not bundle in unrelated edits.

---

## Task 3: Production rollout

**Files (production server):**
- Append: `/etc/nginx/conf.d/studio.sshub.dev.htpasswd`
- Backup + replace: `/etc/nginx/sites-available/studio.sshub.dev`

**Production-touching task. STOP and ask the user for explicit confirmation before running any step in this task.** Send a message like: "Ready to run Task 3 (production rollout): backup current nginx config, add guest user to htpasswd, swap in new config, validate, reload. Confirm to proceed."

The auto-mode classifier may also block production-touching commands; if it does, surface the block and request the user re-confirm in-turn.

- [ ] **Step 1: Confirm latest commit is pushed**

```bash
cd "/d/Python Applications/CSC"
git push origin main
```

Expected: either "Everything up-to-date" or a clean push of Task 1's commit. The deploy script rsyncs the working tree, not the remote, but pushing first ensures GitHub matches what we deploy.

- [ ] **Step 2: Stage SSH key and rsync the repo to /opt/sri-studio**

The deploy script `deploy/deploy.sh` uses `rsync`, which is not installed on the Windows host. Use a containerized rsync (the same approach used for the Featured Runs deploy):

```bash
# Stage key inside the project so the docker bind-mount can see it
cp /c/Users/chara/.ssh/id_hetzner "/d/Python Applications/CSC/.deploy_key"
chmod 600 "/d/Python Applications/CSC/.deploy_key"

# Run rsync via container. MSYS_NO_PATHCONV prevents Git Bash from
# mangling the /src container path into a Windows path.
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "/d/Python Applications/CSC:/src" \
  instrumentisto/rsync-ssh \
  sh -c 'cp /src/.deploy_key /root/id_hetzner && chmod 600 /root/id_hetzner && rsync -az --delete \
    --rsh "ssh -i /root/id_hetzner -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/known_hosts" \
    --exclude=".git" --exclude="runs" --exclude="frontend/node_modules" \
    --exclude="frontend/.next" --exclude="frontend/tsconfig.tsbuildinfo" \
    --exclude="backend/experiments/out" --exclude="backend/__pycache__" \
    --exclude=".probes" --exclude="_resume.md" --exclude=".superpowers" \
    --exclude=".deploy_key" \
    /src/ sri@46.62.255.66:/opt/sri-studio/'

# Clean up the staged key
rm -f "/d/Python Applications/CSC/.deploy_key"
```

Expected: rsync exits 0 (a "directory has vanished" warning for transient temp dirs is benign).

- [ ] **Step 3: Backup the live nginx config**

```bash
ssh -i /c/Users/chara/.ssh/id_hetzner -o StrictHostKeyChecking=accept-new sri@46.62.255.66 \
  "sudo cp /etc/nginx/sites-available/studio.sshub.dev /etc/nginx/sites-available/studio.sshub.dev.bak && \
   ls -la /etc/nginx/sites-available/studio.sshub.dev*"
```

Expected: two files listed, the original and the `.bak` copy with the same size.

- [ ] **Step 4: Add guest user to htpasswd**

Run the `htpasswd` command on the server. Use bcrypt (`-B`) and pass the password via `-b` so the script does not need to be interactive:

```bash
ssh -i /c/Users/chara/.ssh/id_hetzner sri@46.62.255.66 \
  "sudo htpasswd -B -b /etc/nginx/conf.d/studio.sshub.dev.htpasswd guest make-a-reel && \
   sudo cat /etc/nginx/conf.d/studio.sshub.dev.htpasswd"
```

Expected: three lines in the htpasswd output:
- `admin:$2y$05$...`
- `csc:$2y$05$...`
- `guest:$2y$05$...`

If `admin` or `csc` lines are missing, STOP. The spec requires them to remain intact. Restore from `studio.sshub.dev.htpasswd.bak` if one exists, otherwise re-run `htpasswd -B -b ... admin admin` and `htpasswd -B -b ... csc csc2026` to restore them.

- [ ] **Step 5: Swap in the new site config and validate**

The repo copy was rsynced to `/opt/sri-studio/nginx/studio.sshub.dev.conf` in Step 2. The live config at `/etc/nginx/sites-available/studio.sshub.dev` has the same shape PLUS the certbot-injected SSL block at the end. Use a single inline awk to splice the new server block into the existing file in a way that preserves the certbot lines:

The simplest correct approach: read the existing file's certbot block, replace the entire file with the new shape from the repo, then re-append the certbot block. Step-by-step:

```bash
ssh -i /c/Users/chara/.ssh/id_hetzner sri@46.62.255.66 << 'REMOTE'
set -e

# Capture the certbot-injected SSL block (everything between "managed by Certbot" markers)
sudo grep -A 100 "managed by Certbot" /etc/nginx/sites-available/studio.sshub.dev | head -50 > /tmp/cert_block.txt
echo "Captured certbot block:"
cat /tmp/cert_block.txt

# If /tmp/cert_block.txt is empty, certbot has not been re-run since the original setup
# and the live file already matches the shape of the repo file. In that case we just copy.
if [ ! -s /tmp/cert_block.txt ]; then
  echo "No certbot block to preserve; doing a straight copy."
  sudo cp /opt/sri-studio/nginx/studio.sshub.dev.conf /etc/nginx/sites-available/studio.sshub.dev
else
  echo "WARN: certbot lines present in live config. Manual splice needed."
  echo "Aborting Step 5 to avoid breaking SSL. Operator: manually merge"
  echo "/opt/sri-studio/nginx/studio.sshub.dev.conf into the live file,"
  echo "preserving the certbot ssl_* directives, then re-run nginx -t and reload."
  exit 1
fi

sudo nginx -t
REMOTE
```

Expected: `nginx: the configuration file /etc/nginx/nginx.conf syntax is ok` and `nginx: configuration file /etc/nginx/nginx.conf test is successful`.

If the script aborts because certbot lines are present, STOP and ask the user to either:
1. Manually splice the new server block into the live file, preserving the `listen 443 ssl;` + `ssl_certificate*` lines, OR
2. Run `sudo certbot --nginx -d studio.sshub.dev` after the swap so certbot re-injects them.

Do not proceed to Step 6 if `nginx -t` fails.

- [ ] **Step 6: Reload nginx**

```bash
ssh -i /c/Users/chara/.ssh/id_hetzner sri@46.62.255.66 \
  "sudo systemctl reload nginx && sudo systemctl is-active nginx"
```

Expected: `active`. No error output from the reload.

- [ ] **Step 7: Quick health probe**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/
```

Expected: `200`. (If 401, the auth removal did not take effect; SSH back in and check `nginx -T | grep -A 2 "server_name studio.sshub.dev"` for unexpected `auth_basic` lines.)

This task has no commit (all changes are server-side state).

---

## Task 4: Production smoke matrix

**Files:** none (verification only).

After Task 3 succeeds, run the full smoke matrix from spec section 8.3 + 8.4. Anonymous probes, authenticated probe, and a browser walk-through.

- [ ] **Step 1: Anonymous public-route probes**

All three should return 200. Use `-o /dev/null -w "%{http_code}\n"` to print just the status code.

```bash
echo "Homepage:"
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/

echo "Featured runs API:"
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/api/featured-runs

echo "Past runs list API:"
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/api/runs
```

Expected: three lines of `200`. Any 401 is a failure; STOP and run the rollback in section 10 of the spec.

- [ ] **Step 2: Anonymous brief submission**

Submit a brief without auth; should create a run and return 200 with the run id.

```bash
curl -sS -X POST https://studio.sshub.dev/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"smoke test public POST after auth rework","duration_s":5,"with_music":false}'
```

Expected: a JSON body containing `"run_id": "<some_id>"`. Save the run id for Step 3.

- [ ] **Step 3: Anonymous approve attempt should be rejected**

Use the run id from Step 2. The plan needs ~5-10 seconds to generate; sleep first, then attempt to approve without credentials.

```bash
sleep 15
RUN_ID="<paste_from_step_2>"
curl -sS -i -X POST "https://studio.sshub.dev/api/runs/${RUN_ID}/approve-plan" \
  -H 'Content-Type: application/json' \
  -d '{}' | head -10
```

Expected: HTTP/2 401, with a `WWW-Authenticate: Basic realm="Sri Studio: approve reel"` header in the response. NOT a 200 response.

If the response is 200, auth is not enforced; STOP and investigate before proceeding.

- [ ] **Step 4: Authenticated approve with guest credentials**

Same run id, this time with `-u guest:make-a-reel`. The point is to confirm the credential is accepted; you do NOT have to let it run to completion. To avoid burning a paid Execute call, send an empty body (which approves the existing plan as-is) and rely on the daily cost cap to bound spend, OR cancel by killing the curl after the response code shows.

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -u guest:make-a-reel \
  -X POST "https://studio.sshub.dev/api/runs/${RUN_ID}/approve-plan" \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Expected: `200`. NOT 401.

If you want to also verify the existing creds still work, repeat with `-u csc:csc2026` and `-u admin:admin` against fresh runs.

- [ ] **Step 5: Browser walk-through (Playwright MCP)**

Open https://studio.sshub.dev/ in an incognito window via Playwright MCP. Walk through:

```
1. Navigate to https://studio.sshub.dev/  (no auth in URL)
   Expected: page loads with no popup. Featured Runs section visible.
2. Take screenshot to /c/Users/chara/.playwright-mcp/auth-public-home.png
3. Click the "Past runs" link in the header.
   Expected: page loads with no popup. Past runs list renders.
4. Take screenshot to /c/Users/chara/.playwright-mcp/auth-public-runs.png
5. Navigate back home, type "smoke test from browser" in the prompt textarea, click Generate plan.
   Expected: plan generates, scene-by-scene review UI appears, no popup.
6. Take screenshot to /c/Users/chara/.playwright-mcp/auth-public-plan.png
7. Click Approve.
   Expected: browser shows a basic-auth dialog labeled "Sri Studio: approve reel".
   Take screenshot of the dialog if possible (may be OS-native, not always
   in DOM). Document the realm string visible in the dialog.
8. Cancel the dialog (do NOT enter creds, since this would burn an Execute call).
   Expected: the approve request fails; the UI shows whatever default error
   it shows for a failed approve.
```

Use the Playwright MCP tools available in the session:
- `mcp__plugin_playwright_playwright__browser_navigate`
- `mcp__plugin_playwright_playwright__browser_take_screenshot` (save under `C:/Users/chara/.playwright-mcp/`)
- `mcp__plugin_playwright_playwright__browser_evaluate`

Read each screenshot back via the Read tool to verify visually.

This task has no commit; report findings.

---

## Self-review checklist

- Spec section 1 (goal: public site, locked Execute, guest creds) → Tasks 1, 2, 3 cover the nginx + htpasswd + .env documentation.
- Spec section 2 (visitor behavior table) → Task 4 Step 5 walks through each row in a real browser.
- Spec section 3 (architecture diagram) → Task 1 implements the new auth boundary.
- Spec section 4.1 (source-controlled config text) → Task 1 Step 1 is the literal file contents.
- Spec section 4.2 (diff summary) → Task 1 Step 2's grep assertions verify each change.
- Spec section 4.3 (htpasswd already exists) → Task 3 Step 4 appends to it.
- Spec section 5 (server-side procedure) → Task 3 Steps 3-6 execute it.
- Spec section 6 (.env documentation) → Task 2 implements it.
- Spec section 7 (no frontend changes) → no task; intentional.
- Spec section 8 (testing) → Task 4 covers all four sub-sections (8.1 backend = no-op; 8.2 local docker = no-op since no logic changed; 8.3 curl = Steps 1-4; 8.4 browser = Step 5).
- Spec section 9 (edge cases) → Task 3's nginx -t catches typos; Task 4 Step 3 catches a mis-applied auth removal; Task 3's htpasswd -b verification catches credential-loss accidents.
- Spec section 10 (rollback) → referenced in Task 3's pre-step warning and Task 4 Step 1 failure handling.
- Spec section 11 (implementation order) → matches Task 1 → 2 → 3 → 4 numbering.
- Spec section 12 (open questions: none) → no task needed.

No placeholders, no TBDs. Type names not applicable (config-only change). Run id passed from Step 2 to Steps 3-4 of Task 4 is consistent.
