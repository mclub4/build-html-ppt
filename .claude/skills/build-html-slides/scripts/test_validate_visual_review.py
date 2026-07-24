#!/usr/bin/env python3
"""Regression tests for the adaptive visual-review manifest contract."""

from __future__ import annotations

import hashlib
import importlib.util
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
CONTRACT_PATH = Path(__file__).with_name("validation_contract.json")
CONTRACT_BYTES = CONTRACT_PATH.read_bytes()
CONTRACT = json.loads(CONTRACT_BYTES)
PROFILE_SPECS = {
    name: {
        "viewport": "x".join(str(value) for value in profile["viewport"]),
        "visual_viewport": "x".join(str(value) for value in profile["visual_viewport"]),
        "screenshot": "x".join(str(value) for value in profile["screenshot"]),
        "zoom": profile["zoom"],
        "scale_mode": profile["scale_mode"],
        "device_pixel_ratio": profile["device_pixel_ratio"],
    }
    for name, profile in CONTRACT["profiles"].items()
}
BASE_PROFILES = tuple(CONTRACT["base_profiles"])
RESPONSIVE_PROFILES = BASE_PROFILES + tuple(CONTRACT["responsive_profiles"])
CHECKS_BY_CHANGE = {name: tuple(checks) for name, checks in CONTRACT["checks_by_change"].items()}


def checks_for(scope: str, identity: bool = False) -> tuple[str, ...]:
    checks = CHECKS_BY_CHANGE[scope]
    return checks + (("identity",) if identity and scope in {"all", "image"} else ())


def cross_review_numbers(records: list[dict], review_risk: str) -> list[int]:
    return sorted(
        record["slide"]
        for record in records
        if record["visual_critical"] or record.get("identity_required")
    )


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


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_visual_review", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def filtered_png(width: int, height: int, filter_type: int) -> bytes:
    """Encode a PNG whose every scanline uses one specific filter type."""
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressor = zlib.compressobj(6)
    chunks = []
    previous = bytearray(width * 3)
    for row in range(height):
        raw = bytearray()
        for column in range(width):
            level = (row * 7 + column * 3) % 256
            raw += bytes((level, (level * 5) % 256, 255 - level))
        if filter_type == 0:
            encoded = bytes(raw)
        elif filter_type == 1:
            encoded = bytes(
                (raw[index] - (raw[index - 3] if index >= 3 else 0)) & 0xFF for index in range(len(raw))
            )
        elif filter_type == 2:
            encoded = bytes((raw[index] - previous[index]) & 0xFF for index in range(len(raw)))
        elif filter_type == 3:
            encoded = bytes(
                (raw[index] - (((raw[index - 3] if index >= 3 else 0) + previous[index]) >> 1)) & 0xFF
                for index in range(len(raw))
            )
        else:
            encoded = bytearray()
            for index in range(len(raw)):
                left = raw[index - 3] if index >= 3 else 0
                up = previous[index]
                corner = previous[index - 3] if index >= 3 else 0
                estimate = left + up - corner
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - corner))
                predictor = (left, up, corner)[distances.index(min(distances))]
                encoded.append((raw[index] - predictor) & 0xFF)
            encoded = bytes(encoded)
        chunks.append(compressor.compress(bytes([filter_type]) + encoded))
        previous = raw
    chunks.append(compressor.flush())
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", b"".join(chunks))
        + png_chunk(b"IEND", b"")
    )


