#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="pm-mvp"

echo "[stop-mac] Stopping container..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "[stop-mac] Done."
