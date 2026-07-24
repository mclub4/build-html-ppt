#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SOURCE="$REPO/.claude/skills/build-html-slides"
CLAUDE_ARCHIFY_SOURCE="$REPO/.claude/skills/archify"
CODEX_SOURCE="$REPO/codex/skills/build-html-slides"
CODEX_ARCHIFY_SOURCE="$REPO/codex/skills/archify"
GEMINI_SOURCE="$REPO/.gemini/skills/build-html-slides"
GEMINI_ARCHIFY_SOURCE="$REPO/.gemini/skills/archify"
CLAUDE_HOME="${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
# The bundled Archify version is derived, never restated. codex/skills/archify/package.json
# is the single source of truth and scripts/validate_repository.py asserts it everywhere.
ARCHIFY_PACKAGE="$REPO/codex/skills/archify/package.json"
MODE="symlink"
DO_CLAUDE="auto"
DO_CODEX="auto"
DO_GEMINI="auto"
FORCE=0
DRY_RUN=0
SKIP_VALIDATION="${BUILD_HTML_SLIDES_SKIP_VALIDATION:-0}"
STAMP="$(date +%Y%m%d-%H%M%S)"
# Backups live outside every skills scan root. A backup kept beside the skill
# would be discovered as a second skill declaring the same name.
BACKUP_DIRNAME=".build-html-slides-backups"

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install the build-html-slides + Archify skill bundle for detected Claude Code,
Codex, and Gemini CLIs.

Options:
  --copy             Copy files instead of linking them to this clone.
  --claude-only      Install only the Claude Code skills and review agents.
  --codex-only       Install only the Codex skills.
  --gemini-only      Install only the Gemini CLI Agent Skills.
  --force            Back up an unrelated existing installation and replace it.
  --dry-run          Print actions without changing files.
  --skip-validation  Skip the pre-install repository validation. Use only in an
                     offline or minimal environment without python3. Installing
                     with this flag can deliver .claude/ or .gemini/ copies that
                     have drifted from the canonical codex/ source.
  -h, --help         Show this help.

Environment:
  CLAUDE_HOME or CLAUDE_CONFIG_DIR   Claude home directory (default: ~/.claude)
  CODEX_HOME                        Codex home directory (default: ~/.codex)
  GEMINI_HOME                       Gemini home directory (default: ~/.gemini)
  BUILD_HTML_SLIDES_SKIP_VALIDATION Set to 1 for the same effect as --skip-validation.

Before installing, this script runs scripts/validate_repository.py so that the
derived .claude/ and .gemini/ copies are proven identical to the canonical
codex/ source. Existing unrelated installations replaced with --force are moved
to <home>/.build-html-slides-backups/, outside the skills scan root.

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
    --skip-validation) SKIP_VALIDATION=1 ;;
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

