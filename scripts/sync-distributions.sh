#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/codex/skills/build-html-slides/"
ARCHIFY_SOURCE="$ROOT/codex/skills/archify/"
PLUGIN="$ROOT/plugins/build-html-slides/skills/build-html-slides/"
PLUGIN_ARCHIFY="$ROOT/plugins/build-html-slides/skills/archify/"
CLAUDE="$ROOT/.claude/skills/build-html-slides/"
CLAUDE_ARCHIFY="$ROOT/.claude/skills/archify/"
GEMINI="$ROOT/.gemini/skills/build-html-slides/"
GEMINI_ARCHIFY="$ROOT/.gemini/skills/archify/"

# Transient build and session artifacts must never reach a distribution copy.
# They break the byte-identical tree contract enforced by validate_repository.py
# and ship dead weight to installed skills.
EXCLUDES=(
  --exclude='__pycache__/'
  --exclude='.pytest_cache/'
  --exclude='.omc/'
  --exclude='*.pyc'
  --exclude='*.pyo'
  --exclude='.DS_Store'
)

prune_transient() {
  find "$1" \
    \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.omc' \) -prune -exec rm -rf {} + 2>/dev/null || true
  find "$1" \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete 2>/dev/null || true
}

prune_transient "$SOURCE"
prune_transient "$ARCHIFY_SOURCE"

cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$SOURCE"
rsync -a --delete "${EXCLUDES[@]}" "$SOURCE" "$PLUGIN"
mkdir -p "$PLUGIN_ARCHIFY"
rsync -a --delete "${EXCLUDES[@]}" "$ARCHIFY_SOURCE" "$PLUGIN_ARCHIFY"
cp "$ROOT/LICENSE" "$ROOT/THIRD_PARTY_NOTICES.md" "$ROOT/plugins/build-html-slides/"
mkdir -p "$CLAUDE"
rsync -a --delete "${EXCLUDES[@]}" "$SOURCE" "$CLAUDE"
mkdir -p "$CLAUDE_ARCHIFY"
rsync -a --delete "${EXCLUDES[@]}" "$ARCHIFY_SOURCE" "$CLAUDE_ARCHIFY"
mkdir -p "$GEMINI"
rsync -a --delete "${EXCLUDES[@]}" "$SOURCE" "$GEMINI"
mkdir -p "$GEMINI_ARCHIFY"
rsync -a --delete "${EXCLUDES[@]}" "$ARCHIFY_SOURCE" "$GEMINI_ARCHIFY"
prune_transient "$PLUGIN"
prune_transient "$CLAUDE"
prune_transient "$GEMINI"
python3 "$ROOT/scripts/validate_repository.py"
echo "Build HTML Slides and bundled Archify distributions synchronized for Codex, Claude Code, and Gemini CLI."
