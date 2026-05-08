# Deploy

Sri Studio runs on the existing `sshub.dev` Hetzner box. The host's
system nginx terminates TLS and routes `studio.sshub.dev` to the two
Docker containers (backend + frontend, bound to `127.0.0.1`).

## Prerequisites (one-time, host-side)

The base host already has:
- Docker + docker-compose-plugin (per `Hetzner Cloud Setup/setup_instructions.md`).
- nginx (system, not containerized).
- certbot --nginx plugin.
- Firewall (ufw) allowing SSH, HTTP, HTTPS.

## First deploy

### 1. DNS

Add an A record at your DNS provider (Cloudflare):

```
studio.sshub.dev  A  46.62.255.66
```

If your apex is proxied through Cloudflare, `CNAME studio -> sshub.dev`
also works. Wait until `nslookup studio.sshub.dev 8.8.8.8` returns the
IP before issuing a Let's Encrypt cert.

### 2. Sync the project to the host

From your local repo:

```bash
./deploy/deploy.sh
```

That rsyncs to `sri@studio.sshub.dev:/opt/sri-studio/` (assumes the key
at `$HOME/.ssh/id_hetzner` and the `sri` user from
`Hetzner Cloud Setup/setup_instructions.md`).

If `studio.sshub.dev` doesn't resolve yet, override with the IP:

```bash
DEPLOY_HOST=46.62.255.66 ./deploy/deploy.sh
```

### 3. Copy `.env` to the host (once)

`.env` is gitignored, not rsynced. Copy manually one time:

```bash
scp -i ~/.ssh/id_hetzner .env sri@studio.sshub.dev:/opt/sri-studio/.env
```

### 4. Generate basic auth credentials on the host

```bash
ssh -i ~/.ssh/id_hetzner sri@studio.sshub.dev
sudo apt install apache2-utils -y    # one-time
sudo htpasswd -B -c /etc/nginx/conf.d/studio.sshub.dev.htpasswd sri
sudo htpasswd -B    /etc/nginx/conf.d/studio.sshub.dev.htpasswd csc
```

The first line creates the file with the `sri` user; the second adds
`csc` (the assessor account). Use a fresh password (do NOT reuse the
sudo password).

### 5. Install the nginx site config

On the host:

```bash
sudo cp /opt/sri-studio/nginx/studio.sshub.dev.conf \
        /etc/nginx/sites-available/studio.sshub.dev
sudo ln -s /etc/nginx/sites-available/studio.sshub.dev \
           /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Issue Let's Encrypt cert

DNS must resolve before this works.

```bash
sudo certbot --nginx -d studio.sshub.dev
```

Certbot will:
- Validate the domain.
- Edit the nginx site config to add the `listen 443 ssl;` block.
- Reload nginx.
- Schedule auto-renewal (already wired via the host's certbot timer).

### 7. Start the containers

The deploy script (step 2) already ran `docker compose up -d --build`
on the host. To redo it:

```bash
ssh -i ~/.ssh/id_hetzner sri@studio.sshub.dev
cd /opt/sri-studio && docker compose up -d --build
```

### 8. Smoke test

```bash
curl -u sri:<password> https://studio.sshub.dev/api/healthz
# expected: {"status":"ok","service":"sri-studio-backend"}

curl -u sri:<password> https://studio.sshub.dev/ | head -10
# expected: HTML containing "Sri Studio"
```

Browser test: open `https://studio.sshub.dev/` and authenticate with
the `sri` credentials. You should see the New Reel form. Try a small
prompt to verify the full pipeline works against your `.env` keys.

## Subsequent deploys

After the first deploy, just:

```bash
./deploy/deploy.sh
```

The script rsyncs the latest code, rebuilds the Docker images, and
restarts the containers. nginx, certbot, and the `.env` are unchanged.

For the post-deploy healthz check from the local machine to also probe
HTTPS + basic auth, set `BASIC_AUTH`:

```bash
BASIC_AUTH=sri:<password> ./deploy/deploy.sh
```

## Cost cap

`DAILY_COST_CAP_USD` in `/opt/sri-studio/.env` (default `5.00`) bounds
total daily LLM/media spend. Cap state lives in
`/opt/sri-studio/runs/_daily_cost.json` and persists across container
restarts. Aborts new runs once the day's UTC total + the prospective
cost would exceed the cap.

## Logs

```bash
ssh -i ~/.ssh/id_hetzner sri@studio.sshub.dev
cd /opt/sri-studio && docker compose logs -f backend
cd /opt/sri-studio && docker compose logs -f frontend
sudo tail -f /var/log/nginx/access.log
```
