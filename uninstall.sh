#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
DO_CLAUDE=1
DO_CODEX=1
DO_GEMINI=1
DRY_RUN=0

usage() {
  echo "Usage: ./uninstall.sh [--claude-only|--codex-only|--gemini-only] [--dry-run]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --claude-only) DO_CLAUDE=1; DO_CODEX=0; DO_GEMINI=0 ;;
    --codex-only) DO_CLAUDE=0; DO_CODEX=1; DO_GEMINI=0 ;;
    --gemini-only) DO_CLAUDE=0; DO_CODEX=0; DO_GEMINI=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

remove_owned() {
  local source="$1" dest="$2" kind="$3" marker
  if [ "$kind" = "dir" ]; then
    marker="$dest/.build-html-slides-copy-origin"
  else
    marker="$dest.build-html-slides-origin"
  fi

  if { [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; } ||
     { [ -f "$marker" ] && [ "$(cat "$marker")" = "$REPO" ]; }; then
    echo "+ rm -rf $dest"
    [ "$DRY_RUN" -eq 1 ] || rm -rf "$dest"
    if [ "$kind" = "file" ]; then
      echo "+ rm -f $marker"
      [ "$DRY_RUN" -eq 1 ] || rm -f "$marker"
    fi
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "Skipped unrelated installation: $dest"
  else
    echo "Nothing to remove: $dest"
  fi
}

if [ "$DO_CLAUDE" -eq 1 ]; then
  remove_owned "$REPO/.claude/skills/build-html-slides" "$CLAUDE_HOME/skills/build-html-slides" dir
  for agent in "$REPO"/agents/build-html-slides-*.md; do
    remove_owned "$agent" "$CLAUDE_HOME/agents/$(basename "$agent")" file
  done
fi

if [ "$DO_CODEX" -eq 1 ]; then
  remove_owned "$REPO/codex/skills/build-html-slides" "$CODEX_HOME/skills/build-html-slides" dir
fi

if [ "$DO_GEMINI" -eq 1 ]; then
  remove_owned "$REPO/.gemini/skills/build-html-slides" "$GEMINI_HOME/skills/build-html-slides" dir
fi
