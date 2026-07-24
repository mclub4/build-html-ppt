#!/usr/bin/env python3
"""Regression tests for the presenter-notes gate.

This validator ran in the deterministic command set with zero test coverage,
and it disagreed with validate_deck.py about the titles of the same deck.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_speaker_notes.py"
DECK_VALIDATOR = ROOT / "scripts" / "validate_deck.py"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


def notes_for(titles: list[str], bullets: int = 5) -> str:
    body = "\n".join(f"- note bullet {number}" for number in range(1, bullets + 1))
    return "\n\n".join(f"## {index}. {title}\n{body}" for index, title in enumerate(titles, 1)) + "\n"


class ValidateSpeakerNotesTests(unittest.TestCase):
    def validate(self, html: str, notes: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            notes_file = root / "deck-notes.md"
            deck.write_text(html, encoding="utf-8")
            notes_file.write_text(notes, encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck), str(notes_file)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_with_matching_notes_passes(self) -> None:
        result = self.validate(
            TEMPLATE.read_text(encoding="utf-8"),
            notes_for(["Slide 1", "Slide 2", "Slide 3"]),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("3 slide-note sections", result.stdout)

    def test_attribute_order_does_not_change_the_extracted_titles(self) -> None:
        """data-title before class used to make the slide invisible to this gate."""
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<section class="slide" data-title="Slide 2">',
            '<section data-title="Slide 2" class="slide">',
            1,
        )
        result = self.validate(html, notes_for(["Slide 1", "Slide 2", "Slide 3"]))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_attribute_order_still_detects_a_real_title_mismatch(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<section class="slide" data-title="Slide 2">',
            '<section data-title="Slide 2" class="slide">',
            1,
        )
        result = self.validate(html, notes_for(["Slide 1", "Wrong title", "Slide 3"]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("slide 2 title mismatch", result.stdout)

    def test_speaker_notes_agree_with_validate_deck_about_titles(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<section class="slide" data-title="Slide 3">',
            '<section data-title="Slide 3" class="slide">',
            1,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            notes_file = root / "deck-notes.md"
            deck.write_text(html, encoding="utf-8")
            notes_file.write_text(notes_for(["Slide 1", "Slide 2", "Slide 3"]), encoding="utf-8")
            structure = subprocess.run(
                ["python3", str(DECK_VALIDATOR), str(deck)],
                capture_output=True, text=True, check=False,
            )
            notes = subprocess.run(
                ["python3", str(VALIDATOR), str(deck), str(notes_file)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(structure.returncode, 0, structure.stdout + structure.stderr)
        self.assertEqual(notes.returncode, 0, notes.stdout + notes.stderr)

    def test_slide_without_data_title_is_blocking(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<section class="slide" data-title="Slide 2">', '<section class="slide">', 1
        )
        result = self.validate(html, notes_for(["Slide 1", "Slide 3"]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("every slide needs data-title", result.stdout)

    def test_section_count_mismatch_is_blocking(self) -> None:
        result = self.validate(
            TEMPLATE.read_text(encoding="utf-8"), notes_for(["Slide 1", "Slide 2"])
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("notes sections (2) do not match slides (3)", result.stdout)

    def test_thin_note_section_is_blocking(self) -> None:
        result = self.validate(
            TEMPLATE.read_text(encoding="utf-8"),
            notes_for(["Slide 1", "Slide 2", "Slide 3"], bullets=4),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("needs at least five note bullets; found 4", result.stdout)

    def test_out_of_order_numbering_is_blocking(self) -> None:
        notes = notes_for(["Slide 1", "Slide 2", "Slide 3"]).replace("## 2.", "## 4.", 1)
        result = self.validate(TEMPLATE.read_text(encoding="utf-8"), notes)
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected note section 2, found 4", result.stdout)

    def test_missing_notes_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(VALIDATOR), str(deck), str(Path(temporary) / "absent.md")],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("speaker notes not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
