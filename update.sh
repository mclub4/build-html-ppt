#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
GEMINI_HOME="${GEMINI_HOME:-$HOME/.gemini}"
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

# A clone without a remote (an archive extraction, or a repository initialised
# by hand) has nothing to update from. Say so instead of surfacing a raw
# "'origin' does not appear to be a git repository" from git fetch.
if ! git -C "$REPO" remote get-url "$REMOTE" >/dev/null 2>&1; then
  echo "This checkout has no '$REMOTE' remote, so ./update.sh cannot fetch new commits." >&2
  echo "Configured remotes:" >&2
  if [ -n "$(git -C "$REPO" remote)" ]; then
    git -C "$REPO" remote -v >&2
  else
    echo "  (none)" >&2
  fi
  echo "Add one with: git -C \"$REPO\" remote add $REMOTE https://github.com/mclub4/build-html-ppt.git" >&2
  echo "Or re-clone the repository and run ./install.sh again." >&2
  exit 1
fi

if ! git -C "$REPO" fetch --quiet "$REMOTE"; then
  echo "Could not fetch from '$REMOTE'. Check network access and the remote URL." >&2
  exit 1
fi

if ! git -C "$REPO" rev-parse --verify --quiet "$UPSTREAM" >/dev/null; then
  echo "Upstream branch '$UPSTREAM' does not exist on '$REMOTE'." >&2
  echo "Set a tracking branch with: git -C \"$REPO\" branch --set-upstream-to=$REMOTE/<branch>" >&2
  exit 1
fi

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

CLAUDE_COPY=0
CODEX_COPY=0
GEMINI_COPY=0
if [ -f "$CLAUDE_HOME/skills/build-html-slides/.build-html-slides-copy-origin" ] &&
   [ "$(cat "$CLAUDE_HOME/skills/build-html-slides/.build-html-slides-copy-origin")" = "$REPO" ]; then
  CLAUDE_COPY=1
fi
if [ -f "$CODEX_HOME/skills/build-html-slides/.build-html-slides-copy-origin" ] &&
   [ "$(cat "$CODEX_HOME/skills/build-html-slides/.build-html-slides-copy-origin")" = "$REPO" ]; then
  CODEX_COPY=1
fi
if [ -f "$GEMINI_HOME/skills/build-html-slides/.build-html-slides-copy-origin" ] &&
   [ "$(cat "$GEMINI_HOME/skills/build-html-slides/.build-html-slides-copy-origin")" = "$REPO" ]; then
  GEMINI_COPY=1
fi

git -C "$REPO" pull --ff-only

# A pulled commit can contain .claude/ or .gemini/ copies that drifted from the
# canonical codex/ source. Validate before anything is written into a skills
# directory, so a drifted commit fails loudly instead of installing silently.
if command -v python3 >/dev/null 2>&1 && [ -f "$REPO/scripts/validate_repository.py" ]; then
  if ! python3 "$REPO/scripts/validate_repository.py"; then
    echo "Repository validation failed after the update at $(git -C "$REPO" rev-parse --short HEAD)." >&2
    echo "Nothing was reinstalled; the previously installed skills are untouched." >&2
    echo "Run ./scripts/sync-distributions.sh, or report the drifted commit upstream." >&2
    exit 1
  fi
else
  echo "python3 or scripts/validate_repository.py is unavailable; installing without verifying distribution parity." >&2
fi

# Validation already ran here; skip the installer's own pass instead of hashing
# every distribution file three more times.
if [ "$CLAUDE_COPY" -eq 1 ]; then
  "$REPO/install.sh" --copy --claude-only --skip-validation
fi
if [ "$CODEX_COPY" -eq 1 ]; then
  "$REPO/install.sh" --copy --codex-only --skip-validation
fi
if [ "$GEMINI_COPY" -eq 1 ]; then
  "$REPO/install.sh" --copy --gemini-only --skip-validation
fi

echo "Updated to $(git -C "$REPO" rev-parse --short HEAD). Reload plugins or start a new Claude/Codex/Gemini session."
