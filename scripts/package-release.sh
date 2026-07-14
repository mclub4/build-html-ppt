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
]

for source, archive in archives:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts:
                output.write(path, Path(source.name) / path.relative_to(source))
PY

printf 'Created:\n  %s\n  %s\n' \
  "$DIST/BUILD-HTML-SLIDES-CODEX-SKILL-v$VERSION.zip" \
  "$DIST/BUILD-HTML-SLIDES-CODEX-PLUGIN-v$VERSION.zip"
