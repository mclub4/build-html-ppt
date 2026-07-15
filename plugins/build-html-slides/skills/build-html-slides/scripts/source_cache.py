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
FAN_ART_ORIGIN_STATUSES = {"origin-verified", "discovery-only"}
IDENTITY_REFERENCE_KINDS = {"official", "licensed", "supplied"}


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.uses: dict[str, set[str]] = {}

    def record(self, url: str, role: str) -> None:
        if url:
            self.uses.setdefault(url, set()).add(role)

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "img" and values.get("src"):
            self.record(values["src"], "slide-image")
        elif tag == "source" and values.get("srcset"):
            for candidate in values["srcset"].split(","):
                url = candidate.strip().split()[0] if candidate.strip() else ""
                self.record(url, "slide-image")
        elif tag == "image":
            url = values.get("href") or values.get("xlink:href")
            self.record(url or "", "slide-image")
        self.record(values.get("data-identity-reference", ""), "identity-reference")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_assets(deck: Path) -> dict[str, tuple[Path, tuple[str, ...]]]:
    parser = ImageParser()
    parser.feed(deck.read_text(encoding="utf-8"))
    assets: dict[str, tuple[Path, tuple[str, ...]]] = {}
    for raw_url, roles in parser.uses.items():
        parsed = urlparse(raw_url)
        if parsed.scheme in {"http", "https", "data"} or parsed.netloc:
            continue
        relative = unquote(parsed.path)
        suffix = Path(relative).suffix.lower()
        if not relative or (suffix not in RASTER_SUFFIXES and "identity-reference" not in roles):
            continue
        resolved = (deck.parent / relative).resolve()
        key = resolved.relative_to(deck.parent.resolve()).as_posix()
        assets[key] = (resolved, tuple(sorted(roles)))
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
    for relative, (asset, roles) in local_assets(deck).items():
        digest = sha256(asset) if asset.is_file() else ""
        previous = existing_entries.get(relative, {})
        if previous.get("sha256") == digest and digest:
            reused_entry = dict(previous)
            reused_entry["roles"] = list(roles)
            entries.append(reused_entry)
            reused += 1
            continue
        entries.append({
            "path": relative,
            "sha256": digest,
            "roles": list(roles),
            "source_kind": previous.get("source_kind", ""),
            "source_url": previous.get("source_url", ""),
            "verified_at": "",
            "credit": previous.get("credit", ""),
            "origin_status": previous.get("origin_status", ""),
            "status": "needs-review",
        })
        changed += 1
    cache = {
        "schema_version": 2,
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
    if cache.get("schema_version") != 2:
        errors.append("schema_version must be 2; run --update to migrate the source cache")
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
    for relative, (asset, expected_roles) in expected.items():
        entry = by_path.get(relative)
        if entry is None:
            continue
        if not asset.is_file():
            errors.append(f"asset not found: {relative}")
            continue
        if entry.get("sha256") != sha256(asset):
            errors.append(f"asset hash changed; run --update: {relative}")
        roles = entry.get("roles")
        if roles != list(expected_roles):
            errors.append(f"asset roles changed; run --update: {relative}")
        kind = entry.get("source_kind")
        if kind not in SOURCE_KINDS:
            errors.append(f"asset source_kind is invalid: {relative}")
        source_url = entry.get("source_url")
        if kind in URL_REQUIRED_KINDS and (
            not isinstance(source_url, str) or urlparse(source_url).scheme not in {"http", "https"}
        ):
            errors.append(f"asset requires an http(s) source_url: {relative}")
        if kind == "fan-art":
            origin_status = entry.get("origin_status")
            if origin_status not in FAN_ART_ORIGIN_STATUSES:
                errors.append(f"fan-art origin_status is invalid: {relative}")
            if not isinstance(entry.get("credit"), str) or not entry["credit"].strip():
                errors.append(f"fan-art requires visible creator credit: {relative}")
        if "identity-reference" in expected_roles:
            if asset.suffix.lower() != ".webp":
                errors.append(f"identity reference must be a local WebP: {relative}")
            if kind not in IDENTITY_REFERENCE_KINDS:
                errors.append(
                    f"identity reference source_kind must be official, licensed, or supplied: {relative}"
                )
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
