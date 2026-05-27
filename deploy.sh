#!/usr/bin/env bash
# Deploy backend: build locally → push to Docker Hub → pull on VPS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SSH_KEY="$HOME/LightsailDefaultKey-eu-west-3.pem"
VPS="ubuntu@tehtek.com"
REMOTE_DIR="/opt/backend"
IMAGE="boulaz2002/tehtek-backend:latest"

echo "==> Pushing code to GitHub..."
git push origin main

echo "==> Building image locally..."
docker build -t "$IMAGE" .

echo "==> Pushing image to Docker Hub..."
docker push "$IMAGE"

echo "==> Deploying on VPS..."
ssh -i "$SSH_KEY" "$VPS" "
  cd $REMOTE_DIR
  git pull
  docker compose pull backend
  docker compose up -d backend
  sleep 3
  docker logs tehtek_backend --tail 5
"

echo "==> Done."
