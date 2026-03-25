#!/usr/bin/env bash
# Run FastAPI backend locally (outside Docker).
# Infrastructure (postgres, minio, qdrant, ollama) must be running on localhost ports.

set -e
cd "$(dirname "$0")/.."

echo ">>> Backend: ENV_FILE=.env.local"
ENV_FILE=.env.local .venv/Scripts/python -m uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8081 \
  --reload \
  --log-level info
