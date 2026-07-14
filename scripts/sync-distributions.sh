#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/codex/skills/build-html-slides/"
PLUGIN="$ROOT/plugins/build-html-slides/skills/build-html-slides/"

rsync -a --delete "$SOURCE" "$PLUGIN"
python3 "$ROOT/scripts/validate_repository.py"
echo "Plugin skill synchronized with the standalone skill."

