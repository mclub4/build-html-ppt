#!/usr/bin/env python3
"""Tests for canonical slide navigation interactions."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_interactions.py"
TEMPLATE = ROOT / "assets" / "presentation-template.html"


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
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7"/></svg>',
            "←",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("#prev must use an inline SVG icon", result.stdout)


if __name__ == "__main__":
    unittest.main()
