#!/usr/bin/env python3
"""Regression tests for the Korean-market source locality gate.

This validator ran in the deterministic command set with zero test coverage and
classified links with a trailing-slash regex, so a bare `https://host.co.kr`
citation counted as no local source at all.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_source_locality.py"


def deck(links: str, lang: str = "ko") -> str:
    return (
        f"<!doctype html><html lang=\"{lang}\"><head><meta charset=\"utf-8\"></head><body>"
        f"<section class=\"slide\" data-title=\"S1\"><div class=\"slide-media\"></div>"
        f"<div class=\"slide-content\">{links}</div></section></body></html>"
    )


class ValidateSourceLocalityTests(unittest.TestCase):
    def validate(self, html: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "deck.html"
            path.write_text(html, encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_kr_domain_without_trailing_slash_counts_as_local(self) -> None:
        result = self.validate(deck('<a href="https://www.hankyung.co.kr">출처</a>'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_kr_domain_with_path_but_no_trailing_slash_counts_as_local(self) -> None:
        result = self.validate(
            deck('<a href="https://news.example.kr/article/12345">출처</a>')
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_kr_domain_with_trailing_slash_still_counts_as_local(self) -> None:
        result = self.validate(deck('<a href="https://www.hankyung.co.kr/">출처</a>'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ko_path_segment_without_trailing_slash_counts_as_local(self) -> None:
        result = self.validate(deck('<a href="https://example.com/ko">출처</a>'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_korean_deck_without_any_local_source_fails(self) -> None:
        result = self.validate(deck('<a href="https://example.com/docs">source</a>'))
        self.assertEqual(result.returncode, 1)
        self.assertIn("no target-region source links", result.stdout)

    def test_foreign_region_link_needs_the_explicit_exemption(self) -> None:
        result = self.validate(
            deck(
                '<a href="https://example.co.kr/notice">국내</a>'
                '<a href="https://example.com/en-us/pricing">global</a>'
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("foreign-secondary", result.stdout)

    def test_foreign_region_link_with_exemption_passes(self) -> None:
        result = self.validate(
            deck(
                '<a href="https://example.co.kr/notice">국내</a>'
                '<a href="https://example.com/en-us/pricing" '
                'data-source-locality="foreign-secondary">global</a>'
            )
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_trailing_foreign_segment_is_detected(self) -> None:
        result = self.validate(
            deck(
                '<a href="https://example.co.kr/notice">국내</a>'
                '<a href="https://example.com/store/us">global</a>'
            )
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("foreign-secondary", result.stdout)

    def test_non_korean_deck_is_skipped(self) -> None:
        result = self.validate(deck('<a href="https://example.com/us/">us</a>', lang="en"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not applicable", result.stdout)

    def test_commented_out_link_is_not_counted_as_a_local_source(self) -> None:
        result = self.validate(
            deck('<!-- <a href="https://example.co.kr/notice">국내</a> -->'
                 '<a href="https://example.com/docs">source</a>')
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no target-region source links", result.stdout)


if __name__ == "__main__":
    unittest.main()
