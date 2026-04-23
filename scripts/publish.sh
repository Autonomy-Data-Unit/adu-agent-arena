#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Exporting leaderboard ==="
if [ -d "logs/full-matrix" ]; then
    uv run python scripts/export_leaderboard.py logs/full-matrix
elif [ -d "logs" ] && ls logs/*.eval 1>/dev/null 2>&1; then
    uv run python scripts/export_leaderboard.py
else
    echo "No eval logs found — using existing leaderboard.json"
fi

echo "=== Generating summaries ==="
uv run python scripts/generate_summaries.py

echo "=== Building SvelteKit app ==="
cd web
npm run build
cd ..

echo "=== Deploying to AppGarden ==="
appgarden deploy production

echo "=== Done ==="
appgarden apps status adu-agent-arena
