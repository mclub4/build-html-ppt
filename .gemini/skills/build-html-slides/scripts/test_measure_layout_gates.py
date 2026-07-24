#!/usr/bin/env python3
"""Rendered regression tests for the deterministic layout gates.

Every assertion here runs the real measurement script inside real Chromium against a
rendered fixture. The gates under test replaced reviewer prose with measurement:

* ``measure_container_density.js`` finds layout regions without needing a card, border,
  or background, so surfaceless editorial spreads are no longer invisible to it.
* ``measure_geometry.js`` enforces the lower-right navigation exclusion zone that seven
  documents describe and nothing used to check at runtime.
* ``measure_contrast.js`` computes a provable contrast interval over image, gradient, and
  scrim backdrops instead of emitting an advisory "needs a look" warning.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "fixtures"
LOADER = ROOT / "scripts" / "playwright_loader.js"
DENSITY_SCRIPT = ROOT / "scripts" / "measure_container_density.js"
GEOMETRY_SCRIPT = ROOT / "scripts" / "measure_geometry.js"
CONTRAST_SCRIPT = ROOT / "scripts" / "measure_contrast.js"

DRIVER = r"""
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const [loaderPath, deck, checks, scriptDir] = process.argv.slice(2);
const { loadPlaywright } = require(loaderPath);
const sources = {};
for (const name of checks.split(',')) {
  const file = {
    density: 'measure_container_density.js',
    geometry: 'measure_geometry.js',
    contrast: 'measure_contrast.js',
  }[name];
  sources[name] = fs.readFileSync(path.join(scriptDir, file), 'utf8');
}

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await context.newPage();
    await page.goto(pathToFileURL(deck).href, { waitUntil: 'load' });
    await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
    const titles = await page.evaluate(
      () => [...document.querySelectorAll('section.slide')].map(slide => slide.dataset.title || '')
    );
    const result = {};
    for (let number = 1; number <= titles.length; number += 1) {
      await page.evaluate(target => {
        document.querySelectorAll('section.slide').forEach((slide, index) => {
          slide.classList.toggle('active', index === target - 1);
        });
      }, number);
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      result[titles[number - 1]] = {};
      for (const [name, source] of Object.entries(sources)) {
        result[titles[number - 1]][name] = await page.evaluate(code => (0, eval)(code), source);
      }
    }
    const leaked = await page.evaluate(() => [...document.querySelectorAll('style')]
      .filter(style => style.textContent.includes('pointer-events: auto !important')).length);
    result.__leaked_hit_test_styles__ = leaked;
    process.stdout.write(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => {
  process.stderr.write(String(error && error.stack ? error.stack : error));
  process.exit(1);
});
"""


class LayoutGateTests(unittest.TestCase):
    _driver: Path | None = None
    _cache: dict[tuple[str, str], dict] = {}

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
        handle.write(DRIVER)
        handle.close()
        cls._driver = Path(handle.name)
        try:
            cls.measure("layoutgate-density.html", "density")
        except unittest.SkipTest:
            raise
        except Exception as error:  # pragma: no cover - environment guard
            raise unittest.SkipTest(f"Chromium measurement is unavailable: {error}") from error

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._driver and cls._driver.exists():
            cls._driver.unlink()

    @classmethod
    def measure(cls, fixture: str, checks: str) -> dict:
        key = (fixture, checks)
        if key in cls._cache:
            return cls._cache[key]
        result = subprocess.run(
            [
                "node",
                str(cls._driver),
                str(LOADER),
                str(FIXTURES / fixture),
                checks,
                str(ROOT / "scripts"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            message = result.stderr.strip()
            if "playwright" in message.lower() or "executable doesn't exist" in message.lower():
                raise unittest.SkipTest(f"Playwright/Chromium preflight failed: {message}")
            raise AssertionError(f"driver failed for {fixture}: {message}")
        payload = json.loads(result.stdout)
        cls._cache[key] = payload
        return payload

    # ------------------------------------------------------------------ density

    def test_density_measures_every_slide_without_a_visible_surface(self) -> None:
        payload = self.measure("layoutgate-density.html", "density")
        slides = {name: value for name, value in payload.items() if not name.startswith("__")}
        self.assertEqual(len(slides), 6)
        for name, value in slides.items():
            self.assertGreaterEqual(value["density"]["regions"], 1, f"{name} produced no measured region")

    def test_density_flags_surfaceless_editorial_spread(self) -> None:
        density = self.measure("layoutgate-density.html", "density")["editorial-spread-underfilled"]["density"]
        self.assertEqual(density["regions"], 2)
        measured = [item for item in density["items"] if item["measured"]]
        self.assertTrue(all(item["candidateReason"] == "layout-item" for item in measured), measured)
        self.assertTrue(all(item["warning"] for item in measured), measured)
        self.assertEqual(len(density["warnings"]), 2, density["warnings"])
        for warning in density["warnings"]:
            self.assertIn("oversized low-information region", warning)
            self.assertIn("ink ", warning)

    def test_density_does_not_flag_a_statement_composition(self) -> None:
        density = self.measure("layoutgate-density.html", "density")["statement-poster"]["density"]
        measured = [item for item in density["items"] if item["measured"]]
        self.assertTrue(measured)
        self.assertTrue(all(item["statementComposition"] for item in measured), measured)
        self.assertEqual(density["warnings"], [])

    def test_density_does_not_flag_filled_flat_colour_blocks(self) -> None:
        density = self.measure("layoutgate-density.html", "density")["flat-colour-blocks-filled"]["density"]
        self.assertEqual(density["regions"], 2)
        self.assertEqual(density["warnings"], [])

    def test_density_flags_an_empty_colour_block(self) -> None:
        density = self.measure("layoutgate-density.html", "density")["empty-colour-block"]["density"]
        self.assertEqual(density["regions"], 2)
        self.assertEqual(len(density["warnings"]), 1, density["warnings"])
        empty = [item for item in density["items"] if item.get("warning")]
        self.assertEqual(len(empty), 1)
        self.assertEqual(empty[0]["characterCount"], 0)

    def test_density_flags_a_thin_content_band(self) -> None:
        density = self.measure("layoutgate-density.html", "density")["thin-band-rail"]["density"]
        self.assertEqual(len(density["warnings"]), 1, density["warnings"])
        measured = [item for item in density["items"] if item["measured"]]
        self.assertEqual(len(measured), 1, measured)
        # Enough copy to clear the low-ink rule, but all of it clustered in one band.
        self.assertGreater(measured[0]["characterCount"], 240)
        self.assertLess(measured[0]["contentHeightRatio"], 0.5)
        self.assertTrue(measured[0]["subdivision"])

    def test_density_leaves_whole_slide_emptiness_to_the_completion_gate(self) -> None:
        density = self.measure(
            "layoutgate-density.html", "density"
        )["whole-slide-region-is-not-a-container"]["density"]
        measured = [item for item in density["items"] if item["measured"]]
        self.assertEqual(len(measured), 1, measured)
        self.assertFalse(measured[0]["subdivision"])
        self.assertEqual(measured[0]["characterCount"], 0)
        self.assertEqual(density["warnings"], [])

    def test_density_never_double_counts_a_nested_region(self) -> None:
        payload = self.measure("layoutgate-density.html", "density")
        for name, value in payload.items():
            if name.startswith("__"):
                continue
            density = value["density"]
            groups = [item for item in density["items"] if item["measured"] is False]
            self.assertEqual(density["groups"], len(groups))
            for group in groups:
                self.assertEqual(group["role"], "group")
                self.assertFalse(group["warning"], f"{name} warned on an enclosing region")

    # --------------------------------------------------------------- navigation

    def geometry_zone_issues(self, slide: str) -> list[str]:
        payload = self.measure("layoutgate-nav.html", "geometry")
        return [
            issue for issue in payload[slide]["geometry"]["issues"]
            if "navigation exclusion zone" in issue
        ]

    def test_navigation_zone_is_derived_from_the_css_variables(self) -> None:
        payload = self.measure("layoutgate-nav.html", "geometry")
        exclusion = payload["clear-lower-right"]["geometry"]["navExclusion"]
        self.assertEqual(exclusion["source"], "css-variable")
        self.assertEqual(exclusion["width"], 280)
        self.assertEqual(exclusion["height"], 84)

    def test_navigation_zone_documents_the_280x84_fallback(self) -> None:
        source = GEOMETRY_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("NAV_EXCLUSION_FALLBACK_WIDTH = 280", source)
        self.assertIn("NAV_EXCLUSION_FALLBACK_HEIGHT = 84", source)

    def test_footer_note_intruding_into_the_zone_is_blocking(self) -> None:
        issues = self.geometry_zone_issues("footer-note-intrudes")
        self.assertEqual(len(issues), 1, issues)
        self.assertIn(".footnote", issues[0])
        self.assertIn("text intrudes", issues[0])
        self.assertRegex(issues[0], r"intrudes \d+(\.\d+)?×\d+(\.\d+)?px")

    def test_nav_safe_note_helper_clears_the_zone(self) -> None:
        self.assertEqual(self.geometry_zone_issues("nav-safe-note-clears"), [])

    def test_explicit_opt_out_suppresses_the_zone_gate(self) -> None:
        self.assertEqual(self.geometry_zone_issues("explicit-opt-out"), [])

    def test_corner_image_intruding_into_the_zone_is_blocking(self) -> None:
        issues = self.geometry_zone_issues("corner-image-intrudes")
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("media intrudes", issues[0])

    def test_corner_surface_intruding_into_the_zone_is_blocking(self) -> None:
        issues = self.geometry_zone_issues("corner-badge-intrudes")
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("surface intrudes", issues[0])

    def test_clear_lower_right_slide_passes_the_zone_gate(self) -> None:
        self.assertEqual(self.geometry_zone_issues("clear-lower-right"), [])

    # ----------------------------------------------------------------- contrast

    def contrast_for(self, slide: str) -> dict:
        return self.measure("layoutgate-contrast.html", "contrast")[slide]["contrast"]

    def test_contrast_over_an_image_can_fail_deterministically(self) -> None:
        result = self.contrast_for("image-backdrop-provable-fail")
        self.assertEqual(result["deferred"], 0)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("at most", result["issues"][0])
        self.assertIn("against every backdrop this text can sit on", result["issues"][0])
        self.assertIn("below the required 4.5:1", result["issues"][0])
        self.assertEqual(result["items"][0]["method"], "measured-backdrop")
        self.assertEqual(result["items"][0]["reason"], "sampled image pixels")

    def test_contrast_over_an_image_can_pass_deterministically(self) -> None:
        result = self.contrast_for("image-backdrop-provable-pass")
        self.assertTrue(result["ok"])
        self.assertEqual(result["deferred"], 0)
        self.assertEqual(result["items"][0]["status"], "pass")
        self.assertEqual(result["items"][0]["method"], "measured-backdrop")

    def test_contrast_over_a_scrim_resolves_through_the_layer_stack(self) -> None:
        result = self.contrast_for("scrim-over-image-pass")
        self.assertTrue(result["ok"])
        self.assertEqual(result["deferred"], 0)
        item = result["items"][0]
        self.assertEqual(item["status"], "pass")
        self.assertGreaterEqual(item["worstRatio"], 4.5)

    def test_contrast_over_a_gradient_is_bounded_by_its_stops(self) -> None:
        passing = self.contrast_for("gradient-bounds-pass")
        failing = self.contrast_for("gradient-bounds-fail")
        self.assertTrue(passing["ok"])
        self.assertEqual(passing["items"][0]["reason"], "gradient stop bounds")
        self.assertFalse(failing["ok"])
        self.assertEqual(failing["items"][0]["reason"], "gradient stop bounds")
        self.assertLess(failing["items"][0]["bestRatio"], 4.5)

    def test_undecidable_contrast_demands_a_confirm_or_refute_observation(self) -> None:
        for slide in ("image-backdrop-undecidable", "canvas-backdrop-undecidable"):
            with self.subTest(slide=slide):
                result = self.contrast_for(slide)
                self.assertEqual(result["deferred"], 1, result["items"])
                self.assertEqual(len(result["warnings"]), 1)
                warning = result["warnings"][0]
                self.assertIn("UNDECIDABLE contrast", warning)
                self.assertIn("CONFIRM or REFUTE", warning)
                self.assertIn("location-specific observation", warning)
                self.assertIn("is not an accepted answer", warning)
                self.assertRegex(warning, r"worst point at x -?\d+, y -?\d+")
                self.assertIn("measured range", warning)

    def test_canvas_backdrop_names_the_unsamplable_layer(self) -> None:
        result = self.contrast_for("canvas-backdrop-undecidable")
        self.assertIn("<canvas> whose pixels cannot be sampled", result["warnings"][0])

    def test_advisory_contrast_delegation_wording_is_gone(self) -> None:
        source = CONTRAST_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("requires full-size visual review", source)
        self.assertIn("CONFIRM or REFUTE", source)

    def test_hit_testing_override_never_leaks_into_the_capture(self) -> None:
        payload = self.measure("layoutgate-contrast.html", "contrast")
        self.assertEqual(payload["__leaked_hit_test_styles__"], 0)

    # -------------------------------------------------------------- constants

    def test_density_thresholds_are_named_constants(self) -> None:
        source = DENSITY_SCRIPT.read_text(encoding="utf-8")
        for constant in (
            "MIN_REGION_SLIDE_RATIO",
            "DISPLAY_TYPE_PX",
            "STATEMENT_DISPLAY_COVERAGE",
            "LOW_INK_COVERAGE",
            "BAND_EXTENT_RATIO",
        ):
            self.assertIn(constant, source)


if __name__ == "__main__":
    unittest.main()
