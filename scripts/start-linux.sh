#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="pm-mvp:local"
CONTAINER_NAME="pm-mvp"
VOLUME_NAME="pm-mvp-data"
HOST_PORT="${HOST_PORT:-8000}"
FOLLOW_LOGS="${FOLLOW_LOGS:-1}"

cd "$ROOT_DIR"

echo "[start-linux] Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "[start-linux] Removing existing container if present..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "[start-linux] Starting container on http://localhost:${HOST_PORT}"
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "${VOLUME_NAME}:/app/backend/data" \
  -p "${HOST_PORT}:8000" \
  "$IMAGE_NAME" >/dev/null

echo "[start-linux] Started."

if [ "$FOLLOW_LOGS" = "1" ]; then
  echo "[start-linux] Streaming logs. Press Ctrl+C to stop log tailing (container keeps running)."
  docker logs -f "$CONTAINER_NAME"
fi