class CaptureMetricTests(unittest.TestCase):
    """A gate input must never depend on which PNG backend the machine happened to have."""

    module = load_validator()

    def test_both_decoders_agree_on_every_row_filter(self) -> None:
        self.assertIsNotNone(self.module.Image, "Pillow must be installed to compare both backends")
        with tempfile.TemporaryDirectory() as directory:
            for filter_type in range(5):
                path = Path(directory) / f"filter-{filter_type}.png"
                path.write_bytes(filtered_png(97, 61, filter_type))
                pillow = self.module.png_info(path, decoder="pillow")
                fallback = self.module.png_info(path, decoder="fallback")
                self.assertEqual(pillow, fallback, f"row filter {filter_type} metrics diverged")

    def test_both_decoders_agree_on_blank_and_alpha_captures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            blank = Path(directory) / "blank.png"
            blank.write_bytes(png_bytes(320, 180, blank=True))
            self.assertEqual(
                self.module.png_info(blank, decoder="pillow"),
                self.module.png_info(blank, decoder="fallback"),
            )
            dimensions, color_count, luma_range, _ = self.module.png_info(blank, decoder="fallback")
            self.assertEqual(dimensions, (320, 180))
            self.assertEqual(color_count, 1)
            self.assertEqual(luma_range, 0)

    def test_color_count_saturates_at_the_tracked_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            busy = Path(directory) / "busy.png"
            busy.write_bytes(filtered_png(400, 300, 4))
            _, color_count, _, _ = self.module.png_info(busy, decoder="pillow")
            self.assertEqual(color_count, self.module.MAX_TRACKED_COLORS)

    def test_sample_grid_is_deterministic_and_in_bounds(self) -> None:
        self.assertEqual(self.module.sample_positions(4, 64), (0, 1, 2, 3))
        for size in (1, 2, 63, 64, 65, 129, 390, 650, 768, 1024, 1080, 1366, 1920):
            positions = self.module.sample_positions(size, 64)
            self.assertEqual(len(positions), min(size, 64), size)
            self.assertEqual(len(set(positions)), len(positions), size)
            self.assertEqual(list(positions), sorted(positions), size)
            self.assertGreaterEqual(positions[0], 0, size)
            self.assertLess(positions[-1], size, size)

    def test_sample_grid_does_not_alias_with_striped_content(self) -> None:
        # A frame striped on an 8-row period must not read as near-solid.
        rows = self.module.sample_positions(768, 64)
        self.assertGreater(len({row % 8 for row in rows}), 4)


