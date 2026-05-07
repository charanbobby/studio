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
   docker compose --profile prod run --rm certbot certonly --webroot \
     -w /var/www/certbot -d studio.sshub.dev --email you@example.com --agree-tos
   ```
4. `docker compose --profile prod up -d`

## Subsequent deploys
- `BASIC_AUTH=sri:password ./deploy/deploy.sh`

## Cost cap
- Set `DAILY_COST_CAP_USD` in `.env` on the server (default $5).
- Cap state lives in `/opt/sri-studio/runs/_daily_cost.json`; persists across container restarts.
