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

echo ">>> docker compose --profile prod up --build"
ssh "${APP_USER}@${HOST}" "cd ${APP_DIR} && docker compose --profile prod up -d --build"

echo ">>> Health check"
sleep 10
curl -fsS "https://${HOST}/api/healthz" -u "$BASIC_AUTH" \
  || (echo "healthz failed; rolling back manually if needed"; exit 1)
echo "DEPLOY OK: https://${HOST}/"
