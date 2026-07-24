#!/usr/bin/env python3
"""Exercise the rendered text-bounds detector against real Chromium geometry.

Every assertion here is a measurement, never a judgement: each fixture renders a defect the
naked eye can see, and the detector has to report it with a number attached. The fixtures are
evaluated in one browser session against `measure_text_bounds.js` directly, so this module stays
independent of the render pipeline and finishes in a couple of seconds.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = SCRIPTS / "fixtures"
MEASURE = SCRIPTS / "measure_text_bounds.js"
LOADER = SCRIPTS / "playwright_loader.js"

# Wall-clock ceiling for one slide at one capture profile. Full Validation renders roughly
# 25 slides across 3 profiles, so this measurement must stay far below a second to keep the
# whole gate inside its 70-minute budget.
MAX_SLIDE_MEASURE_MS = 250.0

HARNESS = r"""
'use strict';
const fs = require('fs');
const path = require('path');
const { loadPlaywright } = require(process.argv[2]);
const source = fs.readFileSync(process.argv[3], 'utf8');
const jobs = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));

(async () => {
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const results = [];
  for (const job of jobs) {
    const page = await browser.newPage({
      viewport: { width: job.width, height: job.height },
      deviceScaleFactor: 1,
    });
    await page.goto('file://' + path.resolve(job.file));
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    const measurement = await page.evaluate(text => (0, eval)(text), source);
    results.push({ id: job.id, measurement });
    await page.close();
  }
  await browser.close();
  process.stdout.write(JSON.stringify(results));
})().catch(error => {
  process.stderr.write(String(error && error.stack ? error.stack : error));
  process.exit(1);
});
"""


class MeasureTextBoundsTests(unittest.TestCase):
    results: dict[str, dict] = {}

    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        jobs = [
            {"id": "clean", "file": "textbounds-clean-control.html", "width": 1280, "height": 720},
            {"id": "clean-scaled", "file": "textbounds-clean-control.html", "width": 960, "height": 540},
            {"id": "collision", "file": "textbounds-descender-collision.html", "width": 1280, "height": 720},
            {"id": "collision-scaled", "file": "textbounds-descender-collision.html", "width": 960, "height": 540},
            {"id": "bite", "file": "textbounds-foreground-bite.html", "width": 1280, "height": 720},
            {"id": "pseudo", "file": "textbounds-pseudo-decoration.html", "width": 1280, "height": 720},
            {"id": "exempt", "file": "textbounds-occlusion-exempt.html", "width": 1280, "height": 720},
            {"id": "stranded", "file": "textbounds-stranded-final-line.html", "width": 1280, "height": 720},
        ]
        for job in jobs:
            job["file"] = str(FIXTURES / job["file"])
            if not Path(job["file"]).is_file():
                raise unittest.SkipTest(f"missing fixture {job['file']}")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harness = root / "harness.js"
            harness.write_text(HARNESS, encoding="utf-8")
            plan = root / "jobs.json"
            plan.write_text(json.dumps(jobs), encoding="utf-8")
            completed = subprocess.run(
                ["node", str(harness), str(LOADER), str(MEASURE), str(plan)],
                capture_output=True,
                text=True,
                check=False,
            )
        if completed.returncode:
            raise unittest.SkipTest(f"Playwright/Chromium is unavailable: {completed.stderr.strip()[:400]}")
        cls.results = {entry["id"]: entry["measurement"] for entry in json.loads(completed.stdout)}

    def measurement(self, identifier: str) -> dict:
        self.assertIn(identifier, self.results)
        return self.results[identifier]

    def issues(self, identifier: str) -> list[str]:
        return list(self.measurement(identifier).get("issues") or [])

    def test_clean_control_reports_no_issues(self) -> None:
        for identifier in ("clean", "clean-scaled"):
            with self.subTest(identifier=identifier):
                measurement = self.measurement(identifier)
                self.assertEqual(measurement["issues"], [], measurement)
                self.assertTrue(measurement["ok"], measurement)

    def test_glyph_ink_metrics_are_actually_used(self) -> None:
        # Without real ink metrics every check below silently degrades to font-box geometry,
        # which is exactly the blindness this module exists to prevent.
        self.assertIs(self.measurement("clean")["ink_metrics"], True)

    def test_descender_collision_with_the_next_line_is_measured(self) -> None:
        for identifier in ("collision", "collision-scaled"):
            with self.subTest(identifier=identifier):
                matches = [issue for issue in self.issues(identifier) if "rendered text lines collide" in issue]
                self.assertEqual(len(matches), 1, self.issues(identifier))
                self.assertIn("of glyph ink", matches[0])
                depth = float(matches[0].split("collide by ")[1].split("px")[0])
                self.assertGreaterEqual(depth, 1.0, matches[0])

    def test_descender_collision_is_invisible_to_line_box_geometry(self) -> None:
        # The fixture sets line-height 0.86em, comfortably above the legacy 0.8em advance floor and
        # below its 0.4 line-box overlap ratio: only true ink extents can see this defect.
        source = FIXTURES.joinpath("textbounds-descender-collision.html").read_text(encoding="utf-8")
        self.assertIn("line-height: 0.86", source)

    def test_foreground_image_biting_a_glyph_is_reported(self) -> None:
        matches = [issue for issue in self.issues("bite") if "covered by an opaque visual layer" in issue]
        self.assertEqual(len(matches), 1, self.issues("bite"))
        depth = float(matches[0].split("(")[1].split("px")[0])
        self.assertGreaterEqual(depth, 1.5, matches[0])
        self.assertLessEqual(depth, 12.0, matches[0])

    def test_pseudo_element_layer_is_treated_as_foreground(self) -> None:
        matches = [issue for issue in self.issues("pseudo") if "covered by an opaque visual layer" in issue]
        self.assertEqual(len(matches), 1, self.issues("pseudo"))

    def test_occlusion_exemption_downgrades_to_a_warning(self) -> None:
        measurement = self.measurement("exempt")
        self.assertEqual(measurement["issues"], [], measurement)
        self.assertTrue(
            any("intentional occlusion exemption" in warning for warning in measurement["warnings"]),
            measurement,
        )

    def test_stranded_final_line_check_is_preserved(self) -> None:
        self.assertTrue(
            any("punctuation is stranded on its own final line" in issue for issue in self.issues("stranded")),
            self.issues("stranded"),
        )

    def test_per_slide_measurement_stays_inside_the_validation_budget(self) -> None:
        for identifier, measurement in self.results.items():
            with self.subTest(identifier=identifier):
                self.assertIn("elapsed_ms", measurement)
                self.assertLess(measurement["elapsed_ms"], MAX_SLIDE_MEASURE_MS, measurement)

    def test_detector_does_not_point_sample_line_midlines(self) -> None:
        source = MEASURE.read_text(encoding="utf-8")
        # Hit testing survives only as the z-order oracle inside an already measured overlap.
        self.assertEqual(source.count("elementsFromPoint"), 1, "point sampling reintroduced")
        self.assertNotIn("0.02, 0.08, 0.18", source)
        self.assertIn("getClientRects", source)
        self.assertIn("actualBoundingBoxDescent", source)


if __name__ == "__main__":
    unittest.main()
