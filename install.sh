#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SOURCE="$REPO/.claude/skills/build-html-slides"
CODEX_SOURCE="$REPO/codex/skills/build-html-slides"
CLAUDE_HOME="${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
MODE="symlink"
DO_CLAUDE="auto"
DO_CODEX="auto"
FORCE=0
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install build-html-slides for detected Claude Code and Codex CLIs.

Options:
  --copy         Copy files instead of linking them to this clone.
  --claude-only  Install only the Claude Code skill and review agents.
  --codex-only   Install only the Codex skill.
  --force        Back up an unrelated existing installation and replace it.
  --dry-run      Print actions without changing files.
  -h, --help     Show this help.

Environment:
  CLAUDE_HOME or CLAUDE_CONFIG_DIR  Claude home directory (default: ~/.claude)
  CODEX_HOME                       Codex home directory (default: ~/.codex)

Install either a standalone skill or that platform's marketplace plugin, not both.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy) MODE="copy" ;;
    --claude-only) DO_CLAUDE="yes"; DO_CODEX="no" ;;
    --codex-only) DO_CLAUDE="no"; DO_CODEX="yes" ;;
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

copy_marker() {
  local dest="$1" kind="$2"
  if [ "$kind" = "dir" ]; then
    printf '%s\n' "$dest/.build-html-slides-copy-origin"
  else
    printf '%s\n' "$dest.build-html-slides-origin"
  fi
}

is_our_copy() {
  local dest="$1" kind="$2" marker
  marker="$(copy_marker "$dest" "$kind")"
  [ -f "$marker" ] && [ "$(cat "$marker")" = "$REPO" ]
}

prepare_destination() {
  local dest="$1" source="$2" kind="$3" marker
  marker="$(copy_marker "$dest" "$kind")"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; then
    if [ "$MODE" = "symlink" ]; then
      return 1
    fi
    run rm "$dest"
    return 0
  fi

  if is_our_copy "$dest" "$kind"; then
    run rm -rf "$dest"
    [ "$kind" = "file" ] && run rm -f "$marker"
    return 0
  fi

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" -ne 1 ]; then
      echo "Refusing to replace existing installation: $dest" >&2
      echo "Use --force to move it to $dest.bak.$STAMP first." >&2
      exit 1
    fi
    run mv "$dest" "$dest.bak.$STAMP"
  fi
}

install_path() {
  local source="$1" dest="$2" kind="$3" marker
  run mkdir -p "$(dirname "$dest")"
  if ! prepare_destination "$dest" "$source" "$kind"; then
    echo "Already installed: $dest"
    return
  fi

  if [ "$MODE" = "symlink" ]; then
    run ln -s "$source" "$dest"
  elif [ "$kind" = "dir" ]; then
    run cp -R "$source" "$dest"
    marker="$(copy_marker "$dest" "$kind")"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ write copy marker: $marker"
    else
      printf '%s\n' "$REPO" > "$marker"
    fi
  else
    run cp "$source" "$dest"
    marker="$(copy_marker "$dest" "$kind")"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ write copy marker: $marker"
    else
      printf '%s\n' "$REPO" > "$marker"
    fi
  fi
  echo "Installed: $dest ($MODE)"
}

installed_any=0
if [ "$DO_CLAUDE" = "yes" ] || { [ "$DO_CLAUDE" = "auto" ] && command -v claude >/dev/null 2>&1; }; then
  echo "== Claude Code =="
  install_path "$CLAUDE_SOURCE" "$CLAUDE_HOME/skills/build-html-slides" dir
  for agent in "$REPO"/agents/build-html-slides-*.md; do
    install_path "$agent" "$CLAUDE_HOME/agents/$(basename "$agent")" file
  done
  installed_any=1
elif [ "$DO_CLAUDE" = "auto" ]; then
  echo "== Claude Code: skipped (claude not found) =="
fi

if [ "$DO_CODEX" = "yes" ] || { [ "$DO_CODEX" = "auto" ] && command -v codex >/dev/null 2>&1; }; then
  echo "== Codex =="
  install_path "$CODEX_SOURCE" "$CODEX_HOME/skills/build-html-slides" dir
  installed_any=1
elif [ "$DO_CODEX" = "auto" ]; then
  echo "== Codex: skipped (codex not found) =="
fi

if [ "$installed_any" -eq 0 ]; then
  echo "No target selected or supported CLI detected." >&2
  exit 1
fi

echo "Claude Code: start a new session and invoke /build-html-slides."
echo "Codex: start a new task and invoke \$build-html-slides."
