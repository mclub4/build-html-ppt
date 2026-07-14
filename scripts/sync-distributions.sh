#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/codex/skills/build-html-slides/"
PLUGIN="$ROOT/plugins/build-html-slides/skills/build-html-slides/"
CLAUDE="$ROOT/.claude/skills/build-html-slides/"

rsync -a --delete "$SOURCE" "$PLUGIN"
mkdir -p "$CLAUDE"
rsync -a --delete "$SOURCE" "$CLAUDE"
python3 "$ROOT/scripts/validate_repository.py"
echo "Codex plugin and Claude skill synchronized with the canonical skill."
