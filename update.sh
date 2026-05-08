#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Pulling latest changes..."
git pull --ff-only

echo "==> Rebuilding and restarting containers..."
docker compose -f docker-compose.pi.yml up -d --build

echo "==> Pruning dangling images..."
docker image prune -f

echo "==> Done. Tail logs with:"
echo "    docker compose -f docker-compose.pi.yml logs -f"
