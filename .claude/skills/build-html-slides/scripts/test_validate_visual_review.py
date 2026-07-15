#!/usr/bin/env python3
"""Regression tests for adaptive visual-review manifest schema version 7."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import time
import unittest
import zlib
from functools import lru_cache
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate_visual_review.py")
RENDERER = Path(__file__).with_name("render_slides.js")
PROFILE_SPECS = {
    "normal": {"viewport": "1920x1080", "visual_viewport": "1920x1080", "screenshot": "1920x1080", "zoom": 1, "scale_mode": "none", "device_pixel_ratio": 1},
    "short": {"viewport": "1366x650", "visual_viewport": "1366x650", "screenshot": "1366x650", "zoom": 1, "scale_mode": "none", "device_pixel_ratio": 1},
    "zoom150": {"viewport": "1920x1080", "visual_viewport": "1280x720", "screenshot": "1920x1080", "zoom": 1.5, "scale_mode": "browser-page", "device_pixel_ratio": 1},
    "tablet": {"viewport": "1024x768", "visual_viewport": "1024x768", "screenshot": "1024x768", "zoom": 1, "scale_mode": "none", "device_pixel_ratio": 1},
    "mobile": {"viewport": "390x844", "visual_viewport": "390x844", "screenshot": "390x844", "zoom": 1, "scale_mode": "none", "device_pixel_ratio": 1},
}
BASE_PROFILES = ("normal", "short", "zoom150")
RESPONSIVE_PROFILES = BASE_PROFILES + ("tablet", "mobile")
CHECKS_BY_CHANGE = {
    "all": ("crop", "aspect_ratio", "resolution", "content_match", "completion", "overflow", "occlusion", "text", "text_bounds", "density", "controls"),
    "text": ("text", "text_bounds", "density"),
    "image": ("crop", "aspect_ratio", "resolution", "content_match", "completion"),
    "navigation": ("controls",),
}


def checks_for(scope: str, identity: bool = False) -> tuple[str, ...]:
    checks = CHECKS_BY_CHANGE[scope]
    return checks + (("identity",) if identity and scope in {"all", "image"} else ())


def deck_for(count: int, critical: int | None = None, identity: int | None = None) -> str:
    slides = []
    for number in range(1, count + 1):
        content = '<div class="diagram"></div>' if number == critical else ""
        visual_critical = ' data-visual-critical="true"' if number == critical else ""
        identity_required = ' data-identity-review="required"' if number == identity else ""
        slides.append(f'<section class="slide" data-title="Slide {number}"{visual_critical}{identity_required}>{content}</section>')
    return f"<!doctype html><html><body>{''.join(slides)}</body></html>"


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


@lru_cache(maxsize=None)
def png_bytes(width: int, height: int, blank: bool = False) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressor = zlib.compressobj(9)
    chunks = []
    for row_number in range(height):
        if blank:
            pixel = b"\x00\x00\x00"
        else:
            level = 24 + (row_number % 8) * 28
            pixel = bytes((level, (level * 3) % 256, 255 - level))
        chunks.append(compressor.compress(b"\x00" + pixel * width))
    chunks.append(compressor.flush())
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", b"".join(chunks))
        + png_chunk(b"IEND", b"")
    )


def dimensions(profile: str) -> tuple[int, int]:
    return tuple(map(int, PROFILE_SPECS[profile]["screenshot"].split("x")))


def evidence_bytes(profile: str) -> bytes:
    return png_bytes(*dimensions(profile))


class VisualReviewTests(unittest.TestCase):
    run_id = "12345678-1234-1234-1234-123456789abc"
    old_run_id = "87654321-4321-4321-4321-cba987654321"

    def profiles(self, responsive: bool) -> tuple[str, ...]:
        return RESPONSIVE_PROFILES if responsive else BASE_PROFILES

    def reviewer_for(self, number: int, count: int, mode: str, review_risk: str = "standard") -> tuple[str, str]:
        if mode == "quick":
            return "visual-a", "agent-ref-a"
        groups = 3 if review_risk == "high" else 2
        group_size = (count + groups - 1) // groups
        group = min((number - 1) // group_size, groups - 1)
        letter = chr(ord("a") + group)
        return f"visual-{letter}", f"agent-ref-{letter}"

    def record(
        self,
        number: int,
        count: int,
        mode: str,
        responsive: bool,
        scope: str = "all",
        refreshed: bool = True,
        review_risk: str = "standard",
        identity: bool = False,
    ) -> dict:
        reviewer, reviewer_ref = self.reviewer_for(number, count, mode, review_risk)
        source_hash = hashlib.sha256(f"slide-{number}".encode()).hexdigest()
        captures = {}
        for profile in self.profiles(responsive):
            data = evidence_bytes(profile)
            captures[profile] = {
                "path": f"{profile}/slide-{number:02}.png",
                "sha256": hashlib.sha256(data).hexdigest(),
                "active_slide": number,
                "active_title": f"Slide {number}",
                **PROFILE_SPECS[profile],
                "source_sha256": source_hash,
                "render_run_id": self.run_id if refreshed else self.old_run_id,
                "motion_disabled": True,
                "text_geometry": {"ok": True, "checked": 3, "issues": []},
                "container_density": {"ok": True, "checked": 0, "issues": [], "warnings": [], "items": []},
                "control_geometry": {"ok": True, "issues": []},
                "image_geometry": {"ok": True, "checked": 1, "issues": [], "warnings": []},
            }
        return {
            "slide": number,
            "title": f"Slide {number}",
            "source_sha256": source_hash,
            "review_scope": scope,
            "reviewer": reviewer,
            "reviewer_ref": reviewer_ref,
            "visual_critical": False,
            "review_batch_id": "",
            "review_method": "vision-batched-full-size",
            "captures": captures,
            "required_ai_profiles": ["normal"],
            "inspected_profiles": ["normal"],
            "observation": f"Opened slide {number} across all required profiles once; visible text, media, and controls remain clear.",
            "identity_required": identity,
            "identity_detection": "explicit" if identity else "none",
            "identity_targets": ([{
                "target_id": f"slide-{number}-identity-1",
                "subject_id": "series:character-a",
                "subject_name": "Character A / 캐릭터 A",
                "mode": "primary",
                "cues": ["red hair", "star-shaped badge"],
                "asset_path": "assets/character-a.webp",
                "asset_sha256": hashlib.sha256(b"candidate-image").hexdigest(),
                "reference_path": "assets/identity/character-a-official.webp",
                "reference_sha256": hashlib.sha256(b"reference-image").hexdigest(),
            }] if identity else []),
            "identity_review": ([{
                "target_id": f"slide-{number}-identity-1",
                "subject_name": "Character A / 캐릭터 A",
                "verdict": "pass",
                "observation": "Candidate and official reference share the red hair and star-shaped badge with no conflicting identity cues.",
            }] if identity and scope in {"all", "image"} else []),
            "checks": {name: "pass" for name in checks_for(scope, identity)},
            "status": "pass",
            "notes": [],
        }

    def cross_review(self, record: dict, responsive: bool) -> dict:
        reviewer_ref = "cross-ref-b" if record["reviewer_ref"] != "cross-ref-b" else "cross-ref-c"
        return {
            "slide": record["slide"],
            "reviewer": "cross-reviewer",
            "reviewer_ref": reviewer_ref,
            "review_method": "vision-batched-full-size",
            "inspected_profiles": record["required_ai_profiles"],
            "observation": f"Independently inspected slide {record['slide']} once across all current capture profiles and found no defect.",
            "capture_sha256": {
                profile: record["captures"][profile]["sha256"] for profile in record["required_ai_profiles"]
            },
            "checks": {name: "pass" for name in checks_for(record["review_scope"], record["identity_required"])},
            "identity_review": json.loads(json.dumps(record["identity_review"])),
            "status": "pass",
        }

    def manifest(
        self,
        deck: str,
        count: int = 2,
        mode: str = "quick",
        phase: str = "iteration",
        responsive: bool = False,
        rendered: list[int] | None = None,
        requested: list[int] | None = None,
        changed: list[int] | None = None,
        scope: str = "all",
        critical: int | None = None,
        review_risk: str = "standard",
        identity: int | None = None,
    ) -> dict:
        rendered = rendered or list(range(1, count + 1))
        requested = requested or list(rendered)
        changed = changed or list(rendered)
        rendered_set = set(rendered)
        records = [
            self.record(
                number, count, mode, responsive, scope if number in rendered_set else "all",
                number in rendered_set, review_risk, number == identity,
            )
            for number in range(1, count + 1)
        ]
        profiles = self.profiles(responsive)
        for record in records:
            number = record["slide"]
            is_critical = number in {1, count} or number == critical
            identity_review = number == identity and record["review_scope"] in {"all", "image"}
            required = list(profiles) if is_critical else (["normal", *("tablet", "mobile")] if mode == "full" and responsive else (["normal"] if mode == "full" or identity_review else []))
            record["visual_critical"] = is_critical
            record["required_ai_profiles"] = required
            record["inspected_profiles"] = required
            if mode == "quick" and not required:
                record["reviewer"] = ""
                record["reviewer_ref"] = ""
                record["review_method"] = "automated-geometry-only"
                record["observation"] = ""
                record["checks"] = {}
                record["status"] = "automation-pass"
        slide_hashes = {str(record["slide"]): record["source_sha256"] for record in records}
        global_hash = hashlib.sha256(b"global").hexdigest()
        score_value = 2 if mode == "quick" else 3
        quality = {
            "status": "pass" if phase == "final" and mode == "full" else "pending",
            "reviewer": "editor-a" if phase == "final" and mode == "full" else "",
            "reviewer_ref": "editor-ref-a" if phase == "final" and mode == "full" else "",
            "dimensions": {name: score_value if phase == "final" and mode == "full" else 0 for name in (
                "story", "art_direction", "layout_rhythm", "typography",
                "imagery", "composition", "evidence", "presentation_utility",
            )},
            "total": score_value * 8 if phase == "final" and mode == "full" else 0,
            "weakest_slides": list(range(1, min(3, count) + 1)) if phase == "final" and mode == "full" else [],
            "notes": "Final rendered deck has coherent pacing, readable evidence, and stable presentation utility." if phase == "final" and mode == "full" else "",
        }
        cross_reviews = []
        if phase == "final" and mode == "full":
            required = set(range(1, count + 1))
            cross_reviews = [self.cross_review(records[number - 1], responsive) for number in sorted(required)]
        review_batches = []
        ai_reviewed = [number for number in rendered if records[number - 1]["required_ai_profiles"]]
        for offset in range(0, len(ai_reviewed), 4):
            batch_slides = ai_reviewed[offset : offset + 4]
            batch_id = f"batch-{len(review_batches) + 1:02}"
            for number in batch_slides:
                records[number - 1]["review_batch_id"] = batch_id
            review_batches.append({
                "id": batch_id,
                "slides": batch_slides,
                "capture_profiles": {
                    str(number): records[number - 1]["required_ai_profiles"] for number in batch_slides
                },
                "status": "pending",
            })
        return {
            "schema_version": 7,
            "mode": mode,
            "review_risk": review_risk,
            "phase": phase,
            "responsive": responsive,
            "change_type": scope,
            "deck_sha256": hashlib.sha256(deck.encode()).hexdigest(),
            "previous_deck_sha256": hashlib.sha256(b"previous").hexdigest(),
            "render_run": {
                "id": self.run_id,
                "generator": "render_slides.js",
                "generator_sha256": hashlib.sha256(RENDERER.read_bytes()).hexdigest(),
                "browser": "chromium 149.0.0.0",
                "captured_at": "2026-07-14T00:00:00+00:00",
                "strategy": "full" if rendered_set == set(range(1, count + 1)) else "incremental",
                "requested_slides": requested,
                "rendered_slides": rendered,
                "directly_changed_slides": changed,
                "reused_slides": [number for number in range(1, count + 1) if number not in rendered_set],
                "animations_disabled": True,
            },
            "source_fingerprints": {
                "global_sha256": global_hash,
                "previous_global_sha256": global_hash,
                "slides": slide_hashes,
            },
            "viewports": {profile: dict(PROFILE_SPECS[profile]) for profile in profiles},
            "automation_gate": {
                "status": "pass",
                "checks": list({
                    "all": ("text_bounds", "container_density", "controls", "image_geometry"),
                    "text": ("text_bounds", "container_density"),
                    "image": ("image_geometry",),
                    "navigation": ("controls",),
                }[scope]),
                "failures": [],
                "warnings": [],
            },
            "review_batches": review_batches,
            "quality_score": quality,
            "cross_reviews": cross_reviews,
            "slides": records,
        }

    def validate(
        self,
        deck_text: str,
        manifest: dict,
        *,
        missing_capture: str | None = None,
        blank_capture: str | None = None,
        stale_rendered: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = root / "deck.html"
            review = root / "review.json"
            deck.write_text(deck_text, encoding="utf-8")
            review.write_text(json.dumps(manifest), encoding="utf-8")
            for record in manifest.get("slides", []):
                for target in record.get("identity_targets", []):
                    for kind, payload in (("asset", b"candidate-image"), ("reference", b"reference-image")):
                        relative = target.get(f"{kind}_path")
                        if not relative:
                            continue
                        identity_path = root / relative
                        identity_path.parent.mkdir(parents=True, exist_ok=True)
                        identity_path.write_bytes(payload)
            written: set[str] = set()
            for record in manifest.get("slides", []):
                for profile, capture in record.get("captures", {}).items():
                    relative = capture.get("path")
                    if not relative or relative in written or relative == missing_capture:
                        continue
                    written.add(relative)
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if relative == blank_capture:
                        path.write_bytes(png_bytes(*dimensions(profile), blank=True))
                    else:
                        path.write_bytes(evidence_bytes(profile))
            if stale_rendered:
                future = time.time_ns() + 2_000_000_000
                os.utime(deck, ns=(future, future))
            environment = os.environ.copy()
            environment["BUILD_HTML_SLIDES_UNIT_TEST"] = "1"
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck), str(review)],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

    def test_iteration_manifest_passes_without_quality_score(self) -> None:
        deck = deck_for(2)
        result = self.validate(deck, self.manifest(deck))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("without quality scoring", result.stdout)

    def test_final_full_manifest_passes(self) -> None:
        deck = deck_for(3, critical=2)
        result = self.validate(deck, self.manifest(deck, 3, mode="full", phase="final", critical=2))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_visual_classes_do_not_implicitly_require_cross_review(self) -> None:
        deck = deck_for(3).replace(
            'data-title="Slide 2"></section>',
            'data-title="Slide 2"><img class="logo key-visual" src="brand.svg"></section>',
        )
        manifest = self.manifest(deck, 3, mode="full", phase="final")
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_responsive_profiles_are_opt_in(self) -> None:
        deck = deck_for(2)
        result = self.validate(deck, self.manifest(deck, responsive=True))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_manifest_rejects_mobile_profile(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        manifest["responsive"] = False
        manifest["viewports"]["mobile"] = dict(PROFILE_SPECS["mobile"])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly these ordered profiles", result.stdout)

    def test_slide_uses_one_observation_not_profile_observations(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        manifest["slides"][0]["observation"] = ""
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("one concrete slide-level vision observation", result.stdout)

    def test_adaptive_profiles_must_be_inspected_in_one_review(self) -> None:
        deck = deck_for(3, critical=2)
        manifest = self.manifest(deck, count=3, critical=2)
        manifest["slides"][1]["inspected_profiles"] = ["normal", "short"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("inspect its adaptive profile set once", result.stdout)

    def test_automation_gate_blocks_visual_review(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        manifest["automation_gate"]["status"] = "fail"
        manifest["automation_gate"]["failures"] = [{
            "slide": 1,
            "profile": "normal",
            "check": "text_bounds",
            "issue": "title overflow",
        }]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must pass before AI visual review", result.stdout)

    def test_review_batch_cannot_exceed_four_slides(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        manifest["review_batches"] = [{
            "id": "batch-01",
            "slides": [1, 2, 3, 4, 5],
            "capture_profiles": {
                str(number): manifest["slides"][number - 1]["required_ai_profiles"]
                for number in range(1, 6)
            },
        }]
        for record in manifest["slides"]:
            record["review_batch_id"] = "batch-01"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("one to four slide numbers", result.stdout)

    def test_text_change_requires_only_text_checks(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[2, 3, 4], requested=[3], changed=[3], scope="text")
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_text_change_rejects_unrelated_check_contract(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[2, 3, 4], requested=[3], changed=[3], scope="text")
        manifest["slides"][2]["checks"]["crop"] = "pass"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("automation-only record must carry automation-pass status", result.stdout)

    def test_quick_routes_only_critical_slides_to_ai(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        self.assertEqual([batch["slides"] for batch in manifest["review_batches"]], [[1, 5]])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_full_review_cannot_pass_with_failed_completion(self) -> None:
        deck = deck_for(4)
        manifest = self.manifest(deck, count=4, mode="full")
        manifest["slides"][1]["checks"]["completion"] = "fail"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("check did not pass: completion", result.stdout)

    def test_quick_routes_identity_slide_and_accepts_grounded_review(self) -> None:
        deck = deck_for(5, identity=3)
        manifest = self.manifest(deck, count=5, identity=3)
        self.assertEqual([batch["slides"] for batch in manifest["review_batches"]], [[1, 3, 5]])
        self.assertEqual(manifest["slides"][2]["required_ai_profiles"], ["normal"])
        self.assertIn("identity", manifest["slides"][2]["checks"])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_identity_slide_rejects_missing_target_verdict(self) -> None:
        deck = deck_for(3, identity=2)
        manifest = self.manifest(deck, count=3, identity=2)
        manifest["slides"][1]["identity_review"] = []
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must cover every identity target exactly once", result.stdout)

    def test_identity_slide_rejects_candidate_as_reference(self) -> None:
        deck = deck_for(3, identity=2)
        manifest = self.manifest(deck, count=3, identity=2)
        target = manifest["slides"][1]["identity_targets"][0]
        target["reference_path"] = target["asset_path"]
        target["reference_sha256"] = target["asset_sha256"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot use its candidate as the reference", result.stdout)

    def test_high_risk_full_requires_three_reviewers(self) -> None:
        deck = deck_for(9)
        manifest = self.manifest(deck, count=9, mode="full", review_risk="high")
        manifest["slides"][6]["reviewer"] = "visual-b"
        manifest["slides"][6]["reviewer_ref"] = "agent-ref-b"
        manifest["slides"][7]["reviewer"] = "visual-b"
        manifest["slides"][7]["reviewer_ref"] = "agent-ref-b"
        manifest["slides"][8]["reviewer"] = "visual-b"
        manifest["slides"][8]["reviewer_ref"] = "agent-ref-b"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires at least 3 distinct primary reviewer_ref", result.stdout)

    def test_incremental_render_requires_neighbors(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("immediate neighbors", result.stdout)

    def test_incremental_reuse_rejects_global_change(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[2, 3, 4], requested=[3], changed=[3], scope="image")
        manifest["source_fingerprints"]["previous_global_sha256"] = hashlib.sha256(b"old-global").hexdigest()
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("global style/runtime change", result.stdout)

    def test_reused_slide_may_keep_older_capture(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[2, 3, 4], requested=[3], changed=[3], scope="navigation")
        result = self.validate(deck, manifest, stale_rendered=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_refreshed_capture_must_be_newer_than_deck(self) -> None:
        deck = deck_for(2)
        result = self.validate(deck, self.manifest(deck), stale_rendered=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("refreshed capture is older", result.stdout)

    def test_final_phase_requires_quality_score(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck, mode="full", phase="final")
        manifest["quality_score"]["status"] = "pending"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("final phase requires a passing quality_score", result.stdout)

    def test_iteration_does_not_validate_quality_score(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        manifest["quality_score"]["dimensions"] = {"broken": 99}
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_blank_capture_fails(self) -> None:
        deck = deck_for(2)
        result = self.validate(deck, self.manifest(deck), blank_capture="normal/slide-01.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("appears blank or near-solid", result.stdout)

    def test_capture_hash_mismatch_fails(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        manifest["slides"][0]["captures"]["normal"]["sha256"] = "0" * 64
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("capture sha256 mismatch", result.stdout)

    def test_missing_capture_fails(self) -> None:
        deck = deck_for(2)
        result = self.validate(deck, self.manifest(deck), missing_capture="short/slide-02.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("capture not found", result.stdout)

    def test_final_full_requires_cross_review(self) -> None:
        deck = deck_for(3, critical=2)
        manifest = self.manifest(deck, 3, mode="full", phase="final", critical=2)
        manifest["cross_reviews"] = []
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("requires an independent final cross review", result.stdout)

    def test_final_full_requires_cross_review_for_ordinary_slide(self) -> None:
        deck = deck_for(3)
        manifest = self.manifest(deck, 3, mode="full", phase="final")
        manifest["cross_reviews"] = [
            review for review in manifest["cross_reviews"] if review["slide"] != 2
        ]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("slide 2 requires an independent final cross review", result.stdout)

    def test_cross_reviewer_must_be_outside_all_primary_reviewers(self) -> None:
        deck = deck_for(4)
        manifest = self.manifest(deck, 4, mode="full", phase="final")
        manifest["cross_reviews"][0]["reviewer_ref"] = manifest["slides"][-1]["reviewer_ref"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be outside the primary reviewer set", result.stdout)

    def test_cross_reviews_require_distinct_observations(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck, 2, mode="full", phase="final")
        manifest["cross_reviews"][1]["observation"] = manifest["cross_reviews"][0]["observation"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not reuse the same observation", result.stdout)

    def test_full_quality_editor_must_be_independent(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck, mode="full", phase="final")
        manifest["quality_score"]["reviewer_ref"] = manifest["slides"][0]["reviewer_ref"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("quality_score reviewer_ref must differ", result.stdout)


if __name__ == "__main__":
    unittest.main()
