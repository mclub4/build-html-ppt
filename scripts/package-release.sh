#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/package.json")"
DIST="$ROOT/dist"

python3 "$ROOT/scripts/validate_repository.py"
rm -rf "$DIST"
mkdir -p "$DIST"

python3 - "$ROOT" "$VERSION" <<'PY'
from pathlib import Path
import sys
import zipfile

root = Path(sys.argv[1])
version = sys.argv[2]
dist = root / "dist"

archives = [
    (root / "codex/skills/build-html-slides", dist / f"BUILD-HTML-SLIDES-CODEX-SKILL-v{version}.zip"),
    (root / "plugins/build-html-slides", dist / f"BUILD-HTML-SLIDES-CODEX-PLUGIN-v{version}.zip"),
    (root / ".claude/skills/build-html-slides", dist / f"BUILD-HTML-SLIDES-CLAUDE-SKILL-v{version}.zip"),
    (root / ".gemini/skills/build-html-slides", dist / f"BUILD-HTML-SLIDES-GEMINI-SKILL-v{version}.zip"),
]

for source, archive in archives:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
                output.write(path, Path(source.name) / path.relative_to(source))

claude_archive = dist / f"BUILD-HTML-SLIDES-CLAUDE-PLUGIN-v{version}.zip"
with zipfile.ZipFile(claude_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    mappings = [
        (root / ".claude-plugin", Path("build-html-slides/.claude-plugin")),
        (root / ".claude/skills/build-html-slides", Path("build-html-slides/.claude/skills/build-html-slides")),
        (root / "agents", Path("build-html-slides/agents")),
    ]
    for source, prefix in mappings:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
                output.write(path, prefix / path.relative_to(source))
    for filename in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        output.write(root / filename, Path("build-html-slides") / filename)

gemini_source = root / ".gemini/skills/build-html-slides"
gemini_archive = dist / f"BUILD-HTML-SLIDES-GEMINI-v{version}.skill"
with zipfile.ZipFile(gemini_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    for path in sorted(gemini_source.rglob("*")):
        if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
            output.write(path, path.relative_to(gemini_source))
PY

printf 'Created:\n  %s\n  %s\n  %s\n  %s\n  %s\n  %s\n' \
  "$DIST/BUILD-HTML-SLIDES-CODEX-SKILL-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CODEX-PLUGIN-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CLAUDE-SKILL-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CLAUDE-PLUGIN-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-GEMINI-SKILL-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-GEMINI-v$VERSION.skill"
