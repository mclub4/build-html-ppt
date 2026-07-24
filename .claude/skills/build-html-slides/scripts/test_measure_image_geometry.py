#!/usr/bin/env python3
"""Measure the image geometry probe against fixtures that reproduce shipped visual defects.

Every fixture here encodes a defect that a prose reviewer previously rationalised away:
a subject photo skipped because it lived in `.slide-media`, an image escaping its card while
staying inside the slide, and a subject rendered far too small to read on a projector.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "measure_image_geometry.js"
LOADER = ROOT / "scripts" / "playwright_loader.js"
FIXTURES = ROOT / "scripts" / "fixtures"

RUNNER = r"""
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const request = JSON.parse(process.argv[1]);
const { loadPlaywright } = require(request.loader);
const { chromium } = loadPlaywright();
const source = fs.readFileSync(request.script, 'utf8');

(async () => {
  const browser = await chromium.launch({ headless: true, args: request.args });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const output = {};
  for (const deck of request.decks) {
    await page.goto(pathToFileURL(deck).href, { waitUntil: 'load' });
    await page.evaluate(() => Promise.all(
      [...document.images].filter(image => !image.complete).map(image => new Promise(resolve => {
        image.addEventListener('load', resolve, { once: true });
        image.addEventListener('error', resolve, { once: true });
      }))
    ));
    output[path.basename(deck)] = await page.evaluate(text => (0, eval)(text), source);
  }
  await browser.close();
  process.stdout.write(JSON.stringify(output));
})().catch(error => {
  process.stderr.write(String(error && error.stack || error));
  process.exit(1);
});
"""

# The renderer launches Chromium with this flag, so the alpha probe is measured the same way.
FILE_ACCESS_ARGS = ["--allow-file-access-from-files"]
DECKS = [
    "imggeom-clean.html",
    "imggeom-subject-in-slide-media.html",
    "imggeom-card-overflow.html",
    "imggeom-small-subject.html",
    "imggeom-transparent-subject.html",
]


def measure(decks: list[str], args: list[str]) -> dict:
    payload = {
        "loader": str(LOADER),
        "script": str(SCRIPT),
        "decks": [str(FIXTURES / deck) for deck in decks],
        "args": args,
    }
    result = subprocess.run(
        ["node", "-e", RUNNER, json.dumps(payload)],
        cwd=ROOT.parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(f"measurement run failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


class ImageGeometryMeasurementTests(unittest.TestCase):
    results: dict

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        for deck in DECKS:
            if not (FIXTURES / deck).is_file():
                raise unittest.SkipTest(f"missing fixture {deck}")
        try:
            cls.results = measure(DECKS, FILE_ACCESS_ARGS)
        except AssertionError as error:
            raise unittest.SkipTest(f"Playwright/Chromium unavailable: {error}") from error

    def deck(self, name: str) -> dict:
        return self.results[name]

    def item(self, name: str, label: str) -> dict:
        matches = [item for item in self.deck(name)["items"] if item["name"] == label]
        self.assertEqual(len(matches), 1, self.deck(name)["items"])
        return matches[0]

    def issues(self, name: str) -> list[str]:
        return self.deck(name)["issues"]

    def warnings(self, name: str) -> list[str]:
        return self.deck(name)["warnings"]

    # --- clean baseline -------------------------------------------------

    def test_clean_subject_card_stays_silent(self) -> None:
        deck = self.deck("imggeom-clean.html")
        self.assertTrue(deck["ok"], deck["issues"])
        self.assertEqual(deck["issues"], [])
        self.assertEqual(deck["warnings"], [])
        self.assertEqual(deck["checked"], 2)

    def test_aria_hidden_backdrop_remains_decorative(self) -> None:
        backdrop = self.deck("imggeom-clean.html")["items"][0]
        self.assertTrue(backdrop["decorative"])
        self.assertEqual(backdrop["decorativeReason"], "aria-hidden")
        # A decorative cover crop must not spend reviewer time on crop inspection.
        self.assertEqual(self.warnings("imggeom-clean.html"), [])

    def test_contained_subject_records_zero_container_overflow(self) -> None:
        subject = self.item("imggeom-clean.html", "Flagship handset")
        self.assertEqual(subject["container"]["reason"], "explicit-container")
        self.assertEqual(subject["container"]["name"], "card")
        self.assertEqual(
            subject["container"]["overflow"], {"left": 0, "right": 0, "top": 0, "bottom": 0}
        )

    # --- defect A: decorative misclassification -------------------------

    def test_subject_photo_inside_slide_media_is_not_decorative(self) -> None:
        subject = self.item("imggeom-subject-in-slide-media.html", "Flagship handset")
        self.assertFalse(
            subject["decorative"],
            "a declared subject photo inside .slide-media must stay in scope",
        )
        self.assertEqual(subject["decorativeReason"], "declared-meaningful-purpose")
        self.assertEqual(subject["mediaPurpose"], "subject")

    def test_subject_inside_slide_media_is_still_measured_for_prominence(self) -> None:
        deck = self.deck("imggeom-subject-in-slide-media.html")
        self.assertFalse(deck["ok"])
        self.assertTrue(
            any("subject prominence minimum" in issue for issue in deck["issues"]),
            deck["issues"],
        )

    def test_declared_purpose_vocabulary_drives_classification(self) -> None:
        hero = self.item("imggeom-small-subject.html", "Launch key visual")
        self.assertFalse(hero["decorative"])
        self.assertEqual(hero["decorativeReason"], "declared-hero-role")
        self.assertEqual(hero["imageRole"], "hero")
        self.assertEqual(hero["subjectTier"], "hero")

    # --- defect B: container containment --------------------------------

    def test_image_escaping_its_card_raises_an_issue_with_both_rects(self) -> None:
        escaping = [
            issue for issue in self.issues("imggeom-card-overflow.html")
            if issue.startswith("Escaping detail: image overflows its container")
        ]
        self.assertEqual(len(escaping), 1, self.issues("imggeom-card-overflow.html"))
        message = escaping[0]
        self.assertIn("card", message)
        for edge in ("left 60px", "right 60px", "top 40px", "bottom 40px"):
            self.assertIn(edge, message)
        self.assertIn("image 520x340", message)
        self.assertIn("container 400x260", message)

    def test_overflowing_image_stays_inside_the_slide(self) -> None:
        # The shipped defect stayed inside the slide, so the legacy slide-bounds test never fired.
        self.assertFalse(
            any("crosses active slide bounds" in issue
                for issue in self.issues("imggeom-card-overflow.html")),
            self.issues("imggeom-card-overflow.html"),
        )

    def test_sibling_image_inside_its_card_is_not_reported(self) -> None:
        contained = self.item("imggeom-card-overflow.html", "Contained detail")
        self.assertEqual(
            contained["container"]["overflow"], {"left": 0, "right": 0, "top": 0, "bottom": 0}
        )
        self.assertFalse(
            any(issue.startswith("Contained detail")
                for issue in self.issues("imggeom-card-overflow.html")),
            self.issues("imggeom-card-overflow.html"),
        )

    # --- defect C: subject prominence -----------------------------------

    def test_small_subject_passes_resolution_but_fails_prominence(self) -> None:
        packaging = self.item("imggeom-small-subject.html", "Packaging detail")
        self.assertGreaterEqual(packaging["pixelDensity"], 1.25)
        self.assertLess(packaging["subjectAreaRatio"], 0.02)
        self.assertTrue(
            any("Packaging detail" in issue and "subject prominence minimum" in issue
                for issue in self.issues("imggeom-small-subject.html")),
            self.issues("imggeom-small-subject.html"),
        )

    def test_hero_subject_below_hero_minimum_raises_an_issue(self) -> None:
        hero = self.item("imggeom-small-subject.html", "Launch key visual")
        self.assertAlmostEqual(hero["subjectAreaRatio"], 0.0625, places=4)
        self.assertTrue(
            any("Launch key visual" in issue and "hero prominence minimum" in issue
                for issue in self.issues("imggeom-small-subject.html")),
            self.issues("imggeom-small-subject.html"),
        )

    def test_heavily_downscaled_subject_warns(self) -> None:
        self.assertTrue(
            any("renders at 0.2x its intrinsic size" in warning
                for warning in self.warnings("imggeom-small-subject.html")),
            self.warnings("imggeom-small-subject.html"),
        )
        # A 2x retina source rendered at 1x must not warn.
        self.assertFalse(
            any("Contained detail" in warning and "intrinsic size" in warning
                for warning in self.warnings("imggeom-card-overflow.html")),
            self.warnings("imggeom-card-overflow.html"),
        )

    def test_transparent_padding_is_discounted_from_subject_area(self) -> None:
        boxed = self.item("imggeom-transparent-subject.html", "Boxed accessory")
        self.assertAlmostEqual(boxed["stageAreaRatio"], 0.1736, places=3)
        self.assertLess(boxed["bodyBoxFraction"], 0.12)
        self.assertLess(boxed["subjectAreaRatio"], 0.02)
        self.assertTrue(
            any("opaque body" in issue and "subject prominence minimum" in issue
                for issue in self.issues("imggeom-transparent-subject.html")),
            self.issues("imggeom-transparent-subject.html"),
        )

    def test_alpha_probe_failure_degrades_to_the_full_rendered_box(self) -> None:
        # Without --allow-file-access-from-files the canvas readback throws; the probe must fall
        # back to the undiscounted box instead of failing the measurement.
        blind = measure(["imggeom-transparent-subject.html"], [])
        deck = blind["imggeom-transparent-subject.html"]
        boxed = deck["items"][0]
        self.assertNotIn("bodyBoxFraction", boxed)
        self.assertAlmostEqual(boxed["subjectAreaRatio"], boxed["stageAreaRatio"], places=4)
        self.assertEqual(deck["issues"], [])

    # --- contract preservation ------------------------------------------

    def test_legacy_issue_strings_are_preserved(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for message in (
            "Missing active slide",
            "image has no rendered size",
            "image element crosses active slide bounds",
            "image did not load with valid intrinsic dimensions",
            "image is stretched because object-fit is fill",
            "meaningful cover-cropped image requires full-size visual crop inspection",
            "effective raster resolution is only ",
            "effective raster resolution is borderline at ",
            "identity review requires data-subject-id",
            "identity review requires data-subject-name",
            "identity review requires data-identity-reference",
            "identity review requires at least two semicolon-separated identity cues",
            "data-identity-mode must be primary or contains",
            "Identity review requires at least one annotated non-decorative image",
            'data-identity-review="not-applicable" conflicts with subject identity metadata',
        ):
            self.assertIn(message, source, message)

    def test_container_vocabulary_matches_density_probe(self) -> None:
        # Both probes must agree on what counts as a container, or an image can overflow a card
        # that only one of them recognises.
        density = (ROOT / "scripts" / "measure_container_density.js").read_text(encoding="utf-8")
        geometry = SCRIPT.read_text(encoding="utf-8")
        for token in (".card", ".panel", ".tile", ".box", "[data-density-container]"):
            self.assertIn(token, density, token)
            self.assertIn(token, geometry, token)


if __name__ == "__main__":
    unittest.main()
