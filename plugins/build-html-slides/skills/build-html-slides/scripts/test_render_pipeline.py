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
            slide["status"] = "pass"

    def validate(self, deck: Path, manifest_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(VALIDATOR), str(deck), str(manifest_path)],
            capture_output=True,
            text=True,
            check=False,
        )

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
            self.assertEqual(list(manifest["viewports"]), ["normal", "short", "zoom150"])
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
            self.assertEqual(list(manifest["slides"][0]["checks"]), ["text", "text_bounds"])
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

    def test_default_workspace_stays_under_codex_home_and_can_be_cleaned(self) -> None:
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
            self.assertEqual(manifest["review_workspace"]["storage"], "codex-home")
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


if __name__ == "__main__":
    unittest.main()
