#!/usr/bin/env python3
"""Regression tests for portable WOFF2 validation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_fonts.py"
FIXTURE = ROOT / "scripts" / "fixtures" / "inter-latin-400-normal.woff2"


class ValidateFontsTests(unittest.TestCase):
    def validate(self, html: str, include_font: bool = False) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(html, encoding="utf-8")
            if include_font:
                (root / "assets").mkdir()
                shutil.copy2(FIXTURE, root / "assets" / "inter.woff2")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_visible_text_without_font_face_fails(self) -> None:
        result = self.validate(
            "<!doctype html><html><style>:root{--font-body:Arial,sans-serif}</style>"
            "<body><section class='slide'><p>Portable text</p></section></body></html>"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("bundled WOFF2", result.stdout)

    def test_local_woff2_theme_font_passes(self) -> None:
        result = self.validate(
            "<!doctype html><html><style>"
            "@font-face{font-family:'Test Inter';src:url('assets/inter.woff2') format('woff2');font-weight:400}"
            ":root{--font-display:'Test Inter',sans-serif;--font-body:'Test Inter',sans-serif}"
            "</style><body><section class='slide'><h1>Portable text</h1></section></body></html>",
            include_font=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 bundled WOFF2", result.stdout)

    def test_remote_or_non_woff2_font_fails(self) -> None:
        result = self.validate(
            "<!doctype html><html><style>"
            "@font-face{font-family:'Remote';src:url('https://example.com/font.ttf') format('truetype')}"
            ":root{--font-body:'Remote',sans-serif}"
            "</style><body><section class='slide'><p>Remote text</p></section></body></html>"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("local .woff2", result.stdout)


if __name__ == "__main__":
    unittest.main()
