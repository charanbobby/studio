# Sri Studio: Public Site with Locked Execute Endpoint

**Date:** 2026-05-09
**Author:** Sricharan Sunkara, with Claude Code as thinking partner
**Status:** Approved by user; ready for implementation plan
**Touches:** `nginx/studio.sshub.dev.conf` (the deployable copy in the repo), the production server's `/etc/nginx/sites-available/studio.sshub.dev`, the production server's `/etc/nginx/conf.d/studio.sshub.dev.htpasswd`, and `d:/Python Applications/Hetzner Cloud Setup/.env` (documentation only).

---

## 1. Goal

Open the studio.sshub.dev surface to the public so anyone can browse the homepage, view past runs, and even submit a brief to see a Plan, while keeping the paid Execute pipeline (Flux + ElevenLabs + ffmpeg) locked behind HTTP basic auth. Add a guest credential pair the user can share publicly, alongside the two existing pairs (admin and csc).

The new Featured Runs section that just shipped becomes a true showcase: visitors can land on studio.sshub.dev with no credential prompt, watch the pinned reel and the most recent shipped runs, and either stop there or hit "New Reel" to play with the Plan stage themselves.

**Out of scope.**

- Per-user accounts or session-based auth. HTTP basic auth stays.
- Rate limiting on the now-public POST /api/runs (the user accepts the small Plan cost as the price of openness; can be revisited later if abuse appears).
- Frontend custom auth modal. The browser's native basic-auth dialog is the UX.
- Any change to backend code; auth stays at the nginx layer.
- Telemetry of which credential approved each run. Not in scope.

## 2. User-visible behavior

| Visitor action | Today | After this change |
|---|---|---|
| Open https://studio.sshub.dev/ | Browser pops basic auth | Page loads, no prompt |
| Click "Past runs" header link | Page loads (after auth) | Page loads, no prompt |
| Open a per-run detail page | Loads (after auth) | Loads, no prompt |
| Watch the homepage Featured reel videos | Loads (after auth) | Loads, no prompt |
| Submit a brief, see the Plan | Loads (after auth) | Plan generates and renders, no prompt |
| Click "Approve" on the Plan | Fires (after auth) | Browser pops basic auth dialog |
| Enter guest / make-a-reel and submit | (n/a today: same as admin) | Approve goes through; Execute kicks off |
| Enter wrong creds 3 times | Loops the dialog, then 401 | Same |
| Already authenticated this session | Goes through | Goes through (browser cached creds) |

The realm string in the popup is `Sri Studio: approve reel` so visitors who weren't expecting a prompt understand what they're being asked for.

## 3. Architecture

```
                                                 ┌──────────────────────────────┐
                                                 │ /etc/nginx/conf.d/...htpasswd │
                                                 │   admin : <hash>              │
                                                 │   csc   : <hash>              │
                                                 │   guest : <hash>  (NEW)       │
                                                 └──────────────┬────────────────┘
 Browser                                                        │
   │                                                            │ auth_basic
   │                                                            │
   ▼                                                            ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │ nginx (host)                                                             │
  │                                                                          │
  │  location ~ ^/api/runs/[^/]+/approve-plan$  { auth_basic ON }            │
  │  location ~ ^/api/runs/[^/]+/stream$        { (public, SSE settings) }   │
  │  location /api/                             { (public) }                 │
  │  location /                                 { (public, frontend) }       │
  └─────────────────────────────────────────┬────────────────────────────────┘
                                            │ proxy_pass to 127.0.0.1
                                            ▼
                                   ┌──────────────────┐
                                   │ FastAPI backend  │
                                   │ Next.js frontend │
                                   │ (no auth code)   │
                                   └──────────────────┘
```

The auth boundary is moved from the server-level (everything) to a single regex location (just one route). FastAPI does not see Authorization headers or implement any auth itself: nginx either accepts the basic credentials and proxies the request, or rejects with 401 before the request reaches the backend.

## 4. Nginx configuration

### 4.1 Source-controlled file

`nginx/studio.sshub.dev.conf` in the repo is the canonical copy that gets rsync'd to the host. Replace its current shape with:

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

### 4.2 Diff summary

