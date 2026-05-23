#!/usr/bin/env bash
set -euo pipefail

SSH_KEY="$HOME/LightsailDefaultKey-eu-west-3.pem"
VPS="ubuntu@tehtek.com"
REMOTE_DIR="/opt/backend"

echo "==> Pushing to GitHub..."
git push origin main

echo "==> Deploying on VPS..."
ssh -i "$SSH_KEY" "$VPS" "
  cd $REMOTE_DIR
  git pull
  docker compose up -d --build backend
  sleep 2
  docker logs tehtek_backend --tail 5
"

echo "==> Done."
