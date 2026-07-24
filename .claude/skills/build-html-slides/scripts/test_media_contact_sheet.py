#!/usr/bin/env python3
"""Exercise the batched sourced-media contact-sheet builder."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_media_contact_sheet.js"
RENDERER = ROOT / "scripts" / "render_slides.js"


class MediaContactSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if shutil.which("node") is None:
            raise unittest.SkipTest("Node.js is unavailable")
        check = subprocess.run(
            ["node", str(RENDERER), "--check"], capture_output=True, text=True, check=False
        )
        if check.returncode:
            raise unittest.SkipTest(f"Playwright/Chromium preflight failed: {check.stderr.strip()}")

    def create_webp(self, target: Path, color: str) -> None:
        script = r"""
const fs=require('fs');
const {loadPlaywright}=require(process.argv[1]);
(async()=>{const {chromium}=loadPlaywright();const browser=await chromium.launch({headless:true});
const page=await browser.newPage();const data=await page.evaluate(color=>{const canvas=document.createElement('canvas');
canvas.width=960;canvas.height=640;const context=canvas.getContext('2d');context.fillStyle=color;
context.fillRect(0,0,960,640);return canvas.toDataURL('image/webp',.82).split(',')[1];},process.argv[3]);
fs.writeFileSync(process.argv[2],Buffer.from(data,'base64'));await browser.close();})();
"""
        result = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(ROOT / "scripts" / "playwright_loader.js"),
                str(target),
                color,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_builds_batched_pngs_with_identity_cues_and_duplicate_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.webp"
            second = root / "second.webp"
            duplicate = root / "duplicate.webp"
            self.create_webp(first, "#d44d36")
            self.create_webp(second, "#245f8f")
            duplicate.write_bytes(first.read_bytes())
            manifest = root / "media-roster.json"
            manifest.write_text(
                json.dumps(
                    {
                        "title": "Artwork and athlete audit",
                        "items": [
                            {
                                "id": "art-1",
                                "label": "Artwork One",
                                "kind": "artwork",
                                "path": first.name,
                                "cue": "One red field",
                                "source_url": "https://museum.example/work",
                                "min_width": 900,
                            },
                            {
                                "id": "person-1",
                                "label": "Player One",
                                "kind": "person",
                                "path": second.name,
                                "cue": "Blue uniform",
                                "source_url": "https://club.example/player",
                            },
                            {
                                "id": "art-duplicate",
                                "label": "Duplicate Candidate",
                                "kind": "artwork",
                                "path": duplicate.name,
                                "cue": "Should be caught by hash",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "audit"
            result = subprocess.run(
                [
                    "node",
                    str(BUILDER),
                    str(manifest),
                    str(output),
                    "--batch-size",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((output / "media-contact-sheet-01.png").is_file())
            self.assertTrue((output / "media-contact-sheet-02.png").is_file())
            index = json.loads((output / "media-contact-sheet-index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["batch_size"], 2)
            self.assertEqual(len(index["sheets"]), 2)
            self.assertEqual(index["duplicate_hashes"][0]["items"], ["art-1", "art-duplicate"])
            self.assertIn("Deep-research only flagged items", index["review_instruction"])


if __name__ == "__main__":
    unittest.main()
