#!/usr/bin/env python3
"""Exercise full and incremental Chromium rendering end to end."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_slides.js"
VALIDATOR = ROOT / "scripts" / "validate_visual_review.py"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"
FONT_FIXTURE = ROOT / "scripts" / "fixtures" / "inter-latin-400-normal.woff2"


class RenderPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        check = subprocess.run(
            ["node", str(RENDERER), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        if check.returncode:
            raise unittest.SkipTest(f"Playwright/Chromium preflight failed: {check.stderr.strip()}")

    def complete_rendered_reviews(self, manifest: dict) -> None:
        reviewed = set(manifest["render_run"].get("review_slides", manifest["render_run"]["rendered_slides"]))
        reviewer_count = 1 if manifest["mode"] == "quick" else (3 if manifest["review_risk"] == "high" else 2)
        group_size = (len(manifest["slides"]) + reviewer_count - 1) // reviewer_count
        for slide in manifest["slides"]:
            if slide["slide"] not in reviewed:
                continue
            self.assertTrue(
                slide["required_ai_profiles"],
                f"slide {slide['slide']} was rendered without any recorded visual review",
            )
            group = min((slide["slide"] - 1) // group_size, reviewer_count - 1)
            slide["reviewer"] = f"render-smoke-{group + 1}"
            slide["reviewer_ref"] = f"agent-render-smoke-{group + 1:03}"
            slide["inspected_profiles"] = slide["required_ai_profiles"]
            slide["observation"] = (
                f"Opened slide {slide['slide']} once with all current profiles; visible content and boundaries remain clear."
            )
            slide["checks"] = {name: "pass" for name in slide["checks"]}
            slide["identity_review"] = [
                {
                    "target_id": target["target_id"],
                    "subject_name": target["subject_name"],
                    "verdict": "pass",
                    "observation": "Candidate and canonical reference share the red hair and star badge without any conflicting character cues.",
                }
                for target in slide.get("identity_targets", [])
            ]
            slide["status"] = "pass"

    @staticmethod
    def png_size(path: Path) -> str:
        header = path.read_bytes()[:24]
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise AssertionError(f"not a PNG: {path}")
        return f"{int.from_bytes(header[16:20], 'big')}x{int.from_bytes(header[20:24], 'big')}"

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def validate(self, deck: Path, manifest_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(VALIDATOR), str(deck), str(manifest_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def create_webps(self, *targets: tuple[Path, str] | tuple[Path, str, int], split: bool = False) -> None:
        script = r"""
