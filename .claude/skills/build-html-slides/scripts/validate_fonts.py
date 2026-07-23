#!/usr/bin/env python3
"""Require portable, local WOFF2 fonts for a text-bearing presentation."""

from __future__ import annotations

import argparse
import base64
import re
from pathlib import Path
from urllib.parse import unquote, urlparse


GENERIC_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "emoji", "math", "fangsong",
}


def normalize_family(value: str) -> str:
    return value.strip().strip("\"'").lower()


def first_family(value: str) -> str:
    match = re.match(r"\s*(?:([\"'])(.*?)\1|([^,]+))", value)
    if not match:
        return ""
    return normalize_family(match.group(2) or match.group(3) or "")


def property_value(block: str, name: str) -> str:
    match = re.search(rf"(?:^|;)\s*{re.escape(name)}\s*:\s*([^;]+)", block, re.I)
    return match.group(1).strip() if match else ""


def visible_slide_text(html: str) -> str:
    sections = re.findall(
        r"<section\b(?=[^>]*\bclass\s*=\s*[\"'][^\"']*\bslide\b[^\"']*[\"'])[^>]*>([\s\S]*?)</section>",
        html,
        re.I,
    )
    body = " ".join(sections)
    body = re.sub(r"<!--[\s\S]*?-->", " ", body)
    body = re.sub(r"<(?:script|style)\b[^>]*>[\s\S]*?</(?:script|style)>", " ", body, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def decode_data_woff2(url: str) -> bytes | None:
    match = re.fullmatch(r"data:font/woff2(?:;[^,]*)?;base64,(.+)", url, re.I | re.S)
    if not match:
        return None
    try:
        return base64.b64decode(match.group(1), validate=True)
    except ValueError:
        return None


def validate(deck: Path) -> list[str]:
    html = deck.read_text(encoding="utf-8")
    if not visible_slide_text(html):
        return []

    styles = "\n".join(re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", html, re.I))
    face_blocks = re.findall(r"@font-face\s*{([^}]*)}", styles, re.I)
    faces: dict[str, list[str]] = {}
    errors: list[str] = []

    for block in face_blocks:
        family = normalize_family(property_value(block, "font-family"))
        source = property_value(block, "src")
        urls = [
            value.strip().strip("\"'")
            for value in re.findall(r"url\(\s*([^)]+?)\s*\)", source, re.I)
        ]
        if not family:
            errors.append("@font-face is missing font-family")
            continue
        if not urls:
            errors.append(f'font-family "{family}" must include a local .woff2 URL; local() alone is not portable')
            continue
        valid_sources: list[str] = []
        for url in urls:
            embedded = decode_data_woff2(url)
            if embedded is not None:
                if not embedded.startswith(b"wOF2"):
                    errors.append(f'font-family "{family}" has an invalid embedded WOFF2 payload')
                else:
                    valid_sources.append("embedded:woff2")
                continue
            parsed = urlparse(url)
            if parsed.scheme and parsed.scheme != "file":
                errors.append(f'font-family "{family}" must use a local .woff2 asset, not {parsed.scheme}://')
                continue
            raw_path = unquote(parsed.path if parsed.scheme == "file" else url.split("?", 1)[0].split("#", 1)[0])
            font_path = Path(raw_path) if parsed.scheme == "file" else (deck.parent / raw_path)
            font_path = font_path.resolve()
            if font_path.suffix.lower() != ".woff2":
                errors.append(f'font-family "{family}" source must be .woff2: {url}')
                continue
            if not font_path.is_relative_to(deck.parent.resolve()):
                errors.append(f'font-family "{family}" source escapes the portable deck folder: {url}')
                continue
            if not font_path.is_file():
                errors.append(f'font-family "{family}" WOFF2 file is missing: {url}')
                continue
            if not font_path.read_bytes().startswith(b"wOF2"):
                errors.append(f'font-family "{family}" source is not a valid WOFF2 file: {url}')
                continue
            valid_sources.append(font_path.relative_to(deck.parent.resolve()).as_posix())
        if valid_sources:
            faces.setdefault(family, []).extend(valid_sources)

    if not faces:
        errors.append("text-bearing Full Validation requires at least one bundled WOFF2 @font-face")
        return errors

    variables = {
        name.lower(): values[-1]
        for name, values in (
            (name, re.findall(rf"--font-{name}\s*:\s*([^;}}]+)", styles, re.I))
            for name in ("display", "body", "mono")
        )
        if values
    }
    required = {"body"}
    if re.search(r"<(?:h1|h2|h3|h4|h5|h6)\b", html, re.I):
        required.add("display")
    if re.search(r"<(?:code|pre)\b", html, re.I):
        required.add("mono")
    for role in sorted(required):
        family = first_family(variables.get(role, ""))
        if not family:
            errors.append(f"--font-{role} must name a bundled WOFF2 family")
        elif family in GENERIC_FAMILIES or family not in faces:
            errors.append(f'--font-{role} primary family "{family}" is not backed by a bundled WOFF2 @font-face')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", type=Path)
    args = parser.parse_args()
    deck = args.deck.resolve()
    if not deck.is_file():
        parser.error(f"deck not found: {deck}")
    errors = validate(deck)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    html = deck.read_text(encoding="utf-8")
    count = len(re.findall(r"@font-face\s*{", html, re.I))
    print(f"OK: {deck} - {count} bundled WOFF2 font face(s) cover the declared theme roles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
