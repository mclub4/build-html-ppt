#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$REPO/codex/skills/build-html-slides"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_HOME/skills/build-html-slides"
DRY_RUN=0

case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  -h|--help) echo "Usage: ./uninstall.sh [--dry-run]"; exit 0 ;;
  "") ;;
  *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

remove_path() {
  echo "+ rm -rf $DEST"
  [ "$DRY_RUN" -eq 1 ] || rm -rf "$DEST"
}

if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SOURCE" ]; then
  remove_path
elif [ -f "$DEST/.build-html-slides-copy-origin" ] &&
  [ "$(cat "$DEST/.build-html-slides-copy-origin")" = "$REPO" ]; then
  remove_path
elif [ -e "$DEST" ] || [ -L "$DEST" ]; then
  echo "Skipped unrelated installation: $DEST"
else
  echo "Nothing to remove: $DEST"
fi

