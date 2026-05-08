#!/usr/bin/env bash
# One-time host setup for studio.sshub.dev. Run this ONCE on the Hetzner
# box after the first ./deploy/deploy.sh has put the project at
# /opt/sri-studio. Idempotent: re-running is safe.
#
# Prereq: DNS A record studio.sshub.dev -> 46.62.255.66 must resolve.
# Verify with: nslookup studio.sshub.dev 8.8.8.8
#
# Usage on the host:
#   ssh -i ~/.ssh/id_hetzner sri@46.62.255.66
#   bash /opt/sri-studio/deploy/host_setup.sh
#
# Will prompt for sudo password (admin) and for two basic-auth passwords
# (one for sri, one for csc). Use fresh passwords; do not reuse sudo.

set -euo pipefail

APP_DIR="/opt/sri-studio"
NGINX_CONF_DIR="/etc/nginx/conf.d"
NGINX_SITE_AVAIL="/etc/nginx/sites-available"
NGINX_SITE_ENAB="/etc/nginx/sites-enabled"
SITE="studio.sshub.dev"

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: $APP_DIR not found. Run ./deploy/deploy.sh from local first."
  exit 1
fi

echo ">>> Step 1: Install apache2-utils (htpasswd)"
sudo apt update -qq
sudo apt install -y apache2-utils

echo ">>> Step 2: Generate basic-auth credentials"
echo "    You will be prompted for two passwords (sri, then csc)."
sudo htpasswd -B -c "$NGINX_CONF_DIR/$SITE.htpasswd" sri
sudo htpasswd -B    "$NGINX_CONF_DIR/$SITE.htpasswd" csc
sudo chmod 644 "$NGINX_CONF_DIR/$SITE.htpasswd"
echo "    -> $NGINX_CONF_DIR/$SITE.htpasswd"

echo ">>> Step 3: Install nginx site config"
sudo cp "$APP_DIR/nginx/$SITE.conf" "$NGINX_SITE_AVAIL/$SITE"
if [ ! -L "$NGINX_SITE_ENAB/$SITE" ]; then
  sudo ln -s "$NGINX_SITE_AVAIL/$SITE" "$NGINX_SITE_ENAB/$SITE"
fi
sudo nginx -t
sudo systemctl reload nginx

echo ">>> Step 4: Issue Let's Encrypt cert"
echo "    DNS for $SITE must already resolve to this server."
echo "    nslookup $SITE 8.8.8.8 should return 46.62.255.66"
read -rp "    DNS confirmed and resolving? [y/N]: " ans
if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
  sudo certbot --nginx -d "$SITE" --non-interactive --agree-tos \
    --email charan.bobby@gmail.com --redirect
  echo "    Cert installed. Certbot edited the nginx config to add 443/SSL."
else
  echo "    Skipped. After you add the DNS record, run:"
  echo "      sudo certbot --nginx -d $SITE"
fi

echo ">>> Step 5: Verify"
if curl -fsS http://127.0.0.1:8000/healthz > /dev/null; then
  echo "    Backend container OK on 127.0.0.1:8000"
else
  echo "    WARNING: backend not responding. Check: docker compose logs backend"
fi

if curl -fsS http://127.0.0.1:3000/ -o /dev/null; then
  echo "    Frontend container OK on 127.0.0.1:3000"
else
  echo "    WARNING: frontend not responding. Check: docker compose logs frontend"
fi

echo ""
echo "DONE. Test from your laptop:"
echo "  curl -u sri:<password> https://$SITE/api/healthz"
echo "  open https://$SITE/ in a browser"
