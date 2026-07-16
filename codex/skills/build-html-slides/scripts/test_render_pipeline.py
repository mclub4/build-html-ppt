#!/usr/bin/env python3
"""Exercise full and incremental Chromium rendering end to end."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_slides.js"
VALIDATOR = ROOT / "scripts" / "validate_visual_review.py"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


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
        rendered = set(manifest["render_run"]["rendered_slides"])
        reviewer_count = 1 if manifest["mode"] == "quick" else (3 if manifest["review_risk"] == "high" else 2)
        group_size = (len(manifest["slides"]) + reviewer_count - 1) // reviewer_count
        for slide in manifest["slides"]:
            if slide["slide"] not in rendered:
                continue
            if not slide["required_ai_profiles"]:
                self.assertEqual(slide["review_method"], "automated-geometry-only")
                self.assertEqual(slide["status"], "automation-pass")
                continue
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

    def validate(self, deck: Path, manifest_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(VALIDATOR), str(deck), str(manifest_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def create_webps(self, *targets: tuple[Path, str]) -> None:
        script = r"""
const fs = require('fs');
const { loadPlaywright } = require(process.argv[2]);
const { chromium } = loadPlaywright();
(async () => {
  const targets = JSON.parse(process.argv[1]);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  for (const target of targets) {
    const data = await page.evaluate(color => {
      const canvas = document.createElement('canvas');
      canvas.width = 800;
      canvas.height = 800;
      const context = canvas.getContext('2d');
      context.fillStyle = color;
      context.fillRect(0, 0, 800, 800);
      context.fillStyle = '#fff';
      context.fillRect(280, 280, 240, 240);
      return canvas.toDataURL('image/webp', 0.82).split(',')[1];
    }, target.color);
    fs.writeFileSync(target.path, Buffer.from(data, 'base64'));
  }
  await browser.close();
})();
"""
        payload = [{"path": str(path), "color": color} for path, color in targets]
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
            self.assertEqual(manifest["schema_version"], 8)
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
            self.assertIn("rendered 2/3 slides across 3 profiles (incremental", incremental.stdout)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_run"]["rendered_slides"], [1, 2])
            self.assertEqual(manifest["render_run"]["reused_slides"], [3])
            self.assertEqual(manifest["slides"][0]["review_scope"], "text")
            self.assertEqual(list(manifest["slides"][0]["checks"]), ["text", "text_bounds", "density"])
            self.assertEqual(reused_capture.stat().st_mtime_ns, reused_mtime)
            self.assertEqual(manifest["slides"][2]["captures"]["normal"]["sha256"], reused_hash)
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            second_validation = self.validate(deck, manifest_path)
            self.assertEqual(second_validation.returncode, 0, second_validation.stdout + second_validation.stderr)
            self.assertIn("2 refreshed slides use adaptive AI review", second_validation.stdout)

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
            for review in manifest["cross_reviews"]:
                review["reviewer"] = "final-editor"
                review["reviewer_ref"] = "final-editor-run-001"
                review["inspected_profiles"] = manifest["slides"][review["slide"] - 1]["required_ai_profiles"]
                review["observation"] = (
                    f"Independently opened slide {review['slide']} at every required profile and found no crop, text, or control defect."
                )
                review["checks"] = {name: "pass" for name in review["checks"]}
                review["status"] = "pass"
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

    def test_image_change_declared_as_text_is_widened_to_all(self) -> None:
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
            self.assertIn("widened to all", incremental.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["change_type"], "all")
            self.assertEqual(manifest["render_run"]["detected_change_type"], "image")
            self.assertEqual(manifest["slides"][1]["review_scope"], "all")

    def test_external_stylesheet_bytes_change_global_fingerprint(self) -> None:
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
            self.assertNotEqual(
                json.loads(before.stdout)["global_sha256"],
                json.loads(after.stdout)["global_sha256"],
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
                ["node", str(RENDERER), str(deck), str(review_dir), "--mode", "quick"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(render.returncode, 0, render.stderr)
            manifest_path = review_dir / "review.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.complete_rendered_reviews(manifest)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(self.validate(deck, manifest_path).returncode, 0)

            self.create_webps((image, "#882255"))
            stale = self.validate(deck, manifest_path)
            self.assertEqual(stale.returncode, 1)
            self.assertIn("slide source fingerprints do not match", stale.stdout)

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
            self.assertEqual(second["render_run"]["rendered_slides"], [1, 2, 3])
            self.assertEqual(second["render_run"]["reused_slides"], [4, 5])
            self.assertEqual(second["source_fingerprints"]["global_sha256"], global_hash)

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
                '<div class="card" style="width:900px;height:420px;border:1px solid #bbb"><p>짧은 사실</p></div>',
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

    def test_default_workspace_stays_under_agent_home_and_can_be_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            delivery = root / "delivery"
            delivery.mkdir()
            deck = delivery / "발표 자료 (최종).html"
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            deck_alias = root / "deck-alias.html"
            deck_alias.symlink_to(deck)
            codex_home = root / "codex-home"
            env = {**os.environ, "CODEX_HOME": str(codex_home)}

            review_lookup = subprocess.run(
                ["node", str(RENDERER), "--review-dir", str(deck)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(review_lookup.returncode, 0, review_lookup.stderr)
            review_dir = Path(review_lookup.stdout.strip())
            self.assertTrue(str(review_dir).startswith(str(codex_home)))
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
                ["node", str(RENDERER), str(deck), "--mode", "quick"],
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
            env = {key: value for key, value in os.environ.items() if key != "CODEX_HOME"}
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


if __name__ == "__main__":
    unittest.main()
