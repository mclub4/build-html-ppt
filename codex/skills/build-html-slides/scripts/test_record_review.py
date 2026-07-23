#!/usr/bin/env python3
"""Exercise safe review-record updates without generating verdicts."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "scripts" / "record_review.py"


def manifest() -> dict:
    return {
        "schema_version": 13,
        "phase": "iteration",
        "review_batches": [
            {"id": "batch-01", "slides": [1], "capture_profiles": {"1": ["normal"]}, "status": "pending"}
        ],
        "slides": [
            {
                "slide": 1,
                "review_batch_id": "batch-01",
                "required_ai_profiles": ["normal"],
                "reviewer": "",
                "reviewer_ref": "",
                "inspected_profiles": [],
                "observation": "",
                "checks": {"crop": "pending", "text": "pending"},
                "identity_review": [],
                "status": "pending",
            }
        ],
        "cross_review_batches": [],
        "cross_reviews": [],
        "quality_score": {
            "status": "pending",
            "reviewer": "",
            "reviewer_ref": "",
            "dimensions": {},
            "total": 0,
            "weakest_slides": [],
            "notes": "",
        },
        "squint_review": {
            "status": "pending",
            "reviewer": "",
            "reviewer_ref": "",
            "review_method": "vision-squint-contact-sheet",
            "artifact_path": "tmp/squint-contact-sheet.png",
            "artifact_sha256": "a" * 64,
            "normal_capture_sha256": {"1": "b" * 64},
            "checks": {
                "focal_hierarchy": "pending",
                "emphasis_range": "pending",
                "deck_rhythm": "pending",
                "color_density_balance": "pending",
            },
            "observation": "",
            "limitations": ["text-overlap", "line-breaks", "crop", "distortion", "overflow"],
        },
    }


class RecordReviewTests(unittest.TestCase):
    def run(self, path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RECORDER), str(path), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_slide_record_requires_explicit_profiles_and_every_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            path.write_text(json.dumps(manifest()), encoding="utf-8")
            result = self.run(
                path, "slide", "--slide", "1", "--reviewer", "vision-a",
                "--reviewer-ref", "agent-vision-a", "--status", "pass",
                "--observation", "The full-size capture keeps the title and subject inside the slide.",
                "--inspected", "normal", "--check", "crop=pass",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exactly once", result.stderr)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["slides"][0]["status"], "pending")

    def test_slide_record_updates_only_explicit_review_fields_and_batch_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            path.write_text(json.dumps(manifest()), encoding="utf-8")
            result = self.run(
                path, "slide", "--slide", "1", "--reviewer", "vision-a",
                "--reviewer-ref", "agent-vision-a", "--status", "pass",
                "--observation", "The full-size capture keeps the title and subject inside the slide.",
                "--inspected", "normal", "--check", "crop=pass", "--check", "text=pass",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(updated["slides"][0]["status"], "pass")
            self.assertEqual(updated["review_batches"][0]["status"], "complete")
            self.assertEqual(updated["slides"][0]["checks"], {"crop": "pass", "text": "pass"})

    def test_quality_record_computes_total_from_explicit_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            path.write_text(json.dumps(manifest()), encoding="utf-8")
            arguments = [
                "quality", "--reviewer", "editor-a", "--reviewer-ref", "editor-ref-a",
                "--status", "pass", "--weakest", "1",
                "--observation", "The final deck has a coherent story, strong hierarchy, and usable presentation pacing.",
            ]
            for name, score in (
                ("story", 3), ("art_direction", 3), ("layout_rhythm", 2), ("typography", 3),
                ("imagery", 2), ("composition", 3), ("evidence", 2), ("presentation_utility", 2),
            ):
                arguments.extend(("--dimension", f"{name}={score}"))
            result = self.run(path, *arguments)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            score = json.loads(path.read_text(encoding="utf-8"))["quality_score"]
            self.assertEqual(score["total"], 20)
            self.assertEqual(score["weakest_slides"], [1])

    def test_squint_record_preserves_generated_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            original = manifest()
            path.write_text(json.dumps(original), encoding="utf-8")
            arguments = [
                "squint", "--reviewer", "editor-a", "--reviewer-ref", "editor-ref-a",
                "--status", "pass",
                "--observation", "The contact sheet shows a clear focal sequence and varied emphasis across the entire deck.",
            ]
            for name in original["squint_review"]["checks"]:
                arguments.extend(("--check", f"{name}=pass"))
            result = self.run(path, *arguments)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            review = json.loads(path.read_text(encoding="utf-8"))["squint_review"]
            self.assertEqual(review["artifact_sha256"], "a" * 64)
            self.assertEqual(review["status"], "pass")


if __name__ == "__main__":
    unittest.main()