const fs = require('fs');
const { loadPlaywright } = require(process.argv[2]);
const { chromium } = loadPlaywright();
(async () => {
  const targets = JSON.parse(process.argv[1]);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  for (const target of targets) {
    const data = await page.evaluate(({ color, size, split }) => {
      const canvas = document.createElement('canvas');
      canvas.width = size || 800;
      canvas.height = size || 800;
      const context = canvas.getContext('2d');
      context.fillStyle = color;
      context.fillRect(0, 0, canvas.width, canvas.height);
      if (split) {
        // Half the frame is the flat colour and half is white, so text laid across the seam
        // samples both passing and failing backdrops: the undecidable case that must defer.
        context.fillStyle = '#ffffff';
        context.fillRect(canvas.width * 0.25, 0, canvas.width * 0.75, canvas.height);
      } else {
        context.fillStyle = '#fff';
        context.fillRect(280, 280, 240, 240);
      }
      return canvas.toDataURL('image/webp', 0.82).split(',')[1];
    }, { color: target.color, size: target.size, split: target.split });
    fs.writeFileSync(target.path, Buffer.from(data, 'base64'));
  }
  await browser.close();
})();
"""
        payload = [
            {
                "path": str(target[0]),
                "color": target[1],
                "size": target[2] if len(target) == 3 else 800,
                "split": split,
            }
            for target in targets
        ]
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                json.dumps(payload),
                str(ROOT / "scripts" / "playwright_loader.js"),
            ],
            cwd=ROOT.parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_renderer_requires_explicit_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            render = subprocess.run(
                ["node", str(RENDERER), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 2)
            self.assertIn("user-approved mode", render.stderr)

    def test_low_contrast_text_blocks_automation_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<div style="width:100%;height:100%;background:#fff;padding:120px">'
                    '<p style="color:#aaa;font-size:24px">Low contrast body copy</p></div>',
                    1,
                ),
                encoding="utf-8",
            )
            review = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1, render.stdout + render.stderr)
            manifest = json.loads((review / "review.json").read_text(encoding="utf-8"))
            failures = manifest["automation_gate"]["failures"]
            self.assertTrue(any(failure["check"] == "contrast" for failure in failures), failures)

    def test_image_backed_text_defers_contrast_to_visual_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "background.webp", "#888888", 2400), split=True)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                '<div class="slide-media" aria-hidden="true"></div>',
                '<div class="slide-media" aria-hidden="true"><img src="assets/background.webp" alt="" '
                'style="width:100%;height:100%;object-fit:cover"></div>',
                1,
            ).replace(
                "<!-- SLIDE_1_CONTENT -->",
                '<h1 style="margin:120px;color:#777">Image-backed title</h1>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            manifest = json.loads((review / "review.json").read_text(encoding="utf-8"))
            warnings = manifest["automation_gate"]["warnings"]
            self.assertTrue(any(warning["check"] == "contrast" for warning in warnings), warnings)
            # A warning is enough to earn a boundary overlay capture, not only a hard failure.
            warned = {warning["slide"] for warning in warnings}
            for record in manifest["slides"]:
                if record["slide"] not in warned:
                    continue
                self.assertTrue(record["debug_captures"], record["slide"])
                for relative in record["debug_captures"].values():
                    self.assertTrue((review / relative).is_file(), relative)

    def test_manifest_records_actual_bundled_font_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            shutil.copy2(FONT_FIXTURE, assets / "inter.woff2")
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<style>",
                "<style>@font-face{font-family:'Test Inter';src:url('assets/inter.woff2') format('woff2');"
                "font-style:normal;font-weight:400}",
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<p style="font-family:\'Test Inter\',sans-serif;font-size:32px">Portable font</p>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            diagnostics = render.stdout + render.stderr
            if (review / "review.json").is_file():
                failed = json.loads((review / "review.json").read_text(encoding="utf-8"))
                diagnostics += "\n" + json.dumps(failed.get("automation_gate", {}), indent=2)
                diagnostics += "\n" + json.dumps(
                    failed["slides"][1]["captures"]["normal"].get("font_integrity", {}),
                    indent=2,
                )
            self.assertEqual(render.returncode, 0, diagnostics)
            manifest = json.loads((review / "review.json").read_text(encoding="utf-8"))
            audit = manifest["slides"][1]["captures"]["normal"]["font_integrity"]
            self.assertTrue(audit["used_fonts"])
            self.assertTrue(any(font["custom"] for font in audit["used_fonts"]), audit)
            self.assertTrue(any(font["bundled_woff2"] for font in audit["used_fonts"]), audit)

    def test_full_then_incremental_render_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_1_CONTENT -->", "<h1>Initial slide content</h1>", 1
                ),
                encoding="utf-8",
            )
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            self.assertIn("rendered 3/3 slides across 3 profiles", initial.stdout)

            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], 13)
            self.assertEqual(list(manifest["viewports"]), ["normal", "short", "zoom150"])
            self.assertEqual(manifest["viewports"]["zoom150"]["viewport"], "1920x1080")
            self.assertEqual(manifest["viewports"]["zoom150"]["visual_viewport"], "1280x720")
            self.assertEqual(manifest["viewports"]["zoom150"]["scale_mode"], "browser-page")
            self.assertEqual(manifest["slides"][0]["captures"]["zoom150"]["device_pixel_ratio"], 1)
            self.assertEqual(manifest["phase"], "iteration")
            self.assertTrue(all(
                capture["motion_disabled"]
                for slide in manifest["slides"]
                for capture in slide["captures"].values()
            ))
            self.assertIn("transition: opacity 360ms", deck.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            first_validation = self.validate(deck, manifest_path)
            self.assertEqual(first_validation.returncode, 0, first_validation.stdout + first_validation.stderr)

            reused_capture = review_dir / manifest["slides"][2]["captures"]["normal"]["path"]
            reused_mtime = reused_capture.stat().st_mtime_ns
            reused_hash = manifest["slides"][2]["captures"]["normal"]["sha256"]
            deck.write_text(
                deck.read_text(encoding="utf-8").replace(
                    "Initial slide content", "Changed slide content", 1
                ),
                encoding="utf-8",
            )
            incremental = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "1", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(incremental.returncode, 0, incremental.stderr)
            self.assertIn("rendered 1/3 slides across 3 profiles (incremental", incremental.stdout)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1])
            self.assertEqual(manifest["render_run"]["reused_slides"], [2, 3])
            self.assertEqual(manifest["render_run"]["impact_scope"], "direct")
            self.assertEqual(manifest["slides"][0]["review_scope"], "text")
            self.assertEqual(list(manifest["slides"][0]["checks"]), ["text", "text_bounds", "contrast", "density"])
            self.assertEqual(reused_capture.stat().st_mtime_ns, reused_mtime)
            self.assertEqual(manifest["slides"][2]["captures"]["normal"]["sha256"], reused_hash)
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            second_validation = self.validate(deck, manifest_path)
            self.assertEqual(second_validation.returncode, 0, second_validation.stdout + second_validation.stderr)
            self.assertIn("1 refreshed slides use adaptive AI review", second_validation.stdout)

            selected_capture = review_dir / manifest["slides"][0]["captures"]["normal"]["path"]
            selected_mtime = selected_capture.stat().st_mtime_ns
            finalize = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize-prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize.returncode, 1)
            self.assertIn("Quick Draft finishes after verify", finalize.stderr)
            self.assertEqual(selected_capture.stat().st_mtime_ns, selected_mtime)

    def test_full_finalize_prepare_generates_bounded_cross_review_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
            self.assertEqual(self.validate(deck, manifest_path).returncode, 0)

            finalize = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize-prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize.returncode, 0, finalize.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["phase"], "final")
            self.assertTrue(manifest["cross_review_batches"])
            self.assertTrue(all(len(batch["slides"]) <= 4 for batch in manifest["cross_review_batches"]))
            squint_path = (review_dir / manifest["squint_review"]["artifact_path"]).resolve()
            self.assertTrue(squint_path.is_file())
            self.assertEqual(manifest["squint_review"]["status"], "pending")

            manifest["quality_score"] = {
                "status": "pass",
                "reviewer": "final-editor",
                "reviewer_ref": "final-editor-run-001",
                "dimensions": {name: 3 for name in (
                    "story", "art_direction", "layout_rhythm", "typography",
                    "imagery", "composition", "evidence", "presentation_utility",
                )},
                "total": 24,
                "weakest_slides": [1, 2, 3],
                "notes": "The settled deck keeps readable hierarchy, varied composition, and presentation-ready evidence.",
            }
            manifest["squint_review"].update({
                "status": "pass",
                "reviewer": "final-editor",
                "reviewer_ref": "final-editor-run-001",
                "checks": {name: "pass" for name in manifest["squint_review"]["checks"]},
                "observation": "The blurred contact sheet keeps a clear focal sequence, varied emphasis, and balanced color-density rhythm.",
            })
            for review in manifest["cross_reviews"]:
                review["reviewer"] = "final-editor"
                review["reviewer_ref"] = "final-editor-run-001"
                review["inspected_profiles"] = manifest["slides"][review["slide"] - 1]["required_ai_profiles"]
                review["observation"] = (
                    f"Independently opened slide {review['slide']} at every required profile and found no crop, text, or control defect."
                )
                review["checks"] = {name: "pass" for name in review["checks"]}
                review["status"] = "pass"
            for batch in manifest["cross_review_batches"]:
                batch["status"] = "complete"
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
            validation = self.validate(deck, manifest_path)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

            settled_evidence = manifest_path.read_bytes()
            repeated = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize-prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(repeated.returncode, 1)
            self.assertIn("refusing to reset quality or cross-review evidence", repeated.stderr)
            self.assertEqual(manifest_path.read_bytes(), settled_evidence)

    def test_incremental_fix_reuses_independent_cross_reviews_for_unchanged_slides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_1_CONTENT -->", "<p>Initial copy</p>", 1
            ).replace(
                "    </main>",
                '      <section class="slide" data-title="Slide 4"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Four</p></div></section>\n'
                '      <section class="slide" data-title="Slide 5"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Five</p></div></section>\n'
                "    </main>",
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
            finalize = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize-prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize.returncode, 0, finalize.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            initially_cross_reviewed = {review["slide"] for review in manifest["cross_reviews"]}
            self.assertIn(1, initially_cross_reviewed)
            for review in manifest["cross_reviews"]:
                review["reviewer"] = "independent-reviewer"
                review["reviewer_ref"] = "independent-review-run-001"
                review["inspected_profiles"] = manifest["slides"][review["slide"] - 1]["required_ai_profiles"]
                review["observation"] = (
                    f"Independently inspected slide {review['slide']} against its current captures and found no visual defect."
                )
                review["checks"] = {name: "pass" for name in review["checks"]}
                review["status"] = "pass"
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")

            deck.write_text(html.replace("Initial copy", "Revised copy"), encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "full",
                    "--slides", "1", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            retained = {review["slide"] for review in manifest["retained_cross_reviews"]}
            self.assertEqual(retained, initially_cross_reviewed - {1})
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
            finalize_again = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize-prepare"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize_again.returncode, 0, finalize_again.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            complete_slides = {
                number
                for batch in manifest["cross_review_batches"]
                if batch["status"] == "complete"
                for number in batch["slides"]
            }
            pending_slides = {
                number
                for batch in manifest["cross_review_batches"]
                if batch["status"] == "pending"
                for number in batch["slides"]
            }
            self.assertEqual(complete_slides, retained)
            self.assertEqual(pending_slides, {1})

    def test_reviewer_fail_requires_source_change_before_new_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_1_CONTENT -->", "<h1>Initial cover</h1>", 1
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["slides"][0]["status"] = "fail"
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")

            unchanged = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "1", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(unchanged.returncode, 1)
            self.assertIn("reviewer FAIL requires a source fix", unchanged.stderr)

            deck.write_text(html.replace("Initial cover", "Corrected cover"), encoding="utf-8")
            corrected = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "1", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(corrected.returncode, 0, corrected.stderr)
            corrected_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(corrected_manifest["render_run"]["rendered_slides"], [1])

    def test_image_change_declared_as_text_uses_detected_image_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "first.webp", "#225599"), (assets / "second.webp", "#992255"))
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<img src="assets/first.webp" alt="Product view" '
                    'style="width:320px;height:320px;object-fit:contain">',
                    1,
                ),
                encoding="utf-8",
            )
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            deck.write_text(
                deck.read_text(encoding="utf-8").replace("assets/first.webp", "assets/second.webp"),
                encoding="utf-8",
            )

            incremental = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(incremental.returncode, 0, incremental.stderr)
            self.assertIn("resolved to image", incremental.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["change_type"], "image")
            self.assertEqual(manifest["render_run"]["detected_change_type"], "image")
            self.assertEqual(manifest["render_run"]["rendered_slides"], [2])
            self.assertEqual(manifest["slides"][1]["review_scope"], "image")

    def test_external_stylesheet_rule_is_scoped_to_matching_slides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stylesheet = root / "theme.css"
            stylesheet.write_text(".slide h1 { color: rgb(10, 20, 30); }\n", encoding="utf-8")
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8")
                .replace("</head>", '<link rel="stylesheet" href="theme.css"></head>', 1)
                .replace("<!-- SLIDE_1_CONTENT -->", "<h1>Fingerprint target</h1>", 1),
                encoding="utf-8",
            )

            before = subprocess.run(
                ["node", str(RENDERER), "--fingerprints", str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(before.returncode, 0, before.stderr)
            stylesheet.write_text(".slide h1 { color: rgb(200, 40, 30); }\n", encoding="utf-8")
            after = subprocess.run(
                ["node", str(RENDERER), "--fingerprints", str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(after.returncode, 0, after.stderr)
            before_fingerprints = json.loads(before.stdout)
            after_fingerprints = json.loads(after.stdout)
            self.assertEqual(
                before_fingerprints["global_sha256"],
                after_fingerprints["global_sha256"],
            )
            self.assertNotEqual(
                before_fingerprints["slides"]["1"],
                after_fingerprints["slides"]["1"],
            )
            self.assertEqual(
                before_fingerprints["slides"]["2"],
                after_fingerprints["slides"]["2"],
            )

    def test_local_image_mutation_invalidates_existing_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            image = assets / "subject.webp"
            self.create_webps((image, "#225588"))
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<img src="assets/subject.webp" alt="Subject" '
                    'style="width:320px;height:320px;object-fit:contain">',
                    1,
                ),
                encoding="utf-8",
            )
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            first = self.validate(deck, manifest_path)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

            self.create_webps((image, "#882255"))
            stale = self.validate(deck, manifest_path)
            self.assertEqual(stale.returncode, 1)
            self.assertIn("local fingerprint entry 1 changed after rendering", stale.stdout)

    def test_inactive_responsive_srcset_asset_is_fingerprinted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            small = assets / "small.webp"
            large = assets / "large.webp"
            self.create_webps((small, "#225588"), (large, "#882255"))
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<picture><source media="(max-width:700px)" srcset="assets/small.webp">'
                    '<img src="assets/large.webp" alt="Responsive subject" '
                    'style="width:320px;height:320px;object-fit:contain"></picture>',
                    1,
                ),
                encoding="utf-8",
            )
            before = subprocess.run(
                ["node", str(RENDERER), "--fingerprints", str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(before.returncode, 0, before.stderr)
            before_fingerprints = json.loads(before.stdout)

            self.create_webps((small, "#118844"))
            after = subprocess.run(
                ["node", str(RENDERER), "--fingerprints", str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(after.returncode, 0, after.stderr)
            after_fingerprints = json.loads(after.stdout)
            self.assertNotEqual(
                before_fingerprints["components"]["2"]["media_sha256"],
                after_fingerprints["components"]["2"]["media_sha256"],
            )
            self.assertNotEqual(before_fingerprints["slides"]["2"], after_fingerprints["slides"]["2"])

    def test_opaque_visual_covering_text_blocks_quick_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            content = (
                '<h1 style="position:absolute;left:120px;top:120px;width:520px;z-index:1">Visible headline text</h1>'
                '<div style="position:absolute;left:100px;top:100px;width:600px;height:180px;'
                'background:#111;z-index:10"></div>'
            )
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace("<!-- SLIDE_2_CONTENT -->", content, 1),
                encoding="utf-8",
            )
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            issues = [
                failure["issue"] for failure in manifest["automation_gate"]["failures"]
                if failure["check"] == "text_bounds"
            ]
            self.assertTrue(any("opaque visual layer" in issue for issue in issues), issues)

    def test_noop_strong_emphasis_blocks_before_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            content = (
                '<h2 style="margin:120px;font-size:48px;font-weight:400;color:#111">'
                '보통 문장 <strong style="font-weight:inherit;color:inherit">강조 실패</strong></h2>'
            )
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace("<!-- SLIDE_2_CONTENT -->", content, 1),
                encoding="utf-8",
            )
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            issues = [failure["issue"] for failure in manifest["automation_gate"]["failures"]]
            self.assertTrue(any("has no visible emphasis" in issue for issue in issues), issues)

    def test_unsupported_declared_font_weight_blocks_before_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>",
                "@font-face{font-family:'Single Weight';src:local('Arial');font-weight:400}"
                ".unsupported-weight{font-family:'Single Weight';font-weight:800}</style>",
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<h2 class="unsupported-weight" style="margin:120px;font-size:48px">합성 굵기 차단</h2>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            issues = [failure["issue"] for failure in manifest["automation_gate"]["failures"]]
            self.assertTrue(any("outside its declared local faces" in issue for issue in issues), issues)

    def test_partial_korean_font_fallback_blocks_before_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>",
                "@font-face{font-family:'Partial Korean Fixture';src:local('Arial');font-weight:400}"
                ".partial-korean{font-family:'Partial Korean Fixture',sans-serif;font-weight:400}</style>",
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<h2 class="partial-korean" style="margin:100px;font-size:48px">'
                '응원팀은 성적표가 아니라 자꾸 다음 경기를 찾게 되는 이유로 고른다.</h2>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            failures = manifest["automation_gate"]["failures"]
            font_failures = [failure for failure in failures if failure["check"] == "font_integrity"]
            self.assertTrue(font_failures, failures)
            self.assertTrue(any("응(U+C751)" in failure["issue"] for failure in font_failures), font_failures)
            self.assertTrue(any("complete Korean font" in failure["issue"] for failure in font_failures), font_failures)

    def test_meaningful_cover_crop_routes_quick_slide_to_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "subject.webp", "#336699"))
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<img src="assets/subject.webp" alt="Named product" '
                    'style="width:320px;height:200px;object-fit:cover">',
                    1,
                ),
                encoding="utf-8",
            )
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            warnings = [warning for warning in manifest["automation_gate"]["warnings"] if warning["slide"] == 2]
            self.assertTrue(any("cover-cropped" in warning["warning"] for warning in warnings), warnings)
            self.assertTrue(manifest["slides"][1]["required_ai_profiles"])

    def test_low_effective_raster_density_blocks_before_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "small.webp", "#335577"))
            deck = root / "deck.html"
            deck.write_text(
                TEMPLATE.read_text(encoding="utf-8").replace(
                    "<!-- SLIDE_2_CONTENT -->",
                    '<img src="assets/small.webp" alt="Large product detail" '
                    'style="width:700px;height:700px;object-fit:contain">',
                    1,
                ),
                encoding="utf-8",
            )
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            issues = [failure["issue"] for failure in manifest["automation_gate"]["failures"]]
            self.assertTrue(any("effective raster resolution" in issue for issue in issues), issues)

    def test_single_slide_css_change_keeps_incremental_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>", ".slide-2-only{color:#123456}</style>", 1
            ).replace(
                "<!-- SLIDE_2_CONTENT -->", '<p class="slide-2-only">Scoped copy</p>', 1
            ).replace(
                "    </main>",
                '      <section class="slide" data-title="Slide 4"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Four</p></div></section>\n'
                '      <section class="slide" data-title="Slide 5"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Five</p></div></section>\n'
                "    </main>",
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            first = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            global_hash = first["source_fingerprints"]["global_sha256"]

            deck.write_text(html.replace("#123456", "#654321"), encoding="utf-8")
            incremental = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(incremental.returncode, 0, incremental.stderr)
            second = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(second["render_run"]["strategy"], "incremental")
            self.assertEqual(second["render_run"]["directly_changed_slides"], [2])
            self.assertEqual(second["render_run"]["rendered_slides"], [2])
            self.assertEqual(second["render_run"]["reused_slides"], [1, 3, 4, 5])
            self.assertEqual(second["render_run"]["impact_scope"], "direct")
            self.assertEqual(second["source_fingerprints"]["global_sha256"], global_hash)

    def test_structure_change_renders_changed_slide_and_neighbors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->", '<p class="scoped-copy">Scoped copy</p>', 1
            ).replace(
                "    </main>",
                '      <section class="slide" data-title="Slide 4"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Four</p></div></section>\n'
                '      <section class="slide" data-title="Slide 5"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Five</p></div></section>\n'
                "    </main>",
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            deck.write_text(
                html.replace(
                    '<p class="scoped-copy">Scoped copy</p>',
                    '<div class="scoped-copy"><p>Scoped copy</p></div>',
                ),
                encoding="utf-8",
            )
            incremental = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(incremental.returncode, 0, incremental.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["impact_scope"], "neighbors")
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1, 2, 3])
            self.assertEqual(manifest["render_run"]["reused_slides"], [4, 5])
            self.assertIn("structure", manifest["render_run"]["content_changes"])

    def test_slide_scoped_transition_change_includes_neighbors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>", ".slide-2-motion{transition:transform 200ms ease}</style>", 1
            ).replace(
                "<!-- SLIDE_2_CONTENT -->", '<p class="slide-2-motion">Scoped motion</p>', 1
            ).replace(
                "    </main>",
                '      <section class="slide" data-title="Slide 4"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Four</p></div></section>\n'
                '      <section class="slide" data-title="Slide 5"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Five</p></div></section>\n'
                "    </main>",
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            deck.write_text(html.replace("200ms", "420ms"), encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "all",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["impact_scope"], "neighbors")
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1, 2, 3])

    def test_slide_reordering_includes_neighbors_without_full_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "    </main>",
                '      <section class="slide" data-title="Slide 4"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Four</p></div></section>\n'
                '      <section class="slide" data-title="Slide 5"><div class="slide-media" aria-hidden="true"></div><div class="slide-content"><p>Five</p></div></section>\n'
                "    </main>",
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            reordered = html.replace('data-title="Slide 2"', 'data-title="SWAP"', 1)
            reordered = reordered.replace('data-title="Slide 3"', 'data-title="Slide 2"', 1)
            reordered = reordered.replace('data-title="SWAP"', 'data-title="Slide 3"', 1)
            deck.write_text(reordered, encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["impact_scope"], "neighbors")
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1, 2, 3, 4])
            self.assertEqual(manifest["render_run"]["reused_slides"], [5])

    def test_shared_css_change_renders_all_without_navigation_e2e_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>", ".slide{--qa-accent:#123456}</style>", 1
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            deck.write_text(html.replace("#123456", "#654321"), encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["strategy"], "full")
            self.assertEqual(manifest["render_run"]["impact_scope"], "full")
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1, 2, 3])
            self.assertFalse(manifest["render_run"]["navigation_changed"])
            self.assertEqual(manifest["render_run"]["content_changes"], ["style"])

    def test_global_wrapper_change_renders_all_without_navigation_e2e_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8")
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            deck.write_text(html.replace('<main class="stage"', '<main class="stage qa-revised"', 1), encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "all",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["strategy"], "full")
            self.assertFalse(manifest["render_run"]["navigation_changed"])
            self.assertEqual(manifest["render_run"]["content_changes"], ["structure"])

    def test_incremental_text_render_omits_unrelated_geometry_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->", "<p>Initial copy</p>", 1
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            initial = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initial.returncode, 0, initial.stderr)
            deck.write_text(html.replace("Initial copy", "Revised copy"), encoding="utf-8")
            revised = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "text",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(revised.returncode, 0, revised.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            for capture in manifest["slides"][1]["captures"].values():
                self.assertIn("text_geometry", capture)
                self.assertIn("container_density", capture)
                self.assertNotIn("image_geometry", capture)
                self.assertNotIn("control_geometry", capture)

    def test_failed_image_geometry_blocks_review_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                '<div class="slide-media" aria-hidden="true"></div>',
                '<div class="slide-media" aria-hidden="true"><img src="missing.webp" alt=""></div>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            self.assertIn("automated geometry gate blocked AI review", render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["automation_gate"]["status"], "fail")
            self.assertEqual(manifest["review_batches"], [])

    def test_fix_after_automation_failure_rerenders_only_failed_slide_then_batches_pending_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps(
                (assets / "small.webp", "#335577", 240),
                (assets / "large.webp", "#335577", 1600),
            )
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<img src="assets/small.webp" alt="Product detail" '
                'style="width:500px;height:500px;object-fit:contain">',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            failed = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1)
            first = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(first["review_batches"], [])

            deck.write_text(html.replace("small.webp", "large.webp"), encoding="utf-8")
            fixed = subprocess.run(
                [
                    "node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick",
                    "--slides", "2", "--change-type", "image",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(fixed.returncode, 0, fixed.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["rendered_slides"], [2])
            # The re-rendered slide is reviewed as well: a rendered slide never ships unreviewed.
            self.assertEqual(manifest["render_run"]["review_slides"], [1, 2, 3])
            self.assertEqual([batch["slides"] for batch in manifest["review_batches"]], [[1, 2, 3]])
            self.complete_rendered_reviews(manifest)
            manifest_path = review_dir / "review.json"
            manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
            validation = self.validate(deck, manifest_path)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

    def test_text_geometry_blocks_orphan_line_collision_and_nav_occlusion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>",
                """
                .qa-orphan { position:absolute; left:48px; top:38px; width:980px; margin:0; font-size:58px; line-height:1.1; }
                .qa-leading { position:absolute; left:48px; top:260px; width:850px; font-size:90px; line-height:.68; }
                .qa-overlap-a { position:absolute; left:72px; top:540px; margin:0; font-size:34px; }
                .qa-overlap-b { position:absolute; left:110px; top:548px; margin:0; font-size:34px; }
                .qa-footer { position:absolute; right:18px; bottom:18px; margin:0; font-size:20px; }
                </style>
                """,
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                """
                <div class="qa-orphan"><span>행사마다 표정은 달라도, 서점의 목소리는 하나입니</span><br><span>다.</span></div>
                <div class="qa-leading">다음 장면을<br>함께 만들어가요.</div>
                <p class="qa-overlap-a">First text region</p>
                <p class="qa-overlap-b">Second text region</p>
                <p class="qa-footer">One modular rule, many voices</p>
                """,
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            self.assertIn("automated geometry gate blocked AI review", render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            failures = [failure["issue"] for failure in manifest["automation_gate"]["failures"]]
            self.assertTrue(any("stranded Korean ending" in issue for issue in failures))
            self.assertTrue(any("rendered text lines collide" in issue for issue in failures))
            self.assertTrue(any("rendered text regions overlap" in issue for issue in failures))
            self.assertTrue(any("covered by navigation controls" in issue for issue in failures))
            self.assertEqual(manifest["review_batches"], [])

    def test_text_geometry_accepts_balanced_multiline_display_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>",
                """
                .qa-balanced { position:absolute; left:64px; top:72px; width:900px; margin:0; font-size:58px; line-height:1.08; }
                .qa-safe-footer { position:absolute; left:64px; bottom:76px; margin:0; font-size:20px; }
                </style>
                """,
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                """
                <h1 class="qa-balanced">행사마다 표정은 달라도,<br>서점의 목소리는 하나입니다.</h1>
                <p class="qa-safe-footer">Campaign posters and event leaflets</p>
                """,
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            failures = [failure for failure in manifest["automation_gate"]["failures"] if failure["slide"] == 2]
            self.assertEqual(failures, [])

    def test_line_break_exemption_routes_quick_slide_to_ai_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "</style>",
                ".qa-exempt { position:absolute; left:64px; top:72px; margin:0; font-size:58px; line-height:1.08; }</style>",
                1,
            ).replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<h1 class="qa-exempt" data-line-break-ok>의도적인 포스터 문장 구성입니<br>다.</h1>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            warnings = [
                warning for warning in manifest["automation_gate"]["warnings"]
                if warning["slide"] == 2 and "final-line exemption" in warning["warning"]
            ]
            self.assertEqual({warning["profile"] for warning in warnings}, {"normal", "short", "zoom150"})
            self.assertEqual(manifest["slides"][1]["required_ai_profiles"], ["normal", "short", "zoom150"])
            self.assertTrue(any(2 in batch["slides"] for batch in manifest["review_batches"]))

    def test_underfilled_container_warns_and_routes_slide_to_ai_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<div class="step-panel" style="width:900px;height:420px;background:#fff;border:1px solid #bbb">'
                '<p style="position:absolute;top:20px">짧은 사실</p>'
                '<span style="position:absolute;bottom:20px">01</span></div>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            warnings = [
                warning for warning in manifest["automation_gate"]["warnings"]
                if warning["slide"] == 2 and warning["check"] == "container_density"
            ]
            self.assertEqual({warning["profile"] for warning in warnings}, {"normal", "short", "zoom150"})
            self.assertEqual(manifest["slides"][1]["required_ai_profiles"], ["normal", "short", "zoom150"])
            self.assertTrue(any(2 in batch["slides"] for batch in manifest["review_batches"]))

    def test_oversized_term_note_and_citation_crowding_route_slide_to_ai_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<p data-term-note style="position:absolute;left:80px;bottom:54px;width:560px;'
                'padding:22px;background:#fff;font-size:20px">NXT — 대체 거래 시장</p>'
                '<p data-source-citation style="position:absolute;left:80px;bottom:48px;font-size:9px">'
                '출처 · 공식 자료</p>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            warnings = [
                warning for warning in manifest["automation_gate"]["warnings"]
                if warning["slide"] == 2 and warning["check"] == "container_density"
            ]
            messages = [warning["warning"] for warning in warnings]
            self.assertTrue(any("compact caption" in message for message in messages), messages)
            self.assertTrue(any("overlaps or crowds" in message for message in messages), messages)
            self.assertEqual({warning["profile"] for warning in warnings}, {"normal", "short", "zoom150"})
            self.assertEqual(manifest["slides"][1]["required_ai_profiles"], ["normal", "short", "zoom150"])

    def test_identity_contract_binds_reference_and_routes_quick_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            assets = root / "assets"
            identity = assets / "identity"
            identity.mkdir(parents=True)
            self.create_webps(
                (assets / "candidate.webp", "#cc3344"),
                (identity / "official.webp", "#993355"),
            )
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<img src="assets/candidate.webp" alt="Character A" style="width:320px;height:320px;object-fit:contain" '
                'data-subject-id="series:character-a" data-subject-name="Character A / 캐릭터 A" '
                'data-identity-reference="assets/identity/official.webp" '
                'data-identity-cues="red hair; star badge" data-identity-mode="primary">',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                render.returncode,
                0,
                render.stderr + (review_dir / "review.json").read_text(encoding="utf-8"),
            )
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = manifest["slides"][1]
            self.assertTrue(record["identity_required"])
            self.assertEqual(record["identity_detection"], "subject-metadata")
            self.assertEqual(record["required_ai_profiles"], ["normal"])
            self.assertEqual(len(record["identity_targets"]), 1)
            self.assertEqual(record["identity_targets"][0]["reference_path"], "assets/identity/official.webp")
            self.assertIn("content_match", record["checks"])
            self.assertIn("completion", record["checks"])
            self.assertIn("identity", record["checks"])
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            validation = self.validate(deck, manifest_path)
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

    def test_identity_contract_blocks_missing_reference_before_ai_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "candidate.webp", "#cc3344"))
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<img src="assets/candidate.webp" alt="Character A" style="width:320px;height:320px;object-fit:contain" '
                'data-subject-id="series:character-a" data-subject-name="Character A" '
                'data-identity-reference="assets/identity/missing.webp" '
                'data-identity-cues="red hair; star badge">',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            self.assertIn("automated geometry gate blocked AI review", render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["automation_gate"]["status"], "fail")
            self.assertEqual(manifest["review_batches"], [])

    def test_semantic_character_profile_cannot_bypass_identity_review_by_omitting_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "candidate.webp", "#4488cc"))
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<div class="character-profile"><img src="assets/candidate.webp" alt="Named character" '
                'style="width:320px;height:320px;object-fit:contain"></div>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            record = manifest["slides"][1]
            self.assertTrue(record["identity_required"])
            self.assertEqual(record["identity_detection"], "semantic-markup")
            self.assertTrue(any(
                "identity review requires data-subject-id" in failure["issue"]
                for failure in manifest["automation_gate"]["failures"]
            ))

    def test_descendant_person_content_kind_activates_identity_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "candidate.webp", "#225599"))
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<figure data-content-kind="person"><img src="assets/candidate.webp" alt="Named person" '
                'style="width:320px;height:320px;object-fit:contain"></figure>',
                1,
            )
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            record = manifest["slides"][1]
            self.assertTrue(record["identity_required"])
            self.assertEqual(record["identity_detection"], "semantic-markup")

    def test_debug_overlay_capture_accompanies_every_flagged_slide(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            self.create_webps((assets / "plate.webp", "#3d5a80", 1600))
            html = TEMPLATE.read_text(encoding="utf-8").replace(
                "<!-- SLIDE_2_CONTENT -->",
                '<div style="padding:80px 110px">'
                '<h2 style="font-size:46px;margin:0 0 26px;color:#101010">Collage or overflow?</h2>'
                '<div style="position:relative;width:520px;height:260px;border:2px solid #101010;'
                'border-radius:14px;background:#f3f3ef;overflow:visible">'
                '<img src="assets/plate.webp" alt="" style="position:absolute;left:-140px;top:-90px;'
                'width:520px;height:340px;object-fit:cover;display:block"></div></div>',
                1,
            )
            deck = root / "deck.html"
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 1, render.stdout + render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertTrue(any(
                failure["slide"] == 2 for failure in manifest["automation_gate"]["failures"]
            ))

            flagged = manifest["slides"][1]
            self.assertEqual(sorted(flagged["debug_captures"]), sorted(manifest["viewports"]))
            for profile, relative in flagged["debug_captures"].items():
                self.assertEqual(relative, f"{profile}/slide-02-debug.png")
                overlay_path = review_dir / relative
                self.assertTrue(overlay_path.is_file(), overlay_path)
                expected = manifest["viewports"][profile]["screenshot"]
                self.assertEqual(self.png_size(overlay_path), expected)
                overlay = flagged["captures"][profile]["debug_overlay"]
                self.assertEqual(overlay["path"], relative)
                self.assertEqual(overlay["sha256"], self.sha256(overlay_path))
                self.assertGreater(overlay["measured_issues"], 0)
                self.assertIn(f"slide 2 · {profile}", overlay["caption"])
                # The reviewer must be able to see who owns what: card frames, image frames,
                # per-line text ink, the reserved nav zone, and the escaping region itself.
                for kind in ("container", "image", "text-line", "nav-zone", "overflow"):
                    self.assertIn(kind, overlay["region_counts"], overlay["region_counts"])

            clean = manifest["slides"][0]
            self.assertEqual(clean["debug_captures"], {})
            self.assertNotIn("debug_overlay", clean["captures"]["normal"])
            self.assertFalse(list((review_dir / "normal").glob("slide-01-debug.png")))

    def test_content_security_policy_deck_still_renders_with_motion_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            template = TEMPLATE.read_text(encoding="utf-8")
            start = template.index("<style>")
            end = template.index("</style>") + len("</style>")
            stylesheet = template[start + len("<style>"):end - len("</style>")]
            stylesheet += (
                "\n.pad{padding:110px 120px;color:#101010}"
                "\n.pad h1{font-size:70px;margin:0}"
                "\n.pad h2{font-size:48px;margin:0 0 20px}"
                "\n.pad p{font-size:24px;margin:0}\n"
            )
            (root / "deck.css").write_text(stylesheet, encoding="utf-8")
            html = template[:start] + '<link rel="stylesheet" href="deck.css">' + template[end:]
            html = html.replace(
                "<head>",
                '<head>\n  <meta http-equiv="Content-Security-Policy" content="default-src \'self\' '
                "data:; script-src 'unsafe-inline'; style-src 'self'\">",
                1,
            )
            for number, body in (
                (1, '<div class="pad"><h1>Policy deck cover</h1></div>'),
                (2, '<div class="pad"><h2>Second slide</h2><p>Body copy under a strict policy.</p></div>'),
                (3, '<div class="pad"><h2>Closing</h2></div>'),
            ):
                html = html.replace(f"<!-- SLIDE_{number}_CONTENT -->", body, 1)
            deck = root / "deck.html"
            deck.write_text(html, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            # An inline <style> is refused by this policy, so the renderer must fall back to a
            # constructed stylesheet instead of claiming motion_disabled it never applied.
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)
            self.assertIn("constructed-stylesheet", render.stderr)
            manifest = json.loads((review_dir / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["automation_gate"]["failures"], [])
            for record in manifest["slides"]:
                for capture in record["captures"].values():
                    self.assertIs(capture["motion_disabled"], True)
                self.assertTrue(record["required_ai_profiles"])

    def test_change_scope_attribution_matches_the_edited_material(self) -> None:
        scoped_marker = '<style data-slide-scope="3"></style>'
        base = TEMPLATE.read_text(encoding="utf-8").replace("</head>", f"  {scoped_marker}\n</head>", 1)
        base = base.replace(
            "<!-- SLIDE_1_CONTENT -->",
            '<div class="pad"><h1 class="hero">Cover story</h1></div>',
            1,
        ).replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<div class="pad"><h2 class="metric">Baseline</h2><p class="note">Second slide body.</p></div>',
            1,
        ).replace(
            "<!-- SLIDE_3_CONTENT -->",
            '<div class="pad"><h2 class="closing">Closing</h2></div>',
            1,
        )

        def with_rule(source: str, rule: str) -> str:
            return source.replace("  </style>", f"  {rule}\n  </style>", 1)

        def reorder(source: str) -> str:
            blocks = re.findall(r'<section class="slide[^"]*"[^>]*>.*?</section>', source, re.DOTALL)
            self.assertEqual(len(blocks), 3, blocks)
            swapped = source.replace(blocks[1], "\x00", 1).replace(blocks[2], blocks[1], 1)
            return swapped.replace("\x00", blocks[2], 1)

        cases = [
            (
                "copy-only edit",
                lambda source: source.replace("Second slide body.", "Second slide body, revised."),
                {"detected": "text", "impact": "direct", "navigation_changed": False, "changed_slides": [2]},
            ),
            (
                "slide-local CSS",
                lambda source: with_rule(source, ".metric{letter-spacing:0.4px}"),
                {"detected": "all", "impact": "direct", "navigation_changed": False, "changed_slides": [2]},
            ),
            (
                "data-slide-scope CSS",
                lambda source: source.replace(scoped_marker, '<style data-slide-scope="3">.closing{opacity:0.99}</style>'),
                {"detected": "all", "impact": "direct", "navigation_changed": False, "changed_slides": [3]},
            ),
            (
                "multi-slide CSS rule",
                lambda source: with_rule(source, ".metric,.closing{text-transform:none}"),
                {"detected": "all", "impact": "direct", "navigation_changed": False, "changed_slides": [2, 3]},
            ),
            (
                # A rule matching nothing today must still be attributed somewhere. Dropping it
                # from every fingerprint reports a real edit as "no change" and reuses stale
                # captures as PASS evidence.
                "inert CSS rule",
                lambda source: with_rule(source, ".not-in-this-deck{color:#ff0000}"),
                {"detected": "all", "impact": "full", "navigation_changed": False, "changed_slides": []},
            ),
            (
                "shared theme CSS",
                lambda source: with_rule(source, ".slide-content{letter-spacing:0.1px}"),
                {"detected": "all", "impact": "full", "navigation_changed": False, "changed_slides": []},
            ),
            (
                "structural reorder",
                reorder,
                {"detected": "all", "impact": "neighbors", "navigation_changed": False, "changed_slides": [2, 3]},
            ),
            (
                "runtime change",
                lambda source: source.replace("const STAGE_WIDTH = 1280;", "const STAGE_WIDTH = 1280; /* revised */"),
                {"detected": "all", "impact": "full", "navigation_changed": True, "changed_slides": []},
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "deck.html"
            deck.write_text(base, encoding="utf-8")
            review_dir = root / "review"
            render = subprocess.run(
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)

            for name, mutate, expected in cases:
                with self.subTest(change=name):
                    mutated = mutate(base)
                    self.assertNotEqual(mutated, base, name)
                    deck.write_text(mutated, encoding="utf-8")
                    classify = subprocess.run(
                        [
                            "node", str(RENDERER), "--classify-change", str(deck), str(review_dir),
                            "all", "full", "standard", "false",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(classify.returncode, 0, classify.stderr)
                    report = json.loads(classify.stdout)
                    self.assertEqual(
                        {key: report[key] for key in expected},
                        expected,
                        f"{name}: {classify.stdout}",
                    )
                    deck.write_text(base, encoding="utf-8")

    def test_default_workspace_stays_under_agent_home_and_can_be_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            delivery = root / "delivery"
            delivery.mkdir()
            deck = delivery / "발표 자료 (최종).html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            deck_alias = root / "deck-alias.html"
            deck_alias.symlink_to(deck)
            # BUILD_HTML_SLIDES_AGENT_HOME is the agent-neutral override, so this assertion holds
            # identically in codex/, .claude/, .gemini/ and plugins/ copies of the suite. Asserting
            # CODEX_HOME instead made the mirrored suites fail purely because of their own path.
            agent_home = root / "agent-home"
            env = {**os.environ, "BUILD_HTML_SLIDES_AGENT_HOME": str(agent_home)}
            env.pop("BUILD_HTML_SLIDES_WORKSPACE_ROOT", None)

            review_lookup = subprocess.run(
                ["node", str(RENDERER), "--review-dir", str(deck)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(review_lookup.returncode, 0, review_lookup.stderr)
            review_dir = Path(review_lookup.stdout.strip())
            self.assertTrue(review_dir.is_relative_to(agent_home), review_dir)
            self.assertEqual(review_dir.name, "review")
            alias_lookup = subprocess.run(
                ["node", str(RENDERER), "--review-dir", str(deck_alias)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(alias_lookup.returncode, 0, alias_lookup.stderr)
            self.assertEqual(Path(alias_lookup.stdout.strip()), review_dir)

            render = subprocess.run(
                ["node", str(RENDERER), str(deck), "--mode", "full"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            self.assertTrue((review_dir / "review.json").is_file())
            self.assertTrue((review_dir.parent / "drafts").is_dir())
            self.assertTrue((review_dir.parent / "tmp").is_dir())
            self.assertFalse((delivery / "review").exists())

            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["review_workspace"]["storage"], "agent-home")
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            validation = subprocess.run(
                ["python3", str(VALIDATOR), str(deck_alias)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

            clean = subprocess.run(
                ["node", str(RENDERER), "--clean-workspace", str(deck)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertFalse(review_dir.parent.exists())

    def test_claude_config_dir_selects_claude_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "claude-deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            claude_home = root / "claude-home"
            env = {
                key: value for key, value in os.environ.items()
                if key not in {
                    "CODEX_HOME",
                    "BUILD_HTML_SLIDES_AGENT_HOME",
                    "BUILD_HTML_SLIDES_WORKSPACE_ROOT",
                }
            }
            env["CLAUDE_CONFIG_DIR"] = str(claude_home)

            lookup = subprocess.run(
                ["node", str(RENDERER), "--workspace-dir", str(deck)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(lookup.returncode, 0, lookup.stderr)
            self.assertTrue(Path(lookup.stdout.strip()).is_relative_to(claude_home))

    def test_gemini_home_selects_gemini_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            deck = root / "gemini-deck.html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            gemini_home = root / "gemini-home"
            env = {
                key: value for key, value in os.environ.items()
                if key not in {
                    "CODEX_HOME",
                    "CLAUDE_CONFIG_DIR",
                    "CLAUDE_HOME",
                    "BUILD_HTML_SLIDES_AGENT_HOME",
                    "BUILD_HTML_SLIDES_WORKSPACE_ROOT",
                }
            }
            env["GEMINI_HOME"] = str(gemini_home)

            lookup = subprocess.run(
                ["node", str(RENDERER), "--workspace-dir", str(deck)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(lookup.returncode, 0, lookup.stderr)
            self.assertTrue(Path(lookup.stdout.strip()).is_relative_to(gemini_home))


if __name__ == "__main__":
    unittest.main()
