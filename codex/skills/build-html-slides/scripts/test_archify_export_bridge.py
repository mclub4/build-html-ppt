#!/usr/bin/env python3
"""Exercise deterministic Archify asset export and slide embedding."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIFY = ROOT.parent / "archify"
BRIDGE = ROOT / "scripts" / "export_archify_asset.js"
RENDERER = ROOT / "scripts" / "render_slides.js"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


class ArchifyExportBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        check = subprocess.run(
            ["node", str(RENDERER), "--check"], capture_output=True, text=True, check=False
        )
        if check.returncode:
            raise unittest.SkipTest(f"Playwright/Chromium preflight failed: {check.stderr.strip()}")
        if not (ARCHIFY / "examples" / "web-app-rendered.html").is_file():
            raise unittest.SkipTest("bundled Archify rendered example is unavailable")

    def export(self, root: Path, *, width: int = 1000) -> tuple[dict, Path, Path]:
        tokens = root / "theme.json"
        tokens.write_text(
            json.dumps(
                {
                    "background": "#f4f1ea",
                    "surface": "#fffdf8",
                    "text": "#171915",
                    "muted": "#62675d",
                    "line": "#c8c1b4",
                    "accent": "#176b5b",
                    "accent_2": "#7357a3",
                    "positive": "#2f7d4b",
                    "warning": "#b56a16",
                    "danger": "#b53a46",
                    "font_family": '"Noto Sans KR", sans-serif',
                }
            ),
            encoding="utf-8",
        )
        base = root / "architecture"
        result = subprocess.run(
            [
                "node",
                str(BRIDGE),
                str(ARCHIFY / "examples" / "web-app-rendered.html"),
                str(base),
                "--format",
                "both",
                "--width",
                str(width),
                "--tokens",
                str(tokens),
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout), base.with_suffix(".svg"), base.with_suffix(".webp")

    def test_exports_clean_theme_bound_svg_and_exact_webp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            receipt, svg_path, webp_path = self.export(Path(temporary), width=960)
            self.assertTrue(svg_path.is_file())
            self.assertTrue(webp_path.is_file())
            self.assertEqual(receipt["theme"], "light")
            self.assertTrue(receipt["controls_removed"])
            self.assertEqual(receipt["artifacts"]["webp"]["width"], 960)
            self.assertEqual(
                receipt["artifacts"]["webp"]["height"], receipt["dimensions"]["height"]
            )

            root = ET.parse(svg_path).getroot()
            local_names = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
            self.assertFalse(
                local_names & {"script", "foreignObject", "button", "input", "select", "textarea"}
            )
            source = svg_path.read_text(encoding="utf-8")
            self.assertIn('data-slide-asset="true"', source)
            self.assertIn('data-slide-theme-override="true"', source)
            self.assertIn("#f4f1ea", source)
            self.assertIn('font-family: "Noto Sans KR", sans-serif !important', source)

    def test_exported_webp_embeds_without_slide_geometry_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt, _svg_path, webp_path = self.export(root, width=1600)
            deck = root / "deck.html"
            html = TEMPLATE.read_text(encoding="utf-8")
            html = html.replace(
                "<!-- SLIDE_2_CONTENT -->",
                (
                    '<div style="display:grid;place-items:center;width:100%;height:100%;padding:56px 96px">'
                    '<img class="key-visual" src="architecture.webp" alt="System architecture" '
                    'data-media-purpose="evidence" style="width:1000px;height:auto">'
                    "</div>"
                ),
                1,
            )
            deck.write_text(html, encoding="utf-8")
            self.assertEqual(webp_path.name, "architecture.webp")
            review = root / "review"
            result = subprocess.run(
                [
                    "node",
                    str(RENDERER),
                    str(deck),
                    str(review),
                    "--mode",
                    "full",
                    "--review-risk",
                    "standard",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            manifest_path = review / "review.json"
            diagnostics = result.stdout + result.stderr
            if manifest_path.is_file():
                failed_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                diagnostics += "\n" + json.dumps(
                    failed_manifest.get("automation_gate", {}), ensure_ascii=False, indent=2
                )
            self.assertEqual(result.returncode, 0, diagnostics)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["automation_gate"]["status"], "pass")
            slide = manifest["slides"][1]
            image = slide["captures"]["normal"]["image_geometry"]
            self.assertTrue(image["ok"], image["issues"])
            self.assertEqual(image["items"][0]["naturalWidth"], receipt["dimensions"]["width"])
            self.assertEqual(image["items"][0]["naturalHeight"], receipt["dimensions"]["height"])


if __name__ == "__main__":
    unittest.main()