- REMOVE the two server-level `auth_basic` and `auth_basic_user_file` lines.
- ADD a new `location ~ ^/api/runs/[^/]+/approve-plan$` block, placed before the SSE stream location so nginx evaluates the regex blocks in declaration order. (Order of two regex locations only matters if they could both match; these two cannot, but keeping the locked one first makes intent clear.)
- ADD `proxy_set_header Authorization $http_authorization;` inside the locked block. nginx normally forwards Authorization, but being explicit prevents any future global header rule from accidentally stripping it.
- ADD a multi-line comment at the top of the server block explaining the auth model. New maintainers should not have to grep history to understand why most routes are open.

### 4.3 What the production host already has

The `/etc/nginx/conf.d/studio.sshub.dev.htpasswd` file already exists with `admin` and `csc` entries. Adding `guest` is a one-line `htpasswd -B` invocation. Existing entries are untouched.

The certbot lines (commented in the source-controlled file) are filled in on the production host by the existing `sudo certbot --nginx -d studio.sshub.dev` plumbing. The deploy script does not regenerate them.

## 5. Server-side procedure

These commands are run once during the deploy:

```bash
ssh -i ~/.ssh/id_hetzner sri@46.62.255.66

# 1. Add the guest credential. -B is bcrypt; matches existing entries.
sudo htpasswd -B /etc/nginx/conf.d/studio.sshub.dev.htpasswd guest
# Enter 'make-a-reel' twice when prompted.

# 2. Verify all three users present.
sudo cat /etc/nginx/conf.d/studio.sshub.dev.htpasswd
# Expected: three lines, admin / csc / guest, each with a $2y$ bcrypt hash.

# 3. Replace the active site config with the new shape (already rsynced
#    to /opt/sri-studio/nginx/studio.sshub.dev.conf by the deploy script).
sudo cp /opt/sri-studio/nginx/studio.sshub.dev.conf /etc/nginx/sites-available/studio.sshub.dev

# 4. Validate config and reload.
sudo nginx -t && sudo systemctl reload nginx
```

The certbot-managed SSL block in the live `/etc/nginx/sites-available/studio.sshub.dev` will be re-applied by certbot automatically on next renewal; the source-controlled file leaves those lines commented because they reference machine-specific cert paths.

## 6. Local documentation

`d:/Python Applications/Hetzner Cloud Setup/.env` gets one new line:

```
STUDIO_BASIC_AUTH_GUEST=make-a-reel
```

The existing two lines stay:

```
STUDIO_BASIC_AUTH_SRI=admin
STUDIO_BASIC_AUTH_CSC=csc2026
```

This file is documentation only. Nothing reads it at runtime. It exists so the user has a single place to look up "what's the password for X" without grepping nginx configs on the server.

## 7. Frontend changes

None. The browser handles the 401 → popup → retry-with-Authorization flow natively. Once a user enters credentials, the browser caches them for the session so subsequent Approves in the same tab do not prompt again.

The realm string (`Sri Studio: approve reel`) shows in the popup so visitors understand what's being asked of them.

## 8. Testing

### 8.1 Backend tests

No changes. Auth lives at nginx; FastAPI is unaware. The full pytest suite continues to pass without modification.

### 8.2 Local docker-compose check

The local stack does not run nginx. Submitting a brief and approving from `http://localhost:3000` continues to work end to end with no prompt; that confirms backend behavior is unchanged. No new local test is needed.

### 8.3 Production smoke (manual after deploy)

```bash
# Anonymous probes: should all return 200 (or 4xx if input bad, but never 401).
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/api/featured-runs
curl -sS -o /dev/null -w "%{http_code}\n" https://studio.sshub.dev/api/runs

# Anonymous brief submission: should return 200 with a run_id.
curl -sS -X POST https://studio.sshub.dev/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"smoke test public POST","duration_s":5,"with_music":false}'

# Anonymous approve attempt: should return 401 with WWW-Authenticate header.
curl -sS -i -X POST https://studio.sshub.dev/api/runs/<some_id>/approve-plan \
  -H 'Content-Type: application/json' -d '{}' | head -10

# Authenticated approve: should return 200 (or 422 if the run id is wrong, but
# never 401).
curl -sS -u guest:make-a-reel -X POST \
  https://studio.sshub.dev/api/runs/<some_id>/approve-plan \
  -H 'Content-Type: application/json' -d '{}'
```

