#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$REPO/codex/skills/build-html-slides"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST="$CODEX_HOME/skills/build-html-slides"
MODE="symlink"
FORCE=0
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install the standalone build-html-slides skill for Codex.

Options:
  --copy      Copy the skill instead of linking it to this clone.
  --force     Back up an unrelated existing installation and replace it.
  --dry-run   Print actions without changing files.
  -h, --help  Show this help.

Environment:
  CODEX_HOME  Codex home directory (default: ~/.codex)

Install either this standalone skill or the Codex plugin, not both.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy) MODE="copy" ;;
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

run() {
  printf '+ '
  printf '%q ' "$@"
  printf '\n'
  [ "$DRY_RUN" -eq 1 ] || "$@"
}

is_our_copy() {
  [ -f "$DEST/.build-html-slides-copy-origin" ] &&
    [ "$(cat "$DEST/.build-html-slides-copy-origin")" = "$REPO" ]
}

prepare_destination() {
  if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SOURCE" ]; then
    [ "$MODE" = "symlink" ] && return 1
    run rm "$DEST"
    return 0
  fi

  if is_our_copy; then
    [ "$MODE" = "copy" ] && run rm -rf "$DEST" && return 0
  fi

  if [ -e "$DEST" ] || [ -L "$DEST" ]; then
    if [ "$FORCE" -ne 1 ]; then
      echo "Refusing to replace existing installation: $DEST" >&2
      echo "Use --force to move it to $DEST.bak.$STAMP first." >&2
      exit 1
    fi
    run mv "$DEST" "$DEST.bak.$STAMP"
  fi
}

run mkdir -p "$CODEX_HOME/skills"
if prepare_destination; then
  if [ "$MODE" = "symlink" ]; then
    run ln -s "$SOURCE" "$DEST"
  else
    run cp -R "$SOURCE" "$DEST"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ write copy marker: $DEST/.build-html-slides-copy-origin"
    else
      printf '%s\n' "$REPO" > "$DEST/.build-html-slides-copy-origin"
    fi
  fi
  echo "Installed: $DEST ($MODE)"
else
  echo "Already installed: $DEST"
fi

echo "Start a new Codex task, then invoke \$build-html-slides or ask for an HTML presentation."

