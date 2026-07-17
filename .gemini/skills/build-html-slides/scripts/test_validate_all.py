#!/usr/bin/env python3
"""End-to-end tests for the single validation entrypoint."""

from __future__ import annotations

import subprocess
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_all import classify_change_scope, deterministic_commands


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "validate_all.py"
PREFLIGHT = ROOT / "scripts" / "check_environment.py"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


def notes() -> str:
    sections = []
    for number in range(1, 4):
        sections.append(
            f"## {number}. Slide {number}\n\n"
            "- 핵심 메시지\n- 설명 근거\n- 전환 문장\n- 청중 질문\n- 다음 장 연결\n"
        )
    return "\n".join(sections)


class ValidateAllTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check = subprocess.run(
            ["python3", str(PREFLIGHT)], capture_output=True, text=True, check=False
        )
        if check.returncode:
            raise unittest.SkipTest(check.stdout + check.stderr)

    def test_prepare_runs_every_deterministic_gate_and_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace('<html lang="ko">', '<html lang="en">', 1),
                encoding="utf-8",
            )
            notes_path = root / "deck-notes.md"
            notes_path.write_text(notes(), encoding="utf-8")
            review = root / "review"
            result = subprocess.run(
                [
                    "python3", str(ENTRYPOINT), str(deck), "--phase", "prepare", "--mode", "quick",
                    "--notes", str(notes_path), "--review-dir", str(review),
                    "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: browser interaction and print E2E", result.stdout)
            self.assertIn("PASS: Chromium render and geometry gate", result.stdout)
            self.assertTrue((review / "review.json").is_file())

    def test_prepare_requires_user_approved_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(ENTRYPOINT), str(deck), "--phase", "prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--mode quick|full is required", result.stderr)

    def test_prepare_blocks_place_note_before_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<div class="destination-art">PLACE NOTE</div><h2>가나자와</h2>',
                    1,
                ),
                encoding="utf-8",
            )
            notes_path = root / "deck-notes.md"
            notes_path.write_text(notes(), encoding="utf-8")
            review = root / "review"
            result = subprocess.run(
                [
                    "python3", str(ENTRYPOINT), str(deck), "--phase", "prepare", "--mode", "quick",
                    "--notes", str(notes_path), "--review-dir", str(review),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("blocked PLACE NOTE text", result.stdout)
            self.assertIn("placeholder and incomplete-asset gate failed", result.stderr)
            self.assertFalse((review / "review.json").exists())

    def test_incremental_change_types_skip_unrelated_expensive_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text('<!doctype html><html><body></body></html>', encoding="utf-8")
            notes_path = root / "deck-notes.md"
            sources = root / "sources.json"
            text_labels = {label for label, _command in deterministic_commands(deck, notes_path, sources, "text")}
            navigation_labels = {
                label for label, _command in deterministic_commands(deck, notes_path, sources, "navigation")
            }
            image_labels = {label for label, _command in deterministic_commands(deck, notes_path, sources, "image")}
            style_labels = {
                label for label, _command in deterministic_commands(
                    deck, notes_path, sources, "all", content_changes=["style"]
                )
            }
            structure_labels = {
                label for label, _command in deterministic_commands(
                    deck, notes_path, sources, "all", content_changes=["structure"]
                )
            }
            self.assertNotIn("browser interaction and print E2E", text_labels)
            self.assertNotIn("image reuse", text_labels)
            self.assertIn("placeholder and incomplete-asset gate", text_labels)
            self.assertIn("browser interaction and print E2E", navigation_labels)
            self.assertIn("placeholder and incomplete-asset gate", navigation_labels)
            self.assertNotIn("presenter notes", navigation_labels)
            self.assertIn("source locality", image_labels)
            self.assertNotIn("source locality", text_labels)
            self.assertEqual(
                style_labels,
                {"deck structure", "placeholder and incomplete-asset gate"},
            )
            self.assertIn("presenter notes", structure_labels)
            self.assertNotIn("source locality", structure_labels)
            self.assertNotIn("browser interaction and print E2E", structure_labels)

    def test_incremental_prepare_widens_a_misdeclared_text_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8")
                .replace('<html lang="ko">', '<html lang="en">', 1)
                .replace("<!-- SLIDE_2_CONTENT -->", "<h2>Initial structure</h2>", 1),
                encoding="utf-8",
            )
            notes_path = root / "deck-notes.md"
            notes_path.write_text(notes(), encoding="utf-8")
            review = root / "review"
            initial = subprocess.run(
                [
                    "python3", str(ENTRYPOINT), str(deck), "--phase", "prepare", "--mode", "quick",
                    "--notes", str(notes_path), "--review-dir", str(review),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)

            deck.write_text(
                deck.read_text(encoding="utf-8").replace(
                    "<h2>Initial structure</h2>",
                    "<h2><span>Changed structure</span></h2>",
                    1,
                ),
                encoding="utf-8",
            )
            revised = subprocess.run(
                [
                    "python3", str(ENTRYPOINT), str(deck), "--phase", "prepare", "--mode", "quick",
                    "--notes", str(notes_path), "--review-dir", str(review),
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stdout + revised.stderr)
            self.assertIn("requested change type text resolved to all", revised.stdout)
            manifest = json.loads((review / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["change_type"], "all")
            self.assertEqual(manifest["render_run"]["requested_change_type"], "text")
            self.assertEqual(manifest["render_run"]["detected_change_type"], "all")

    def test_change_classifier_widens_when_review_configuration_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            review = root / "review"
            initial = subprocess.run(
                [
                    "node", str(ROOT / "scripts" / "render_slides.js"), str(deck), str(review),
                    "--mode", "quick", "--review-risk", "standard",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
            effective = classify_change_scope(
                deck,
                review,
                "text",
                "quick",
                "high",
                False,
                review / ".fingerprint-cache.json",
            )
            self.assertEqual(effective["effective"], "all")
            self.assertEqual(effective["impact"], "full")


if __name__ == "__main__":
    unittest.main()
