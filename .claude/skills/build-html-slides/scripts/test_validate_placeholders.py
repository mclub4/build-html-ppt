#!/usr/bin/env python3
"""Regression tests for the no-placeholder delivery gate."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_placeholders.py"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


class ValidatePlaceholdersTests(unittest.TestCase):
    def validate(self, body: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace("<!-- SLIDE_2_CONTENT -->", body, 1),
                encoding="utf-8",
            )
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_authoring_comments_are_not_visible_placeholders(self) -> None:
        result = self.validate("<p>Finished content</p>")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_place_note_visible_text_is_blocking(self) -> None:
        result = self.validate('<div class="destination-art">PLACE NOTE</div>')
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked PLACE NOTE text", result.stdout)

    def test_placeholder_class_and_asset_filename_are_blocking(self) -> None:
        result = self.validate(
            '<div class="destination-placeholder"><img class="key-visual" '
            'src="assets/kanazawa-placeholder.webp" alt="Kanazawa"></div>'
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("placeholder marker in class", result.stdout)
        self.assertIn("placeholder marker in src", result.stdout)

    def test_korean_temporary_image_instruction_is_blocking(self) -> None:
        result = self.validate("<p>임시 이미지 - 추후 사진 교체</p>")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unfinished Korean media instruction", result.stdout)

    def test_literal_placeholder_discussion_can_be_explicitly_exempted(self) -> None:
        result = self.validate(
            '<p data-placeholder-literal="true">HTML placeholder 속성의 접근성 동작을 비교합니다.</p>'
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_technical_fallback_copy_is_not_mistaken_for_missing_art(self) -> None:
        result = self.validate("<p>Primary database failure triggers the fallback path.</p>")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
