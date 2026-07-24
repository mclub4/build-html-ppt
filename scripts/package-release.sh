#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/package.json")"
ARCHIFY_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/codex/skills/archify/package.json")"
DIST="$ROOT/dist"

python3 "$ROOT/scripts/validate_repository.py"
rm -rf "$DIST"
mkdir -p "$DIST"

python3 - "$ROOT" "$VERSION" "$ARCHIFY_VERSION" <<'PY'
from pathlib import Path
import hashlib
import sys
import zipfile

root = Path(sys.argv[1])
version = sys.argv[2]
archify_version = sys.argv[3]
dist = root / "dist"

def write_tree(output, source, prefix):
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
            output.write(path, prefix / path.relative_to(source))


bundle_archives = [
    (
        dist / f"BUILD-HTML-SLIDES-CODEX-BUNDLE-v{version}.zip",
        [root / "codex/skills/build-html-slides", root / "codex/skills/archify"],
    ),
    (
        dist / f"BUILD-HTML-SLIDES-CLAUDE-BUNDLE-v{version}.zip",
        [root / ".claude/skills/build-html-slides", root / ".claude/skills/archify"],
    ),
    (
        dist / f"BUILD-HTML-SLIDES-GEMINI-BUNDLE-v{version}.zip",
        [root / ".gemini/skills/build-html-slides", root / ".gemini/skills/archify"],
    ),
]

for archive, sources in bundle_archives:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for source in sources:
            write_tree(output, source, Path(source.name))

codex_plugin_archive = dist / f"BUILD-HTML-SLIDES-CODEX-PLUGIN-v{version}.zip"
with zipfile.ZipFile(codex_plugin_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    write_tree(output, root / "plugins/build-html-slides", Path("build-html-slides"))

claude_archive = dist / f"BUILD-HTML-SLIDES-CLAUDE-PLUGIN-v{version}.zip"
with zipfile.ZipFile(claude_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    mappings = [
        (root / ".claude-plugin", Path("build-html-slides/.claude-plugin")),
        (root / ".claude/skills/build-html-slides", Path("build-html-slides/.claude/skills/build-html-slides")),
        (root / ".claude/skills/archify", Path("build-html-slides/.claude/skills/archify")),
        (root / "agents", Path("build-html-slides/agents")),
    ]
    for source, prefix in mappings:
        write_tree(output, source, prefix)
    for filename in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        output.write(root / filename, Path("build-html-slides") / filename)

gemini_source = root / ".gemini/skills/build-html-slides"
gemini_archive = dist / f"BUILD-HTML-SLIDES-GEMINI-v{version}.skill"
with zipfile.ZipFile(gemini_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    write_tree(output, gemini_source, Path("."))

gemini_archify_source = root / ".gemini/skills/archify"
gemini_archify_archive = dist / f"ARCHIFY-GEMINI-v{archify_version}.skill"
with zipfile.ZipFile(gemini_archify_archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    write_tree(output, gemini_archify_source, Path("."))

release_assets = [
    dist / f"BUILD-HTML-SLIDES-CODEX-BUNDLE-v{version}.zip",
    codex_plugin_archive,
    dist / f"BUILD-HTML-SLIDES-CLAUDE-BUNDLE-v{version}.zip",
    claude_archive,
    dist / f"BUILD-HTML-SLIDES-GEMINI-BUNDLE-v{version}.zip",
    gemini_archive,
    gemini_archify_archive,
]
checksum_path = dist / f"build-html-slides-v{version}-sha256.txt"
checksum_path.write_text(
    "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in release_assets
    ),
    encoding="utf-8",
)
PY

printf 'Created:\n  %s\n  %s\n  %s\n  %s\n  %s\n  %s\n  %s\n  %s\n' \
  "$DIST/BUILD-HTML-SLIDES-CODEX-BUNDLE-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CODEX-PLUGIN-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CLAUDE-BUNDLE-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CLAUDE-PLUGIN-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-GEMINI-BUNDLE-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-GEMINI-v$VERSION.skill" \
  "$DIST/ARCHIFY-GEMINI-v$ARCHIFY_VERSION.skill" \
  "$DIST/build-html-slides-v$VERSION-sha256.txt"