class LocalFileIntegrityTests(unittest.TestCase):
    module = load_validator()

    def entry(self, path: Path) -> dict:
        stat = path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "ctime_ns": stat.st_ctime_ns,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def test_timestamp_drift_alone_is_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "photo.webp"
            asset.write_bytes(b"image-bytes")
            entry = self.entry(asset)
            os.chmod(asset, 0o600)
            os.utime(asset, ns=(entry["mtime_ns"] + 5_000_000_000,) * 2)
            errors: list[str] = []
            notices: list[str] = []
            self.module.validate_local_file_metadata({"local_files": [entry]}, errors, notices)
            self.assertEqual(errors, [])
            self.assertEqual(len(notices), 1)
            self.assertIn("kept identical bytes", notices[0])

    def test_changed_content_fails_even_when_timestamps_are_restored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            asset = Path(directory) / "photo.webp"
            asset.write_bytes(b"image-bytes")
            entry = self.entry(asset)
            asset.write_bytes(b"image-bytez")
            os.utime(asset, ns=(entry["mtime_ns"], entry["mtime_ns"]))
            errors: list[str] = []
            notices: list[str] = []
            self.module.validate_local_file_metadata({"local_files": [entry]}, errors, notices)
            self.assertEqual(notices, [])
            self.assertEqual(len(errors), 1)
            self.assertIn("local fingerprint entry 1 changed after rendering", errors[0])
            self.assertIn("recorded sha256 does not match the bytes on disk", errors[0])


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

    def cross_review(self, record: dict, responsive: bool, batch_id: str = "") -> dict:
        reviewer_ref = "cross-ref-b" if record["reviewer_ref"] != "cross-ref-b" else "cross-ref-c"
        return {
            "slide": record["slide"],
            "reviewer": "cross-reviewer",
            "reviewer_ref": reviewer_ref,
            "review_batch_id": batch_id,
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
        impact: str | None = None,
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
            # Non-critical slides still carry the normal-profile review in both modes. The old
            # expression here was `["normal"] if mode == "full" or identity_review else []`, which
            # mirrored routing the validator no longer implements: an empty set means the slide is
            # in no review batch, and nothing in the pipeline would ever fill in its reviewer or
            # check verdicts. Keep this unconditional.
            required = list(profiles) if is_critical else ["normal"]
            record["visual_critical"] = is_critical
            record["required_ai_profiles"] = required
            record["inspected_profiles"] = required
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
        cross_review_batches = []
        if phase == "final" and mode == "full":
            required = cross_review_numbers(records, review_risk)
            for offset in range(0, len(required), CONTRACT["review_batch_size"]):
                batch_slides = required[offset : offset + CONTRACT["review_batch_size"]]
                batch_id = f"cross-batch-{len(cross_review_batches) + 1:02}"
                cross_review_batches.append({
                    "id": batch_id,
                    "slides": batch_slides,
                    "capture_profiles": {
                        str(number): records[number - 1]["required_ai_profiles"] for number in batch_slides
                    },
                    "status": "complete",
                })
                cross_reviews.extend(
                    self.cross_review(records[number - 1], responsive, batch_id) for number in batch_slides
                )
        squint_payload = png_bytes(960, 540)
        squint_review = None
        if phase == "final" and mode == "full":
            squint_review = {
                "status": "pass",
                "reviewer": "editor-a",
                "reviewer_ref": "editor-ref-a",
                "review_method": "vision-squint-contact-sheet",
                "artifact_path": "tmp/squint-contact-sheet.png",
                "artifact_sha256": hashlib.sha256(squint_payload).hexdigest(),
                "normal_capture_sha256": {
                    str(record["slide"]): record["captures"]["normal"]["sha256"] for record in records
                },
                "checks": {name: "pass" for name in CONTRACT["squint_review_checks"]},
                "observation": "The blurred overview preserves a clear focal sequence, varied emphasis, and balanced deck-wide density.",
                "limitations": ["text-overlap", "line-breaks", "crop", "distortion", "overflow"],
            }
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
        strategy = (
            "full"
            if scope == "all" and rendered_set == set(range(1, count + 1))
            else "incremental"
        )
        selected_set = set(requested) | set(changed)
        neighbor_set = {
            candidate
            for number in selected_set
            for candidate in (number - 1, number, number + 1)
            if 1 <= candidate <= count
        }
        if impact is None:
            impact = (
                "full" if strategy == "full"
                else "neighbors" if rendered_set == neighbor_set and rendered_set != selected_set
                else "direct"
            )
        content_changes = {
            "all": ["text", "image", "structure", "style", "runtime"] if strategy == "full" else ["style"],
            "text": ["text"],
            "image": ["image"],
            "navigation": ["runtime"],
        }[scope]
        return {
            "schema_version": CONTRACT["schema_version"],
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
                "contract_sha256": hashlib.sha256(CONTRACT_BYTES).hexdigest(),
                "browser": "chromium 149.0.0.0",
                "captured_at": "2026-07-14T00:00:00+00:00",
                "strategy": strategy,
                "requested_slides": requested,
                "rendered_slides": rendered,
                "directly_changed_slides": changed,
                "reused_slides": [number for number in range(1, count + 1) if number not in rendered_set],
                "animations_disabled": True,
                "requested_change_type": scope,
                "detected_change_type": "all" if scope == "all" else scope,
                "impact_scope": impact,
                "navigation_changed": "runtime" in content_changes,
                "content_changes": content_changes,
                "review_slides": ai_reviewed,
            },
            "source_fingerprints": {
                "global_sha256": global_hash,
                "previous_global_sha256": global_hash,
                "dependencies": [],
                "local_files": [],
                "global_components": {
                    "runtime_sha256": hashlib.sha256(b"runtime").hexdigest(),
                    "structure_sha256": hashlib.sha256(b"structure").hexdigest(),
                    "styles_sha256": hashlib.sha256(b"styles").hexdigest(),
                },
                "components": {
                    str(number): {
                        name: hashlib.sha256(f"{name}-{number}".encode()).hexdigest()
                        for name in (
                            "text_sha256", "media_sha256", "structure_sha256",
                            "styles_sha256", "transition_sha256",
                        )
                    }
                    for number in range(1, count + 1)
                },
                "slides": slide_hashes,
            },
            "viewports": {profile: dict(PROFILE_SPECS[profile]) for profile in profiles},
            "automation_gate": {
                "status": "pass",
                "checks": list({
                    "all": ("text_bounds", "font_integrity", "contrast", "container_density", "controls", "image_geometry"),
                    "text": ("text_bounds", "font_integrity", "contrast", "container_density"),
                    "image": ("image_geometry",),
                    "navigation": ("controls",),
                }[scope]),
                "failures": [],
                "warnings": [],
            },
            "review_batches": review_batches,
            "quality_score": quality,
            "cross_reviews": cross_reviews,
            "cross_review_batches": cross_review_batches,
            "squint_review": squint_review,
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
        capture_scope: str = "full",
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
            squint_review = manifest.get("squint_review")
            if isinstance(squint_review, dict) and squint_review.get("artifact_path"):
                squint_path = root / squint_review["artifact_path"]
                squint_path.parent.mkdir(parents=True, exist_ok=True)
                squint_path.write_bytes(png_bytes(960, 540))
            if stale_rendered:
                future = time.time_ns() + 2_000_000_000
                os.utime(deck, ns=(future, future))
            environment = os.environ.copy()
            environment["BUILD_HTML_SLIDES_UNIT_TEST"] = "1"
            return subprocess.run(
                [
                    "python3", str(VALIDATOR), str(deck), str(review),
                    "--capture-scope", capture_scope,
                ],
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

    def test_full_responsive_routes_ordinary_slides_to_normal_only(self) -> None:
        deck = deck_for(3)
        manifest = self.manifest(deck, count=3, mode="full", responsive=True)
        self.assertEqual(manifest["slides"][1]["required_ai_profiles"], ["normal"])
        result = self.validate(deck, manifest)
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
        self.assertIn(f"one to {CONTRACT['review_batch_size']} slide numbers", result.stdout)

    def test_text_change_requires_only_text_checks(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_text_change_rejects_unrelated_check_contract(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        manifest["slides"][2]["checks"]["crop"] = "pass"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unexpected ["crop"]', result.stdout)

    def test_missing_check_key_is_named_in_the_error(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        del manifest["slides"][0]["checks"]["contrast"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing ["contrast"]', result.stdout)
        self.assertIn('"contrast"', result.stdout)
        self.assertIn("required exactly, in order", result.stdout)

    def test_reordered_check_keys_report_ordering_not_membership(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck)
        checks = manifest["slides"][0]["checks"]
        manifest["slides"][0]["checks"] = dict(reversed(list(checks.items())))
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("keys out of order", result.stdout)

    def test_automation_only_review_shape_is_rejected(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        record = manifest["slides"][2]
        record["reviewer"] = ""
        record["reviewer_ref"] = ""
        record["review_method"] = "automated-geometry-only"
        record["observation"] = ""
        record["checks"] = {}
        record["status"] = "automation-pass"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("removed automation-only review shape", result.stdout)
        self.assertIn("slide 3 overall status must be pass", result.stdout)

    def test_every_slide_records_its_full_check_tuple(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        manifest["slides"][2]["checks"] = {}
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("slide 3 (all review scope) checks are wrong", result.stdout)

    def test_manifest_cannot_downscope_a_detected_image_change_to_text(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        manifest["render_run"]["detected_change_type"] = "image"
        manifest["render_run"]["content_changes"] = ["image"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("change_type improperly narrows the detected source change", result.stdout)

    def test_quick_routes_every_slide_to_ai_and_escalates_critical_ones(self) -> None:
        # Replaces test_quick_routes_only_critical_slides_to_ai. Do not "restore" that test: the
        # contract it asserted was unsatisfiable, not merely stricter. render_slides.js emits
        # reviewer "" / status "pending" / a full check tuple for every slide, and this validator
        # unconditionally requires reviewer + vision-batched-full-size + all checks pass for every
        # slide. Only batched slides ever receive a reviewer, so a slide left out of the review set
        # could reach "pass" only by fabricating a reviewer name and check verdicts for a capture
        # nobody opened - the exact defect (5 of 7 slides shipped unreviewed) this suite guards.
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        # Quick mode reviews every slide at the normal profile; there is no automation-only
        # escape hatch, so no slide can reach a passing status without a real vision review.
        self.assertEqual([batch["slides"] for batch in manifest["review_batches"]], [[1, 2, 3, 4], [5]])
        self.assertEqual(manifest["render_run"]["review_slides"], [1, 2, 3, 4, 5])
        # Cover and closing escalate to every profile; the interior slides stay at normal only.
        self.assertEqual(manifest["slides"][0]["required_ai_profiles"], list(BASE_PROFILES))
        self.assertEqual(manifest["slides"][4]["required_ai_profiles"], list(BASE_PROFILES))
        for index in (1, 2, 3):
            self.assertEqual(manifest["slides"][index]["required_ai_profiles"], ["normal"])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_quick_slide_cannot_pass_without_being_routed_to_a_reviewer(self) -> None:
        # This is the regression the removed quick-mode routing allowed: an interior slide that
        # ships with no vision review at all. Kept as a positive assertion so that reinstating the
        # old "only critical slides are routed" behaviour fails loudly here.
        deck = deck_for(5)
        manifest = self.manifest(deck, count=5)
        manifest["render_run"]["review_slides"] = [1, 2, 4, 5]
        manifest["review_batches"] = [{
            "id": "batch-01",
            "slides": [1, 2, 4, 5],
            "capture_profiles": {
                str(number): manifest["slides"][number - 1]["required_ai_profiles"]
                for number in (1, 2, 4, 5)
            },
            "status": "pending",
        }]
        for number in (1, 2, 4, 5):
            manifest["slides"][number - 1]["review_batch_id"] = "batch-01"
        manifest["slides"][2]["review_batch_id"] = ""
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("every refreshed AI-routed slide must appear in render_run review_slides", result.stdout)

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
        # Batching covers all five slides, not just [1, 3, 5]: every slide is routed now, so the
        # identity slide is no longer distinguished by *whether* it is reviewed, only by the extra
        # identity check it carries. Reverting this to [[1, 3, 5]] would require the unsatisfiable
        # routing described on test_quick_routes_every_slide_to_ai_and_escalates_critical_ones.
        self.assertEqual([batch["slides"] for batch in manifest["review_batches"]], [[1, 2, 3, 4], [5]])
        self.assertEqual(manifest["slides"][2]["required_ai_profiles"], ["normal"])
        self.assertIn("identity", manifest["slides"][2]["checks"])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pending_reused_identity_review_keeps_its_original_scope(self) -> None:
        deck = deck_for(5, identity=3)
        manifest = self.manifest(
            deck,
            count=5,
            rendered=[2],
            requested=[2],
            changed=[2],
            scope="text",
            identity=3,
        )
        # Slide 2 is the refreshed slide and must be reviewed; slide 3 is pulled in because its
        # identity review is still pending, and it keeps its original image-scoped identity work
        # even though this run only changed text. Slide 2 was absent from this review set before
        # the routing fix, which was only legal while a refreshed slide could opt out of vision
        # review entirely - see test_quick_routes_every_slide_to_ai_and_escalates_critical_ones.
        manifest["render_run"]["review_slides"] = [2, 3]
        manifest["review_batches"] = [{
            "id": "batch-01",
            "slides": [2, 3],
            "capture_profiles": {"2": ["normal"], "3": ["normal"]},
            "status": "pending",
        }]
        manifest["slides"][1]["review_batch_id"] = "batch-01"
        manifest["slides"][2]["review_batch_id"] = "batch-01"
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

    def test_direct_incremental_render_accepts_only_changed_slide(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_neighbor_impact_requires_changed_slide_and_neighbors(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(
            deck, 5, rendered=[3], requested=[3], changed=[3], scope="all", impact="neighbors"
        )
        manifest["render_run"]["content_changes"] = ["structure"]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("detected impact scope", result.stdout)

    def test_incremental_reuse_rejects_global_change(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="image")
        manifest["source_fingerprints"]["previous_global_sha256"] = hashlib.sha256(b"old-global").hexdigest()
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("global style/runtime change", result.stdout)

    def test_reused_slide_may_keep_older_capture(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
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

    def test_final_phase_requires_squint_review(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck, mode="full", phase="final")
        manifest["squint_review"] = None
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("final phase requires a passing squint_review", result.stdout)

    def test_squint_review_binds_current_normal_capture_hashes(self) -> None:
        deck = deck_for(2)
        manifest = self.manifest(deck, mode="full", phase="final")
        manifest["squint_review"]["normal_capture_sha256"]["1"] = "0" * 64
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("bind every current normal capture hash", result.stdout)

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

    def test_refreshed_capture_scope_skips_reused_pixel_rechecks(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        reused_blank = "normal/slide-01.png"
        focused = self.validate(
            deck,
            manifest,
            blank_capture=reused_blank,
            capture_scope="refreshed",
        )
        self.assertEqual(focused.returncode, 0, focused.stdout + focused.stderr)
        full = self.validate(deck, manifest, blank_capture=reused_blank, capture_scope="full")
        self.assertEqual(full.returncode, 1)
        self.assertIn("appears blank or near-solid", full.stdout)

    def test_refreshed_capture_scope_still_checks_changed_slide_pixels(self) -> None:
        deck = deck_for(5)
        manifest = self.manifest(deck, 5, rendered=[3], requested=[3], changed=[3], scope="text")
        result = self.validate(
            deck,
            manifest,
            blank_capture="normal/slide-03.png",
            capture_scope="refreshed",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("appears blank or near-solid", result.stdout)

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

    def test_final_full_rejects_pending_cross_review_batch(self) -> None:
        deck = deck_for(3)
        manifest = self.manifest(deck, 3, mode="full", phase="final")
        manifest["cross_review_batches"][0]["status"] = "pending"
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be marked complete", result.stdout)

    def test_final_full_requires_cross_review_for_cover(self) -> None:
        deck = deck_for(3)
        manifest = self.manifest(deck, 3, mode="full", phase="final")
        manifest["cross_reviews"] = [
            review for review in manifest["cross_reviews"] if review["slide"] != 1
        ]
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("slide 1 requires an independent final cross review", result.stdout)

    def test_standard_final_cross_review_is_risk_routed(self) -> None:
        deck = deck_for(20)
        manifest = self.manifest(deck, 20, mode="full", phase="final", review_risk="standard")
        reviewed = [review["slide"] for review in manifest["cross_reviews"]]
        self.assertEqual(reviewed, [1, 20])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_standard_final_rejects_cross_review_outside_generated_sample(self) -> None:
        deck = deck_for(20)
        manifest = self.manifest(deck, 20, mode="full", phase="final", review_risk="standard")
        extra_slide = 2
        batch_id = "cross-extra"
        manifest["cross_reviews"].append(
            self.cross_review(manifest["slides"][extra_slide - 1], False, batch_id)
        )
        manifest["cross_review_batches"].append({
            "id": batch_id,
            "slides": [extra_slide],
            "capture_profiles": {
                str(extra_slide): manifest["slides"][extra_slide - 1]["required_ai_profiles"]
            },
            "status": "pending",
        })
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 1)
        self.assertIn("slide 2 is outside the generated final cross-review set", result.stdout)

    def test_high_risk_final_keeps_cross_review_risk_routed(self) -> None:
        deck = deck_for(12)
        manifest = self.manifest(deck, 12, mode="full", phase="final", review_risk="high")
        self.assertEqual([review["slide"] for review in manifest["cross_reviews"]], [1, 12])
        result = self.validate(deck, manifest)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
