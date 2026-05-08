#!/usr/bin/env bash
# Deploys Sri Studio to the sshub.dev Hetzner host.
#
# Pattern: rsync repo to /opt/sri-studio, ssh in, build + start the two
# Docker containers (backend + frontend, bound to 127.0.0.1). The host's
# system nginx + certbot handle TLS and routing studio.sshub.dev to the
# containers (config in nginx/studio.sshub.dev.conf, copied once during
# first-time setup per deploy/README.md).
#
# Usage:
#   ./deploy/deploy.sh
#
# Optional environment:
#   DEPLOY_HOST     default: studio.sshub.dev
#   DEPLOY_USER     default: sri
#   SSH_KEY         default: $HOME/.ssh/id_hetzner
#   BASIC_AUTH      default: unset (skip post-deploy healthz auth check)

set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-studio.sshub.dev}"
DEPLOY_USER="${DEPLOY_USER:-sri}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_hetzner}"
APP_DIR="/opt/sri-studio"

if [ ! -f "$SSH_KEY" ]; then
  echo "ERROR: SSH key not found at $SSH_KEY"
  echo "Override with SSH_KEY=/path/to/id_hetzner ./deploy/deploy.sh"
  exit 1
fi

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new)

echo ">>> Syncing repo to ${DEPLOY_USER}@${DEPLOY_HOST}:${APP_DIR}"
rsync -az --delete \
  --rsh "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  --exclude './.git' \
  --exclude './runs' \
  --exclude './frontend/node_modules' \
  --exclude './frontend/.next' \
  --exclude './frontend/tsconfig.tsbuildinfo' \
  --exclude './backend/experiments/out' \
  --exclude './backend/__pycache__' \
  --exclude './.probes' \
  --exclude './_resume.md' \
  ./ "${DEPLOY_USER}@${DEPLOY_HOST}:${APP_DIR}/"

echo ">>> docker compose up --build (host: ${DEPLOY_HOST})"
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "cd ${APP_DIR} && docker compose up -d --build"

echo ">>> waiting for backend healthz..."
sleep 10
for i in $(seq 1 12); do
  if [ -n "${BASIC_AUTH:-}" ]; then
    if curl -fsS -u "$BASIC_AUTH" "https://${DEPLOY_HOST}/api/healthz" > /dev/null 2>&1; then
      echo "DEPLOY OK: https://${DEPLOY_HOST}/  (authed healthz green)"
      exit 0
    fi
  else
    if ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
         "curl -fsS http://127.0.0.1:8000/healthz" > /dev/null 2>&1; then
      echo "DEPLOY OK: backend container healthy on host."
      echo "  set BASIC_AUTH=user:pass to also probe https://${DEPLOY_HOST}/"
      exit 0
    fi
  fi
  echo "  not yet (attempt $i/12), waiting 5s..."
  sleep 5
done

echo "ERROR: healthz did not turn green within 60s"
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "cd ${APP_DIR} && docker compose logs --tail=30 backend"
exit 1
