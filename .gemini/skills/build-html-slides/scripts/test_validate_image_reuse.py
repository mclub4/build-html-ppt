#!/usr/bin/env python3
"""Regression tests for the cross-slide image reuse gate.

This validator ran in the deterministic command set with zero test coverage.
The near-duplicate slide that shipped in the reported defective deck is exactly
what this gate is supposed to catch, so its behaviour is pinned here.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_image_reuse.py"

WEBP_ONE = bytes.fromhex(
    "524946461a000000574542505650384c0d0000002f00000010071011118888e807000000"
)[:26]
WEBP_TWO = WEBP_ONE[:-1] + b"\x01"


def deck(*slides: str) -> str:
    body = "".join(
        f'<section class="slide" data-title="S{index}">'
        f'<div class="slide-media">{markup}</div>'
        f'<div class="slide-content"></div></section>'
        for index, markup in enumerate(slides, 1)
    )
    return f'<!doctype html><html lang="ko"><body>{body}</body></html>'


class ValidateImageReuseTests(unittest.TestCase):
    def validate(self, html: str, assets: dict[str, bytes] | None = None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "deck.html"
            path.write_text(html, encoding="utf-8")
            for name, payload in (assets or {}).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            return subprocess.run(
                ["python3", str(VALIDATOR), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_distinct_images_pass(self) -> None:
        result = self.validate(
            deck('<img src="a.webp" alt="a">', '<img src="b.webp" alt="b">'),
            {"a.webp": WEBP_ONE, "b.webp": WEBP_TWO},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_file_on_two_slides_is_blocking(self) -> None:
        result = self.validate(
            deck('<img src="a.webp" alt="a">', '<img src="a.webp" alt="a">'),
            {"a.webp": WEBP_ONE},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("reused on slides 1, 2", result.stdout)

    def test_identical_bytes_under_two_names_is_blocking(self) -> None:
        """Renaming a duplicate asset must not launder a near-duplicate slide."""
        result = self.validate(
            deck('<img src="a.webp" alt="a">', '<img src="copy.webp" alt="a">'),
            {"a.webp": WEBP_ONE, "copy.webp": WEBP_ONE},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("reused on slides 1, 2", result.stdout)

    def test_percent_encoded_reference_matches_the_plain_one(self) -> None:
        result = self.validate(
            deck('<img src="my image.webp" alt="a">', '<img src="my%20image.webp" alt="a">'),
            {"my image.webp": WEBP_ONE},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("reused on slides 1, 2", result.stdout)

    def test_approved_thumbnail_hero_pair_passes(self) -> None:
        result = self.validate(
            deck(
                '<img src="a.webp" alt="a" data-image-role="hero" data-repeat-ok="callback-1">',
                '<img src="a.webp" alt="a" data-image-role="thumbnail" data-repeat-ok="callback-1">',
            ),
            {"a.webp": WEBP_ONE},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repeat_token_cannot_approve_three_slides(self) -> None:
        result = self.validate(
            deck(
                '<img src="a.webp" alt="a" data-image-role="hero" data-repeat-ok="c1">',
                '<img src="a.webp" alt="a" data-image-role="thumbnail" data-repeat-ok="c1">',
                '<img src="a.webp" alt="a" data-image-role="thumbnail" data-repeat-ok="c1">',
            ),
            {"a.webp": WEBP_ONE},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("reused on slides 1, 2, 3", result.stdout)

    def test_raster_in_global_css_is_blocking(self) -> None:
        html = deck('<img src="a.webp" alt="a">').replace(
            "<body>", '<style>.bg{background-image:url("a.webp")}</style><body>', 1
        )
        result = self.validate(html, {"a.webp": WEBP_ONE})
        self.assertEqual(result.returncode, 1)
        self.assertIn("not global CSS url()", result.stdout)

    def test_reuse_after_a_nested_section_is_still_detected(self) -> None:
        """A non-greedy </section> regex used to truncate the slide body here."""
        html = deck(
            '<section class="figure-group"><figcaption>inner</figcaption></section>'
            '<img src="a.webp" alt="a">',
            '<img src="a.webp" alt="a">',
        )
        result = self.validate(html, {"a.webp": WEBP_ONE})
        self.assertEqual(result.returncode, 1)
        self.assertIn("reused on slides 1, 2", result.stdout)

    def test_commented_out_image_is_not_counted_as_reuse(self) -> None:
        html = deck(
            '<img src="a.webp" alt="a">',
            '<!-- <img src="a.webp" alt="a"> --><img src="b.webp" alt="b">',
        )
        result = self.validate(html, {"a.webp": WEBP_ONE, "b.webp": WEBP_TWO})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deck_without_slides_is_reported(self) -> None:
        result = self.validate('<!doctype html><html lang="ko"><body></body></html>')
        self.assertEqual(result.returncode, 1)
        self.assertIn("no slides found", result.stdout)


if __name__ == "__main__":
    unittest.main()
