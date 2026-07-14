#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_HOME/skills/build-html-slides"
CHECK_ONLY=0

case "${1:-}" in
  --check) CHECK_ONLY=1 ;;
  -h|--help) echo "Usage: ./update.sh [--check]"; exit 0 ;;
  "") ;;
  *) echo "Unknown option: $1" >&2; exit 2 ;;
esac

git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null
UPSTREAM="$(git -C "$REPO" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo origin/main)"
REMOTE="${UPSTREAM%%/*}"
git -C "$REPO" fetch --quiet "$REMOTE"

LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD)"
REMOTE_SHA="$(git -C "$REPO" rev-parse "$UPSTREAM")"
BASE_SHA="$(git -C "$REPO" merge-base HEAD "$UPSTREAM")"

if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "Already up to date."
  exit 0
fi
if [ "$BASE_SHA" = "$REMOTE_SHA" ]; then
  echo "Local checkout is ahead; no update applied."
  exit 0
fi
if [ "$BASE_SHA" != "$LOCAL_SHA" ]; then
  echo "Local and upstream histories diverged; update manually." >&2
  exit 1
fi
if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "Update available: $(git -C "$REPO" rev-list --count "HEAD..$UPSTREAM") commit(s)."
  exit 10
fi

COPY_MODE=0
if [ -f "$DEST/.build-html-slides-copy-origin" ] &&
  [ "$(cat "$DEST/.build-html-slides-copy-origin")" = "$REPO" ]; then
  COPY_MODE=1
fi

git -C "$REPO" pull --ff-only
if [ "$COPY_MODE" -eq 1 ]; then
  "$REPO/install.sh" --copy
fi
echo "Updated to $(git -C "$REPO" rev-parse --short HEAD). Start a new Codex task to reload it."

