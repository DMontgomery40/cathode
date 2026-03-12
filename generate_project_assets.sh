#!/usr/bin/env bash
# Generate assets and render a Cathode project.
# Run from the cathode directory: ./generate_project_assets.sh projects/<project_name>

set -euo pipefail

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

project_dir="${1:-}"

if [ -z "$project_dir" ]; then
  echo "Usage: $0 projects/<project_name>"
  exit 1
fi

echo "=== Cathode Project Asset Generation ==="
echo "Starting at $(date)"

/opt/homebrew/bin/python3.10 - "$project_dir" <<'PY'
from pathlib import Path
from core.pipeline_service import generate_project_assets_service, render_project_service
import json
import sys

project_dir = Path(sys.argv[1])

print('Generating assets...')
result = generate_project_assets_service(
    project_dir,
    generate_images=True,
    generate_videos=True,
    generate_audio=True,
    regenerate_images=False,
    regenerate_audio=False,
)
print(json.dumps(result, indent=2))

print()
print('Rendering final video...')
render = render_project_service(project_dir)
print(json.dumps(render, indent=2))
PY

echo "Completed at $(date)"
