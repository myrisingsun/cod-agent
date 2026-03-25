#!/usr/bin/env bash
# Run Vite dev server locally. Proxies /api → http://localhost:8080.

set -e
cd "$(dirname "$0")/../frontend"

echo ">>> Frontend: http://localhost:3000 → proxies /api to http://localhost:8081"
VITE_BACKEND_URL=http://localhost:8081 npm run dev