(Use a real run id from a freshly submitted brief in the last two probes. Or reject the test plan after probing instead of approving, to avoid burning a real Execute call.)

### 8.4 Browser smoke (manual after deploy)

In an incognito window:

1. Open https://studio.sshub.dev/. Confirm no popup; the homepage and Featured Runs row render.
2. Click into "Past runs"; confirm no popup; the list loads.
3. Click "Sri Studio" to return home, type a 1-line brief, submit. Confirm Plan generates and renders, no popup.
4. Click "Approve". Confirm the browser shows a basic-auth popup with the realm "Sri Studio: approve reel".
5. Enter `guest` / `make-a-reel`. Confirm the request goes through and Execute starts.
6. Submit a second brief and approve it in the same tab. Confirm no second popup (browser cached the credential).

## 9. Edge cases and risks

| Case | Behavior | Mitigation if needed |
|---|---|---|
| Visitor enters wrong creds 3 times | Browser keeps prompting until they cancel; on cancel the request is aborted and the frontend shows whatever default error UI the approve-plan call has today. | Acceptable for V1. Could add a friendlier error string on the frontend later. |
| nginx config typo or htpasswd mismatch | `nginx -t` catches syntax errors; if the htpasswd path is wrong the config fails to load and reload is rejected. | Always run `nginx -t` before `systemctl reload nginx`. The procedure in section 5 does this. |
| Bot spams POST /api/runs (Plan generation) | Each request costs ~$0.007 (Extract + Plan only; the daily cost cap from ADR 012 still aborts at $5/day). | If abuse appears, add nginx `limit_req_zone` keyed on `$binary_remote_addr` for `POST /api/runs`. Revisit only if it happens. |
| Visitor enters guest creds but the realm description confuses them ("why is it asking?") | The realm is "Sri Studio: approve reel". Most users will read it. | Could add a one-line hint in the Plan-review UI ("approving a plan requires the demo password we shared with you") in a future polish. |
| User finds an old browser bookmark with the cached basic-auth credential | The credential still works. The Authorization header is automatically sent on every request to studio.sshub.dev for the duration of the cached session. | Not a vulnerability; same as today. To invalidate, change the htpasswd entry. |
| The `Authorization` header gets stripped between nginx and the backend | The locked block explicitly sets `proxy_set_header Authorization $http_authorization;` so this cannot happen by accident. | Already mitigated. |
| Production server's `/etc/nginx/sites-available/studio.sshub.dev` is out of sync with the repo `nginx/studio.sshub.dev.conf` | The deploy script rsyncs into `/opt/sri-studio/`, not `/etc/nginx/`. Section 5 step 3 copies it across explicitly during this deploy. | One-time during this rollout. After that, future edits go through the same procedure. |

## 10. Rollback

If smoke fails or anything looks wrong:

```bash
ssh -i ~/.ssh/id_hetzner sri@46.62.255.66

# Restore the previous server-level auth_basic config (a copy of the
# pre-change file should be saved as a .bak before swap; see plan).
sudo cp /etc/nginx/sites-available/studio.sshub.dev.bak \
        /etc/nginx/sites-available/studio.sshub.dev
sudo nginx -t && sudo systemctl reload nginx
```

The `guest` htpasswd entry is harmless to leave in place during rollback.

## 11. Implementation order

1. Update `nginx/studio.sshub.dev.conf` in the repo to the new shape.
2. Commit and push.
3. SSH in, back up the live site config (`cp ... .bak`), add guest to htpasswd, copy the new config across, `nginx -t`, reload.
4. Run the curl probes in section 8.3.
5. Run the browser smoke in section 8.4 in an incognito window.
6. Update `d:/Python Applications/Hetzner Cloud Setup/.env` with the guest line and commit.
7. If everything is green, leave the deploy in place; if anything fails, follow section 10 rollback.

## 12. Open questions

None at spec time.
