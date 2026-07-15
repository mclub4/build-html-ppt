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
        for slide in manifest["slides"]:
            if slide["slide"] not in rendered:
                continue
            if not slide["required_ai_profiles"]:
                self.assertEqual(slide["review_method"], "automated-geometry-only")
                self.assertEqual(slide["status"], "automation-pass")
                continue
            slide["reviewer"] = "render-smoke"
            slide["reviewer_ref"] = "agent-render-smoke-001"
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
const { chromium } = require('playwright');
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
            ["node", "-e", script, json.dumps(payload)],
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
            deck.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
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
            self.assertEqual(manifest["schema_version"], 7)
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
                    "<!-- SLIDE_1_CONTENT -->", "<h1>Changed slide content</h1>", 1
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
                ["node", str(RENDERER), str(deck), str(review_dir), "--finalize"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(finalize.returncode, 0, finalize.stderr)
            self.assertIn("without re-rendering", finalize.stdout)
            self.assertEqual(selected_capture.stat().st_mtime_ns, selected_mtime)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_path.write_text(f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
            final_validation = self.validate(deck, manifest_path)
            self.assertEqual(final_validation.returncode, 0, final_validation.stdout + final_validation.stderr)
            self.assertIn("without quality scoring", final_validation.stdout)

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
