#!/usr/bin/env python3
"""Tests for canonical slide navigation interactions."""

from __future__ import annotations

import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_interactions.py"
BROWSER_VALIDATOR = ROOT / "scripts" / "validate_browser_e2e.js"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


class InteractionTests(unittest.TestCase):
    def validate(self, html: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(html, encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_navigation_passes(self) -> None:
        result = self.validate(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_text_arrow_navigation_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
            "←",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("#prev must use an inline SVG icon", result.stdout)

    def run_browser(self, html: str) -> subprocess.CompletedProcess[str]:
        if shutil.which("node") is None:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(html, encoding="utf-8")
            return subprocess.run(
                ["node", str(BROWSER_VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_navigation_and_print_pass_browser_e2e(self) -> None:
        result = self.run_browser(TEMPLATE.read_text(encoding="utf-8"))
        if "Playwright is not installed" in result.stderr:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("print layout passed E2E", result.stdout)

    def test_broken_next_handler_fails_browser_e2e(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "next.addEventListener('click', () => show(index + 1));",
            "next.addEventListener('click', () => {});",
            1,
        )
        result = self.run_browser(html)
        if "Playwright is not installed" in result.stderr:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 1)
        self.assertIn("next button produced inconsistent navigation state", result.stderr)


if __name__ == "__main__":
    unittest.main()
