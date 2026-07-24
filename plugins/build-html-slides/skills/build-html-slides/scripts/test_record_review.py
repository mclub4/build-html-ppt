#!/usr/bin/env python3
"""Exercise safe review-record updates without generating verdicts.

Every helper on a ``TestCase`` here is named so it cannot shadow a
``unittest.TestCase`` attribute. A subprocess helper called ``run`` used to sit
on this class; ``TestCase.__call__`` dispatches through ``self.run(result)``, so
the shadow swallowed the result object, executed a subprocess, and returned a
``CompletedProcess``. Every test reported success while ``testsRun`` stayed at
zero. ``test_workflow_contract.SuiteIntegrityTests`` now blocks the whole class
of defect across the suite.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "scripts" / "record_review.py"

SLIDE_CHECKS = ("--check", "crop=pass", "--check", "text=pass")


def manifest() -> dict:
    return {
        "schema_version": 13,
        "phase": "iteration",
        "review_batches": [
            {"id": "batch-01", "slides": [1], "capture_profiles": {"1": ["normal"]}, "status": "pending"}
        ],
        "automation_gate": {"status": "pass", "checks": [], "failures": [], "warnings": []},
        "slides": [
            {
                "slide": 1,
                "review_batch_id": "batch-01",
                "required_ai_profiles": ["normal"],
                "reviewer": "",
                "reviewer_ref": "",
                "inspected_profiles": [],
                "debug_captures": {},
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


def warned_manifest() -> dict:
    """A manifest whose slide 1 carries a deterministic warning and an overlay."""
    data = manifest()
    data["automation_gate"]["warnings"] = [
        {
            "slide": 1,
            "profile": "normal",
            "check": "contrast",
            "warning": "slide 1: text may sit on overlapping media; contrast interval straddles 4.5:1",
        }
    ]
    data["slides"][0]["debug_captures"] = {"normal": "normal/slide-01-debug.png"}
    return data


class RecordReviewTests(unittest.TestCase):
    def record(self, path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RECORDER), str(path), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def manifest_file(self, stack: tempfile.TemporaryDirectory, data: dict) -> Path:
        path = Path(stack.name) / "review.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def setUp(self) -> None:
        self.stack = tempfile.TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)

    def test_slide_record_requires_explicit_profiles_and_every_check(self) -> None:
        path = self.manifest_file(self.stack, manifest())
        result = self.record(
            path, "slide", "--slide", "1", "--reviewer", "vision-a",
            "--reviewer-ref", "agent-vision-a", "--status", "pass",
            "--observation", "The full-size capture keeps the title and subject inside the slide.",
            "--inspected", "normal", "--check", "crop=pass",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exactly once", result.stderr)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["slides"][0]["status"], "pending")

    def test_slide_record_updates_only_explicit_review_fields_and_batch_state(self) -> None:
        path = self.manifest_file(self.stack, manifest())
        result = self.record(
            path, "slide", "--slide", "1", "--reviewer", "vision-a",
            "--reviewer-ref", "agent-vision-a", "--status", "pass",
            "--observation", "The full-size capture keeps the title and subject inside the slide.",
            "--inspected", "normal", *SLIDE_CHECKS,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        updated = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(updated["slides"][0]["status"], "pass")
        self.assertEqual(updated["review_batches"][0]["status"], "complete")
        self.assertEqual(updated["slides"][0]["checks"], {"crop": "pass", "text": "pass"})

    def test_quality_record_computes_total_from_explicit_dimensions(self) -> None:
        path = self.manifest_file(self.stack, manifest())
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
        result = self.record(path, *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        score = json.loads(path.read_text(encoding="utf-8"))["quality_score"]
        self.assertEqual(score["total"], 20)
        self.assertEqual(score["weakest_slides"], [1])

    def test_squint_record_preserves_generated_evidence(self) -> None:
        original = manifest()
        path = self.manifest_file(self.stack, original)
        arguments = [
            "squint", "--reviewer", "editor-a", "--reviewer-ref", "editor-ref-a",
            "--status", "pass",
            "--observation", "The contact sheet shows a clear focal sequence and varied emphasis across the entire deck.",
        ]
        for name in original["squint_review"]["checks"]:
            arguments.extend(("--check", f"{name}=pass"))
        result = self.record(path, *arguments)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        review = json.loads(path.read_text(encoding="utf-8"))["squint_review"]
        self.assertEqual(review["artifact_sha256"], "a" * 64)
        self.assertEqual(review["status"], "pass")


class RefuteOrConfirmTests(unittest.TestCase):
    """references/reviewer-gates.md, 'Refute-or-confirm'."""

    def record(self, path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RECORDER), str(path), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def setUp(self) -> None:
        self.stack = tempfile.TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.path = Path(self.stack.name) / "review.json"
        self.path.write_text(json.dumps(warned_manifest()), encoding="utf-8")

    def slide(self, observation: str, *extra: str, status: str = "pass") -> subprocess.CompletedProcess[str]:
        return self.record(
            self.path, "slide", "--slide", "1", "--reviewer", "vision-a",
            "--reviewer-ref", "agent-vision-a", "--status", status,
            "--observation", observation, "--inspected", "normal",
            "--inspected-debug", "normal", *(extra or SLIDE_CHECKS),
        )

    def test_generic_approval_cannot_close_a_warned_slide(self) -> None:
        # The exact shape of approval that shipped the overlapping-price defect.
        result = self.slide("An intentional connecting rule that does not cover the product photo.")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must begin with 'CONFIRM: ' or 'REFUTE: '", result.stderr)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["slides"][0]["status"], "pending")

    def test_verdict_without_a_measurable_locator_is_rejected(self) -> None:
        result = self.slide("REFUTE: the rule terminates well before the handset and looks completely fine here.")
        self.assertEqual(result.returncode, 2)
        self.assertIn("coordinate, size, or distance", result.stderr)

    def test_verdict_may_not_restate_the_warning(self) -> None:
        result = self.slide(
            "REFUTE: text may sit on overlapping media; contrast interval straddles 4.5:1"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must not restate the warning", result.stderr)

    def test_confirm_must_fail_the_mapped_check(self) -> None:
        result = self.slide(
            "CONFIRM: the 1px connecting rule crosses the handset at x=690 and passes through the price numeral."
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("record --status fail", result.stderr)

    def test_confirm_with_a_failed_check_is_recorded(self) -> None:
        result = self.slide(
            "CONFIRM: the 1px connecting rule crosses the handset at x=690 and passes through the price numeral.",
            "--check", "crop=pass", "--check", "text=fail",
            status="fail",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(self.path.read_text(encoding="utf-8"))["slides"][0]
        self.assertEqual(record["status"], "fail")
        self.assertTrue(record["observation"].startswith("CONFIRM: "))

    def test_located_refutation_is_accepted_and_records_the_overlay(self) -> None:
        result = self.slide(
            "REFUTE: the rule terminates at x=612, 78px left of the handset edge; "
            "the scrim rectangle is fully transparent at that row."
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(self.path.read_text(encoding="utf-8"))["slides"][0]
        self.assertEqual(record["status"], "pass")
        self.assertEqual(record["inspected_debug_captures"], ["normal"])

    def test_boundary_overlay_must_be_inspected_when_one_exists(self) -> None:
        result = self.record(
            self.path, "slide", "--slide", "1", "--reviewer", "vision-a",
            "--reviewer-ref", "agent-vision-a", "--status", "pass",
            "--observation",
            "REFUTE: the rule terminates at x=612, 78px left of the handset edge; the scrim is transparent there.",
            "--inspected", "normal", *SLIDE_CHECKS,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--inspected-debug must exactly match", result.stderr)

    def test_verdict_prefix_is_rejected_on_an_unwarned_slide(self) -> None:
        path = Path(self.stack.name) / "clean.json"
        path.write_text(json.dumps(manifest()), encoding="utf-8")
        result = self.record(
            path, "slide", "--slide", "1", "--reviewer", "vision-a",
            "--reviewer-ref", "agent-vision-a", "--status", "pass",
            "--observation", "CONFIRM: the rule crosses the handset at x=690 and passes through the price.",
            "--inspected", "normal", *SLIDE_CHECKS,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("reserved for slides carrying a deterministic warning", result.stderr)


class TemplateOutputTests(unittest.TestCase):
    """`template` prints invocations that run unmodified except for the placeholders."""

    def setUp(self) -> None:
        self.stack = tempfile.TemporaryDirectory()
        self.addCleanup(self.stack.cleanup)
        self.path = Path(self.stack.name) / "review.json"
        self.path.write_text(json.dumps(warned_manifest()), encoding="utf-8")

    def emit(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(RECORDER), str(self.path), "template", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_template_emits_the_real_tuple_profiles_and_overlay_flags(self) -> None:
        result = self.emit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--slide 1", result.stdout)
        self.assertIn("--inspected normal", result.stdout)
        self.assertIn("--inspected-debug normal", result.stdout)
        self.assertIn("--check crop=pass", result.stdout)
        self.assertIn("--check text=pass", result.stdout)
        self.assertIn("# WARNING slide 1:", result.stdout)
        self.assertIn("CONFIRM:", result.stdout)
        self.assertIn("quality", result.stdout)
        self.assertIn("squint", result.stdout)

    def test_template_is_runnable_after_substituting_the_placeholders(self) -> None:
        block = next(
            chunk for chunk in self.emit("--slide", "1").stdout.split("\n\n")
            if "--slide 1" in chunk
        )
        command = " ".join(
            line for line in block.splitlines() if not line.startswith("#")
        ).replace("\\", "")
        command = command.replace(
            "'CONFIRM: NAME THE ELEMENT AND ITS COORDINATE'",
            "'CONFIRM: the rule crosses the handset at x=690 and cuts the price numeral in half.'",
        ).replace("REVIEWER_REF", "vr-a-01").replace("--status pass", "--status fail")
        command = command.replace("--check text=pass", "--check text=fail")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["slides"][0]["status"], "fail")

    def test_template_reports_nothing_pending_once_records_are_complete(self) -> None:
        data = warned_manifest()
        data["review_batches"][0]["status"] = "complete"
        data["quality_score"]["status"] = "pass"
        data["squint_review"]["status"] = "pass"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        result = self.emit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no pending review records", result.stdout)


if __name__ == "__main__":
    unittest.main()
