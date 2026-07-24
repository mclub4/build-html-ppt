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
PURGE_BACKUPS=0
BACKUP_DIRNAME=".build-html-slides-backups"

usage() {
  cat <<'EOF'
Usage: ./uninstall.sh [--claude-only|--codex-only|--gemini-only] [--purge-backups] [--dry-run]

  --purge-backups  Also delete the <home>/.build-html-slides-backups/ trees that
                   ./install.sh --force created. Without this flag the backups
                   are left in place and reported.
  --dry-run        Print actions without changing files.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --claude-only) DO_CLAUDE=1; DO_CODEX=0; DO_GEMINI=0 ;;
    --codex-only) DO_CLAUDE=0; DO_CODEX=1; DO_GEMINI=0 ;;
    --gemini-only) DO_CLAUDE=0; DO_CODEX=0; DO_GEMINI=1 ;;
    --purge-backups) PURGE_BACKUPS=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# Guards every rm -rf below: an absolute path at least two segments deep, so an
# empty or truncated home directory can never expand into a delete of / or of a
# top-level directory.
assert_safe_target() {
  local target="$1" trimmed
  case "$target" in
    /*) ;;
    *) echo "Refusing to operate on a non-absolute path: '$target'" >&2; exit 1 ;;
  esac
  trimmed="${target%/}"
  if [ -z "$trimmed" ] || [ "$trimmed" = "/" ]; then
    echo "Refusing to operate on the filesystem root: '$target'" >&2
    exit 1
  fi
  case "${trimmed#/}" in
    */*) ;;
    *) echo "Refusing to operate on a top-level path: '$target'" >&2; exit 1 ;;
  esac
}

handle_backups() {
  # Separate statements: bash expands every argument of `local` before it
  # assigns any of them, so "$home" would still be unbound on one line.
  local home="$1"
  local label="$2"
  local root="$home/$BACKUP_DIRNAME"
  [ -d "$root" ] || return 0
  if [ "$PURGE_BACKUPS" -eq 1 ]; then
    assert_safe_target "$root"
    echo "+ rm -rf $root"
    [ "$DRY_RUN" -eq 1 ] || rm -rf "$root"
    return 0
  fi
  echo "$label backups left in place: $root"
  find "$root" -mindepth 2 -maxdepth 2 -print 2>/dev/null | sed 's/^/  - /' || true
  echo "  Re-run with --purge-backups to delete them."
}

remove_owned() {
  local source="$1" dest="$2" kind="$3" marker
  if [ "$kind" = "dir" ]; then
    marker="$dest/.build-html-slides-copy-origin"
  else
    marker="$dest.build-html-slides-origin"
  fi

  if { [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; } ||
     { [ -f "$marker" ] && [ "$(cat "$marker")" = "$REPO" ]; }; then
    assert_safe_target "$dest"
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
  remove_owned "$REPO/.claude/skills/archify" "$CLAUDE_HOME/skills/archify" dir
  for agent in "$REPO"/agents/build-html-slides-*.md; do
    remove_owned "$agent" "$CLAUDE_HOME/agents/$(basename "$agent")" file
  done
  handle_backups "$CLAUDE_HOME" "Claude Code"
fi

if [ "$DO_CODEX" -eq 1 ]; then
  remove_owned "$REPO/codex/skills/build-html-slides" "$CODEX_HOME/skills/build-html-slides" dir
  remove_owned "$REPO/codex/skills/archify" "$CODEX_HOME/skills/archify" dir
  handle_backups "$CODEX_HOME" "Codex"
fi

if [ "$DO_GEMINI" -eq 1 ]; then
  remove_owned "$REPO/.gemini/skills/build-html-slides" "$GEMINI_HOME/skills/build-html-slides" dir
  remove_owned "$REPO/.gemini/skills/archify" "$GEMINI_HOME/skills/archify" dir
  handle_backups "$GEMINI_HOME" "Gemini CLI"
fi
