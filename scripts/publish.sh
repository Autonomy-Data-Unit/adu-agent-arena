#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Exporting leaderboard ==="
uv run python scripts/export_leaderboard.py

echo "=== Generating summaries ==="
uv run python scripts/generate_summaries.py

echo "=== Re-exporting with summaries ==="
uv run python scripts/export_leaderboard.py

echo "=== Building SvelteKit app ==="
cd web
npm run build
cd ..

echo "=== Deploying to AppGarden ==="
appgarden deploy production

echo "=== Done ==="
appgarden apps status adu-agent-arena --server adu-apps
