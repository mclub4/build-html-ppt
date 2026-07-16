#!/usr/bin/env python3
"""Install Playwright and Chromium into a user-scoped runtime after explicit consent."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


CONTRACT = json.loads(Path(__file__).with_name("validation_contract.json").read_text(encoding="utf-8"))
PLAYWRIGHT_VERSION = CONTRACT["playwright_version"]


def default_runtime() -> Path:
    configured = os.environ.get("BUILD_HTML_SLIDES_RUNTIME")
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".build-html-slides" / "runtime"


def run(command: list[str]) -> None:
    print("RUN:", " ".join(command))
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--consent",
        action="store_true",
        help="Confirm that the user explicitly approved this dependency installation.",
    )
    parser.add_argument("--runtime-dir", type=Path, default=default_runtime())
    parser.add_argument(
        "--with-deps",
        action="store_true",
        help="Also ask Playwright to install Linux system libraries; may require elevated privileges.",
    )
    args = parser.parse_args()
    if not args.consent:
        parser.error("--consent is required; ask the user before installing software")

    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        parser.error("Node.js and npm must be installed before Playwright")

    runtime = args.runtime_dir.expanduser().resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    run([
        npm,
        "install",
        "--prefix",
        str(runtime),
        "--no-audit",
        "--no-fund",
        "--save-exact",
        f"playwright@{PLAYWRIGHT_VERSION}",
    ])
    cli = runtime / "node_modules" / "playwright" / "cli.js"
    install = [node, str(cli), "install"]
    if args.with_deps:
        install.append("--with-deps")
    install.append("chromium")
    run(install)
    print(f"OK: Playwright {PLAYWRIGHT_VERSION} and Chromium are available under {runtime}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