# Every destructive path in this script flows through here. A destination must
# be absolute, must not be the filesystem root, and must be at least two levels
# below it, so an empty or truncated home directory can never expand into a
# recursive delete of / or of a top-level directory.
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
  # Require at least two path segments, e.g. /home/user/... never /skills.
  case "${trimmed#/}" in
    */*) ;;
    *) echo "Refusing to operate on a top-level path: '$target'" >&2; exit 1 ;;
  esac
}

archify_version() {
  if [ ! -f "$ARCHIFY_PACKAGE" ]; then
    echo "Bundled Archify package metadata is missing: $ARCHIFY_PACKAGE" >&2
    exit 1
  fi
  sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ARCHIFY_PACKAGE" | head -n 1
}

validate_repository() {
  local validator="$REPO/scripts/validate_repository.py"
  if [ "$SKIP_VALIDATION" = "1" ]; then
    echo "Skipping repository validation (--skip-validation)."
    echo "The .claude/ and .gemini/ copies are installed unverified; run ./scripts/sync-distributions.sh if they drifted." >&2
    return 0
  fi
  if [ ! -f "$validator" ]; then
    echo "Repository validator is missing: $validator" >&2
    echo "Re-clone the repository, or rerun with --skip-validation to install unverified." >&2
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required to verify that the Claude and Gemini copies match the canonical codex/ source." >&2
    echo "Install python3, or rerun with --skip-validation to install unverified." >&2
    exit 1
  fi
  echo "== Verifying distributions against the canonical codex/ source =="
  if ! python3 "$validator"; then
    echo "Repository validation failed. The installable copies do not match codex/skills/." >&2
    echo "Run ./scripts/sync-distributions.sh, or rerun with --skip-validation to install anyway." >&2
    exit 1
  fi
}

validate_repository
ARCHIFY_VERSION="$(archify_version)"
if [ -z "$ARCHIFY_VERSION" ]; then
  echo "Could not read the bundled Archify version from $ARCHIFY_PACKAGE" >&2
  exit 1
fi

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

# Claude Code, Codex, and Gemini all discover skills by scanning every
# subdirectory of <home>/skills for SKILL.md. A backup left at
# <home>/skills/<name>.bak.<stamp> therefore registers as a second skill
# declaring the same name, colliding with the one just installed, and
# uninstall.sh has no way to recognise it. Backups go to
# <home>/.build-html-slides-backups/<category>/, one level above the scan root.
backup_path_for() {
  local dest="$1" home category name
  home="$(dirname "$(dirname "$dest")")"
  category="$(basename "$(dirname "$dest")")"
  name="$(basename "$dest")"
  printf '%s\n' "$home/$BACKUP_DIRNAME/$category/$name.bak.$STAMP"
}

prepare_destination() {
  local dest="$1" source="$2" kind="$3" marker backup
  marker="$(copy_marker "$dest" "$kind")"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; then
    if [ "$MODE" = "symlink" ]; then
      return 1
    fi
    run rm "$dest"
    return 0
  fi

  if is_our_copy "$dest" "$kind"; then
    assert_safe_target "$dest"
    run rm -rf "$dest"
    [ "$kind" = "file" ] && run rm -f "$marker"
    return 0
  fi

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    backup="$(backup_path_for "$dest")"
    if [ "$FORCE" -ne 1 ]; then
      echo "Refusing to replace existing installation: $dest" >&2
      echo "Use --force to move it to $backup first." >&2
      exit 1
    fi
    run mkdir -p "$(dirname "$backup")"
    run mv "$dest" "$backup"
    echo "Backed up existing installation to: $backup"
  fi
}

# cp -R would deliver __pycache__, .pyc, .pytest_cache, and .omc session state
# into the user's home. tar is used instead of rsync so the installer keeps
# working on a minimal system that has no rsync.
COPY_EXCLUDES=(
  --exclude=__pycache__
  --exclude=.pytest_cache
  --exclude=.omc
  --exclude=.git
  --exclude='*.pyc'
  --exclude='*.pyo'
  --exclude=.DS_Store
)

copy_tree() {
  local source="$1" dest="$2"
  printf '+ copy tree (excluding %s): %q -> %q\n' \
    "__pycache__, .pytest_cache, .omc, .git, *.pyc, *.pyo, .DS_Store" "$source" "$dest"
  [ "$DRY_RUN" -eq 1 ] && return 0
  mkdir -p "$dest"
  tar -C "$source" "${COPY_EXCLUDES[@]}" -cf - . | tar -C "$dest" -xf -
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
    copy_tree "$source" "$dest"
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

install_bundled_archify() {
  local source="$1" dest="$2"
  if { [ -e "$dest" ] || [ -L "$dest" ]; } &&
     ! { [ -L "$dest" ] && [ "$(readlink "$dest")" = "$source" ]; } &&
     ! is_our_copy "$dest" dir &&
     [ "$FORCE" -ne 1 ]; then
    echo "Bundled Archify skipped; existing installation preserved: $dest"
    return
  fi
  install_path "$source" "$dest" dir
}

installed_any=0
installed_claude=0
installed_codex=0
installed_gemini=0
if [ "$DO_CLAUDE" = "yes" ] || { [ "$DO_CLAUDE" = "auto" ] && command -v claude >/dev/null 2>&1; }; then
  echo "== Claude Code =="
  install_path "$CLAUDE_SOURCE" "$CLAUDE_HOME/skills/build-html-slides" dir
  install_bundled_archify "$CLAUDE_ARCHIFY_SOURCE" "$CLAUDE_HOME/skills/archify"
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
  install_bundled_archify "$CODEX_ARCHIFY_SOURCE" "$CODEX_HOME/skills/archify"
  installed_any=1
  installed_codex=1
elif [ "$DO_CODEX" = "auto" ]; then
  echo "== Codex: skipped (codex not found) =="
fi

if [ "$DO_GEMINI" = "yes" ] || { [ "$DO_GEMINI" = "auto" ] && command -v gemini >/dev/null 2>&1; }; then
  echo "== Gemini CLI =="
  install_path "$GEMINI_SOURCE" "$GEMINI_HOME/skills/build-html-slides" dir
  install_bundled_archify "$GEMINI_ARCHIFY_SOURCE" "$GEMINI_HOME/skills/archify"
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
echo "- Bundled technical diagrams: tt-a1i/archify v$ARCHIFY_VERSION is included as an independent skill for architecture, topology, sequence, workflow, lifecycle, and data-flow diagrams. It ships with the supported distributions and needs no separate consent."
echo "- The installer preserves an unrelated existing Archify installation unless --force was explicitly supplied."
echo "- AI installer: ask whether to install im-not-ai only when humanize-korean is missing. Do not install it or any additional dependency without explicit consent."
echo "- Available humanize-korean and bundled Archify are used automatically when their routing rules match; do not ask again before each deck."
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
