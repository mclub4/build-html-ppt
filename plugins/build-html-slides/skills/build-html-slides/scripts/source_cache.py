#!/usr/bin/env python3
"""Maintain a hash-bound source cache for local slide imagery."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


RASTER_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".avif"}
SOURCE_KINDS = {"official", "licensed", "fan-art", "generated", "supplied", "other"}
URL_REQUIRED_KINDS = {"official", "licensed", "fan-art", "other"}


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "img" and values.get("src"):
            self.urls.add(values["src"])
        elif tag == "source" and values.get("srcset"):
            for candidate in values["srcset"].split(","):
                url = candidate.strip().split()[0] if candidate.strip() else ""
                if url:
                    self.urls.add(url)
        elif tag == "image":
            url = values.get("href") or values.get("xlink:href")
            if url:
                self.urls.add(url)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_assets(deck: Path) -> dict[str, Path]:
    parser = ImageParser()
    parser.feed(deck.read_text(encoding="utf-8"))
    assets: dict[str, Path] = {}
    for raw_url in parser.urls:
        parsed = urlparse(raw_url)
        if parsed.scheme in {"http", "https", "data"} or parsed.netloc:
            continue
        relative = unquote(parsed.path)
        if not relative or Path(relative).suffix.lower() not in RASTER_SUFFIXES:
            continue
        resolved = (deck.parent / relative).resolve()
        key = resolved.relative_to(deck.parent.resolve()).as_posix()
        assets[key] = resolved
    return dict(sorted(assets.items()))


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid source cache: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("source cache root must be an object")
    return value


def update(deck: Path, cache_path: Path) -> int:
    existing = load_cache(cache_path)
    existing_entries = {
        entry.get("path"): entry
        for entry in existing.get("assets", [])
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    entries = []
    reused = 0
    changed = 0
    for relative, asset in local_assets(deck).items():
        digest = sha256(asset) if asset.is_file() else ""
        previous = existing_entries.get(relative, {})
        if previous.get("sha256") == digest and digest:
            entries.append(previous)
            reused += 1
            continue
        entries.append({
            "path": relative,
            "sha256": digest,
            "source_kind": previous.get("source_kind", ""),
            "source_url": previous.get("source_url", ""),
            "verified_at": "",
            "credit": previous.get("credit", ""),
            "status": "needs-review",
        })
        changed += 1
    cache = {
        "schema_version": 1,
        "deck": deck.name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "assets": entries,
    }
    cache_path.write_text(f"{json.dumps(cache, ensure_ascii=False, indent=2)}\n", encoding="utf-8")
    print(f"OK: {cache_path} - reused {reused}, new/changed {changed}, removed {max(0, len(existing_entries) - len(entries))}")
    return 0


def check(deck: Path, cache_path: Path) -> int:
    errors: list[str] = []
    try:
        cache = load_cache(cache_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    if cache.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if cache.get("deck") != deck.name:
        errors.append(f"deck must be {deck.name}")
    entries = cache.get("assets")
    if not isinstance(entries, list):
        errors.append("assets must be an array")
        entries = []
    by_path: dict[str, dict] = {}
    for position, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append(f"asset {position} needs a path")
            continue
        relative = entry["path"]
        if relative in by_path:
            errors.append(f"duplicate asset path: {relative}")
        by_path[relative] = entry

    expected = local_assets(deck)
    if set(by_path) != set(expected):
        for relative in sorted(set(expected) - set(by_path)):
            errors.append(f"uncached local raster asset: {relative}")
        for relative in sorted(set(by_path) - set(expected)):
            errors.append(f"stale cache entry: {relative}")
    for relative, asset in expected.items():
        entry = by_path.get(relative)
        if entry is None:
            continue
        if not asset.is_file():
            errors.append(f"asset not found: {relative}")
            continue
        if entry.get("sha256") != sha256(asset):
            errors.append(f"asset hash changed; run --update: {relative}")
        kind = entry.get("source_kind")
        if kind not in SOURCE_KINDS:
            errors.append(f"asset source_kind is invalid: {relative}")
        source_url = entry.get("source_url")
        if kind in URL_REQUIRED_KINDS and (
            not isinstance(source_url, str) or urlparse(source_url).scheme not in {"http", "https"}
        ):
            errors.append(f"asset requires an http(s) source_url: {relative}")
        try:
            datetime.fromisoformat(str(entry.get("verified_at", "")).replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"asset verified_at must be an ISO date/time: {relative}")
        if entry.get("status") != "verified":
            errors.append(f"asset source status must be verified: {relative}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {cache_path} - {len(expected)} unchanged local raster asset source record(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("cache", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--update", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    deck = args.deck.resolve()
    cache_path = args.cache.resolve()
    if not deck.is_file():
        print(f"ERROR: deck not found: {deck}")
        return 1
    try:
        return update(deck, cache_path) if args.update else check(deck, cache_path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
