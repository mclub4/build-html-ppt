#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/codex/skills/build-html-slides/"
PLUGIN="$ROOT/plugins/build-html-slides/skills/build-html-slides/"
CLAUDE="$ROOT/.claude/skills/build-html-slides/"
GEMINI="$ROOT/.gemini/skills/build-html-slides/"

rsync -a --delete "$SOURCE" "$PLUGIN"
mkdir -p "$CLAUDE"
rsync -a --delete "$SOURCE" "$CLAUDE"
mkdir -p "$GEMINI"
rsync -a --delete "$SOURCE" "$GEMINI"
python3 "$ROOT/scripts/validate_repository.py"
echo "Codex plugin, Claude Code skill, and Gemini CLI skill synchronized with the canonical skill."
