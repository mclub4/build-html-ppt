#!/usr/bin/env python3
"""Check slide-rendering dependencies without installing or changing anything."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


MIN_PYTHON = (3, 10)
MIN_NODE = 18


def parse_node_major(version: str) -> int | None:
    match = re.search(r"v?(\d+)", version.strip())
    return int(match.group(1)) if match else None


def inspect_environment(
    *,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    suggestions: list[str] = []

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    python_ok = sys.version_info[:2] >= MIN_PYTHON
    checks.append({
        "name": "python",
        "status": "pass" if python_ok else "fail",
        "detail": f"Python {python_version}" if python_ok else f"Python {python_version}; 3.10 or newer is required",
    })
    if not python_ok:
        suggestions.append("Install Python 3.10 or newer.")

    node = which("node")
    node_ok = False
    if node:
        result = run([node, "--version"], capture_output=True, text=True, check=False, timeout=30)
        version = (result.stdout or result.stderr).strip()
        major = parse_node_major(version)
        node_ok = result.returncode == 0 and major is not None and major >= MIN_NODE
        detail = version or "version unavailable"
        if not node_ok:
            detail = f"{detail}; Node.js {MIN_NODE} or newer is required"
    else:
        detail = "Node.js was not found"
    checks.append({"name": "node", "status": "pass" if node_ok else "fail", "detail": detail})
    if not node_ok:
        suggestions.append(f"Install Node.js {MIN_NODE} or newer.")

    if node_ok:
        renderer = Path(__file__).with_name("render_slides.js")
        result = run(
            [node, str(renderer), "--check"],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        browser_ok = result.returncode == 0
        detail = (result.stdout if browser_ok else result.stderr or result.stdout).strip()
        checks.append({
            "name": "playwright_chromium",
            "status": "pass" if browser_ok else "fail",
            "detail": detail or "Playwright/Chromium check returned no detail",
        })
        if not browser_ok:
            suggestions.append("Install project packages, then install Chromium with Playwright.")
    else:
        checks.append({
            "name": "playwright_chromium",
            "status": "blocked",
            "detail": "Cannot check Playwright or Chromium until Node.js is available",
        })

    ready = all(check["status"] == "pass" for check in checks)
    return {"ready": ready, "checks": checks, "installation_suggestions": suggestions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    result = inspect_environment()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in result["checks"]:
            label = "OK" if check["status"] == "pass" else check["status"].upper()
            print(f"{label}: {check['name']} - {check['detail']}")
        if result["installation_suggestions"]:
            print("Installation requires user confirmation:")
            for suggestion in result["installation_suggestions"]:
                print(f"- {suggestion}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
