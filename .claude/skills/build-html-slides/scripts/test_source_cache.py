#!/usr/bin/env python3
"""Tests for hash-bound slide image source caching."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).with_name("source_cache.py")


class SourceCacheTests(unittest.TestCase):
    def run_cache(self, deck: Path, cache: Path, action: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), str(deck), str(cache), action],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_update_reuses_unchanged_asset_and_invalidates_changed_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            asset = asset_dir / "hero.webp"
            asset.write_bytes(b"webp-v1")
            deck = root / "deck.html"
            deck.write_text('<section class="slide"><img src="assets/hero.webp" alt="Hero"></section>', encoding="utf-8")
            cache = root / "sources.json"

            first = self.run_cache(deck, cache, "--update")
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            data = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], 2)
            entry = data["assets"][0]
            self.assertEqual(entry["roles"], ["media-purpose:unspecified", "slide-image"])
            entry.update({
                "source_kind": "official",
                "source_url": "https://example.com/hero",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "credit": "Example",
                "status": "verified",
            })
            cache.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")
            check = self.run_cache(deck, cache, "--check")
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

            deck.write_text(deck.read_text(encoding="utf-8") + "<!-- copy edit -->", encoding="utf-8")
            unchanged = self.run_cache(deck, cache, "--update")
            self.assertEqual(unchanged.returncode, 0, unchanged.stdout + unchanged.stderr)
            self.assertIn("reused 1", unchanged.stdout)
            preserved = json.loads(cache.read_text(encoding="utf-8"))["assets"][0]
            self.assertEqual(preserved["status"], "verified")

            asset.write_bytes(b"webp-v2")
            changed = self.run_cache(deck, cache, "--update")
            self.assertEqual(changed.returncode, 0, changed.stdout + changed.stderr)
            invalidated = json.loads(cache.read_text(encoding="utf-8"))["assets"][0]
            self.assertEqual(invalidated["status"], "needs-review")
            self.assertEqual(invalidated["verified_at"], "")

    def test_internal_fan_art_accepts_discovery_url_and_visible_credit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset_dir = root / "assets"
            asset_dir.mkdir()
            asset = asset_dir / "fan-art.webp"
            asset.write_bytes(b"fan-art-webp")
            deck = root / "deck.html"
            deck.write_text('<section class="slide"><img src="assets/fan-art.webp" alt="Fan art"></section>', encoding="utf-8")
            cache = root / "sources.json"
            self.assertEqual(self.run_cache(deck, cache, "--update").returncode, 0)
            data = json.loads(cache.read_text(encoding="utf-8"))
            data["assets"][0].update({
                "source_kind": "fan-art",
                "source_url": "https://example.com/discovery-post",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "credit": "@visible-creator",
                "origin_status": "discovery-only",
                "status": "verified",
            })
            cache.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")
            result = self.run_cache(deck, cache, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_identity_reference_is_cached_and_must_be_authoritative_webp(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets = root / "assets"
            assets.mkdir()
            (assets / "candidate.webp").write_bytes(b"candidate-webp")
            (assets / "official.webp").write_bytes(b"official-reference-webp")
            deck = root / "deck.html"
            deck.write_text(
                '<section class="slide"><img src="assets/candidate.webp" alt="Character" '
                'data-subject-id="series:character" data-identity-reference="assets/official.webp"></section>',
                encoding="utf-8",
            )
            cache = root / "sources.json"
            self.assertEqual(self.run_cache(deck, cache, "--update").returncode, 0)
            data = json.loads(cache.read_text(encoding="utf-8"))
            by_path = {entry["path"]: entry for entry in data["assets"]}
            self.assertEqual(by_path["assets/official.webp"]["roles"], ["identity-reference"])
            self.assertEqual(
                by_path["assets/candidate.webp"]["roles"],
                ["identity-candidate", "media-purpose:unspecified", "slide-image"],
            )
            for entry in data["assets"]:
                entry.update({
                    "source_kind": "official",
                    "source_url": f"https://example.com/{Path(entry['path']).stem}",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "credit": "Example",
                    "status": "verified",
                })
            cache.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")
            result = self.run_cache(deck, cache, "--check")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            (assets / "official.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            deck.write_text(
                deck.read_text(encoding="utf-8").replace("official.webp", "official.svg"),
                encoding="utf-8",
            )
            self.assertEqual(self.run_cache(deck, cache, "--update").returncode, 0)
            migrated = json.loads(cache.read_text(encoding="utf-8"))
            for entry in migrated["assets"]:
                entry.update({
                    "source_kind": "official",
                    "source_url": "https://example.com/reference",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "credit": "Example",
                    "status": "verified",
                })
            cache.write_text(f"{json.dumps(migrated, indent=2)}\n", encoding="utf-8")
            result = self.run_cache(deck, cache, "--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("identity reference must be a local WebP", result.stdout)

    def test_generated_asset_accepts_only_non_factual_declared_purpose(self) -> None:
        cases = (
            (
                "atmosphere",
                '<img src="assets/generated.webp" data-media-purpose="atmosphere" alt="Atmosphere">',
                0,
                "",
            ),
            (
                "missing-purpose",
                '<img src="assets/generated.webp" alt="Generated">',
                1,
                "generated asset requires data-media-purpose",
            ),
            (
                "factual-subject",
                '<img src="assets/generated.webp" data-media-purpose="subject" alt="Named subject">',
                1,
                "generated asset cannot fill factual media purpose (subject)",
            ),
            (
                "identity-candidate",
                '<img src="assets/generated.webp" data-media-purpose="atmosphere" '
                'data-subject-id="group:member" alt="Member">',
                1,
                "generated asset cannot be an identity candidate",
            ),
        )
        for name, image_markup, expected_code, expected_message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                assets = root / "assets"
                assets.mkdir()
                (assets / "generated.webp").write_bytes(b"generated-webp")
                deck = root / "deck.html"
                deck.write_text(
                    f'<section class="slide">{image_markup}</section>',
                    encoding="utf-8",
                )
                cache = root / "sources.json"
                self.assertEqual(self.run_cache(deck, cache, "--update").returncode, 0)
                data = json.loads(cache.read_text(encoding="utf-8"))
                data["assets"][0].update({
                    "source_kind": "generated",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "credit": "Image generator",
                    "status": "verified",
                })
                cache.write_text(f"{json.dumps(data, indent=2)}\n", encoding="utf-8")
                result = self.run_cache(deck, cache, "--check")
                self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
                if expected_message:
                    self.assertIn(expected_message, result.stdout)


if __name__ == "__main__":
    unittest.main()
