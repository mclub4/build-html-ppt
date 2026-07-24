#!/usr/bin/env python3
"""Regression tests for validate_deck.py image and layer contracts."""

from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = SKILL_ROOT / "scripts" / "validate_deck.py"
GEOMETRY_CHECK = SKILL_ROOT / "scripts" / "measure_geometry.js"
TEMPLATE = SKILL_ROOT / "assets" / "runtime-shell.html"
EMPTY_MEDIA = '<div class="slide-media" aria-hidden="true"></div>'


class ValidateDeckTests(unittest.TestCase):
    def validate(self, html: str, assets: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = root / "deck.html"
            deck.write_text(html, encoding="utf-8")
            for asset in assets:
                (root / asset).touch()
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck)],
                check=False,
                capture_output=True,
                text=True,
            )

    def template_with(self, replacement: str) -> str:
        return TEMPLATE.read_text(encoding="utf-8").replace(EMPTY_MEDIA, replacement, 1)

    def test_starter_template_passes(self) -> None:
        result = self.validate(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_webp_image_passes(self) -> None:
        html = self.template_with(
            '<div class="slide-media" aria-hidden="true"><img src="asset.webp" alt="test"></div>'
        )
        result = self.validate(html, ("asset.webp",))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_alt_is_blocking(self) -> None:
        html = self.template_with(
            '<div class="slide-media" aria-hidden="true"><img src="asset.webp"></div>'
        )
        result = self.validate(html, ("asset.webp",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("image is missing alt", result.stdout)

    def test_png_image_fails(self) -> None:
        html = self.template_with(
            '<div class="slide-media" aria-hidden="true"><img src="asset.png" alt="test"></div>'
        )
        result = self.validate(html, ("asset.png",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("raster image must be WebP", result.stdout)

    def test_svg_identity_reference_fails_even_when_svg_images_are_otherwise_allowed(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_1_CONTENT -->",
            '<img class="key-visual" src="candidate.webp" alt="Character" '
            'data-identity-reference="official.svg">',
            1,
        )
        result = self.validate(html, ("candidate.webp", "official.svg"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("identity reference must be a local WebP", result.stdout)

    def test_css_png_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "</style>", '.test-bg{background-image:url("asset.png")}</style>', 1
        )
        result = self.validate(html, ("asset.png",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("raster image must be WebP (CSS url())", result.stdout)

    def test_css_webp_fails_layer_contract(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "</style>", '.test-bg{background-image:url("asset.webp")}</style>', 1
        )
        result = self.validate(html, ("asset.webp",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("raster image must be an element inside .slide-media", result.stdout)

    def test_svg_diagram_ancestor_allows_webp_image(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<div class="slide-content">',
            '<div class="slide-content"><div class="safe-media"><svg class="diagram">'
            '<image href="asset.webp"></image></svg></div>',
            1,
        )
        result = self.validate(html, ("asset.webp",))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_direct_foreground_image_outside_content_fails(self) -> None:
        html = self.template_with(
            '<div class="slide-media" aria-hidden="true"></div>'
            '<img class="key-visual" src="asset.webp" alt="test">'
        )
        result = self.validate(html, ("asset.webp",))
        self.assertEqual(result.returncode, 1)
        self.assertIn("image elements outside slide-media", result.stdout)

    def test_direct_inner_width_scaling_fails_even_with_visual_viewport(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "(() => {", "(() => { const legacyScale=Math.min(innerWidth/1920,innerHeight/1080);", 1
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("direct innerWidth/innerHeight ratio", result.stdout)

    def test_constant_based_inner_width_scaling_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "(() => {",
            "(() => { const LEGACY_WIDTH=1920;const LEGACY_HEIGHT=1080;"
            "const sx=window.innerWidth/LEGACY_WIDTH;const sy=window.innerHeight/LEGACY_HEIGHT;",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("direct innerWidth/innerHeight ratio", result.stdout)

    def test_geometry_check_accepts_template_nav_selector(self) -> None:
        template = TEMPLATE.read_text(encoding="utf-8")
        geometry = GEOMETRY_CHECK.read_text(encoding="utf-8")
        self.assertIn('class="nav"', template)
        self.assertIn("querySelector('.controls, .nav')", geometry)

    def test_template_nav_has_no_visible_slide_title(self) -> None:
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn('class="nav-title"', template)
        self.assertNotIn('id="navTitle"', template)

    def test_generic_system_font_only_deck_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8")
        html = re.sub(r'--font-display:\s*[^;]+;', '--font-display: system-ui, sans-serif;', html)
        html = re.sub(r'--font-body:\s*[^;]+;', '--font-body: system-ui, sans-serif;', html)
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("deliberate named display/body font stack", result.stdout)

    def test_theme_font_variables_are_required(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace("--font-display:", "--removed-display:", 1)
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("typography must declare --font-display", result.stdout)

    def test_geometry_checks_page_counter_centers(self) -> None:
        geometry = GEOMETRY_CHECK.read_text(encoding="utf-8")
        self.assertIn(".page-separator, .pager-separator", geometry)
        self.assertIn("Math.abs(dy) > 1.5", geometry)

    def test_reserved_source_class_cannot_be_reused_as_component_modifier(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<div class="event-stream source"><b>source stream</b><span>delta</span></div>',
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("reserved citation class .source", result.stdout)


if __name__ == "__main__":
    unittest.main()
