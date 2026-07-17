#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SOURCE="$REPO/.claude/skills/build-html-slides"
CODEX_SOURCE="$REPO/codex/skills/build-html-slides"
GEMINI_SOURCE="$REPO/.gemini/skills/build-html-slides"
CLAUDE_HOME="${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
MODE="symlink"
DO_CLAUDE="auto"
DO_CODEX="auto"
DO_GEMINI="auto"
FORCE=0
DRY_RUN=0
STAMP="$(date +%Y%m%d-%H%M%S)"

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install build-html-slides for detected Claude Code, Codex, and Gemini CLIs.

Options:
  --copy         Copy files instead of linking them to this clone.
  --claude-only  Install only the Claude Code skill and review agents.
  --codex-only   Install only the Codex skill.
  --gemini-only  Install only the Gemini CLI Agent Skill.
  --force        Back up an unrelated existing installation and replace it.
  --dry-run      Print actions without changing files.
  -h, --help     Show this help.

Environment:
  CLAUDE_HOME or CLAUDE_CONFIG_DIR  Claude home directory (default: ~/.claude)
  CODEX_HOME                       Codex home directory (default: ~/.codex)
  GEMINI_HOME                      Gemini home directory (default: ~/.gemini)

Install either a standalone skill or that platform's marketplace plugin, not both.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --copy) MODE="copy" ;;
    --claude-only) DO_CLAUDE="yes"; DO_CODEX="no"; DO_GEMINI="no" ;;
    --codex-only) DO_CLAUDE="no"; DO_CODEX="yes"; DO_GEMINI="no" ;;
    --gemini-only) DO_CLAUDE="no"; DO_CODEX="no"; DO_GEMINI="yes" ;;
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
installed_claude=0
installed_codex=0
installed_gemini=0
if [ "$DO_CLAUDE" = "yes" ] || { [ "$DO_CLAUDE" = "auto" ] && command -v claude >/dev/null 2>&1; }; then
  echo "== Claude Code =="
  install_path "$CLAUDE_SOURCE" "$CLAUDE_HOME/skills/build-html-slides" dir
  for agent in "$REPO"/agents/build-html-slides-*.md; do
    install_path "$agent" "$CLAUDE_HOME/agents/$(basename "$agent")" file
  done
  installed_any=1
  installed_claude=1
elif [ "$DO_CLAUDE" = "auto" ]; then
  echo "== Claude Code: skipped (claude not found) =="
fi

if [ "$DO_CODEX" = "yes" ] || { [ "$DO_CODEX" = "auto" ] && command -v codex >/dev/null 2>&1; }; then
  echo "== Codex =="
  install_path "$CODEX_SOURCE" "$CODEX_HOME/skills/build-html-slides" dir
  installed_any=1
  installed_codex=1
elif [ "$DO_CODEX" = "auto" ]; then
  echo "== Codex: skipped (codex not found) =="
fi

if [ "$DO_GEMINI" = "yes" ] || { [ "$DO_GEMINI" = "auto" ] && command -v gemini >/dev/null 2>&1; }; then
  echo "== Gemini CLI =="
  install_path "$GEMINI_SOURCE" "$GEMINI_HOME/skills/build-html-slides" dir
  installed_any=1
  installed_gemini=1
elif [ "$DO_GEMINI" = "auto" ]; then
  echo "== Gemini CLI: skipped (gemini not found) =="
fi

if [ "$installed_any" -eq 0 ]; then
  echo "No target selected or supported CLI detected." >&2
  exit 1
fi

if [ "$installed_claude" -eq 1 ]; then
  echo "Claude Code: start a new session and invoke /build-html-slides."
fi
if [ "$installed_codex" -eq 1 ]; then
  echo "Codex: start a new task and invoke \$build-html-slides."
fi
if [ "$installed_gemini" -eq 1 ]; then
  echo "Gemini CLI: start a new session, approve Agent Skill activation, and request an HTML presentation in natural language."
fi
echo
echo "Post-install guidance:"
echo "- Optional Korean polish: epoko77-ai/im-not-ai provides humanize-korean for slide copy and presenter notes after facts, numbers, names, and citations are settled. It is not bundled or installed automatically."
echo "- After installing im-not-ai separately, invoke /humanize-korean in Claude Code or \$humanize-korean in Codex; Codex uses its Fast single-call mode."
echo "- Optional technical diagrams: tt-a1i/archify creates self-contained HTML architecture, topology, ERD, UML, sequence, workflow, lifecycle, and complex-flow diagrams with inline SVG and export controls."
echo "- AI installer: check which companions are missing, then ask whether to install im-not-ai and/or archify. Do not install either companion or any dependency without explicit consent."
if [ "$installed_claude" -eq 1 ]; then
  echo "- Claude Code can inspect rendered images but does not include a raster image generator by default. Connect a compatible image-generation plugin, MCP server, or external tool separately if generated imagery is needed."
  echo "- Do not install or configure an image generator, credentials, or a paid service without explicit user consent. The slide skill still works without one."
fi
if [ "$installed_codex" -eq 1 ]; then
  echo "- Codex can use ImageGen only when the current Codex environment exposes it; image generation is optional."
fi
if [ "$installed_gemini" -eq 1 ]; then
  echo "- Gemini CLI Agent Skills activate from matching natural-language requests after user consent; use /skills list or /skills reload to inspect discovery state."
  echo "- Gemini CLI image generation depends on the tools or extensions available in the current session. Do not add a generator, extension, credentials, or paid service without explicit consent."
fi
