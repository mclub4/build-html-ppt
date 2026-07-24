#!/usr/bin/env python3
import base64
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import deck_html


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


if len(sys.argv) != 2:
    fail("usage: validate_image_reuse.py DECK.html")

deck_path = Path(sys.argv[1]).resolve()
if not deck_path.is_file():
    fail(f"deck not found: {deck_path}")

html = deck_path.read_text(encoding="utf-8")
# Slide bodies come from the parser: a non-greedy `</section>` regex stops at the
# first nested close tag, which quietly hid every asset after a nested <section>.
index = deck_html.parse(html)
slide_elements = index.slides()
if not slide_elements:
    fail("no slides found")

URL_RE = re.compile(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^\)"\']+))\s*\)', re.I)


def css_urls(text: str):
    for match in URL_RE.finditer(text):
        value = next(group for group in match.groups() if group is not None).strip()
        if not value or value.startswith("#") or value.lower().startswith("%23"):
            continue
        yield value


def fingerprint(asset: str):
    asset = asset.strip()
    if asset.startswith("data:"):
        header, _, payload = asset.partition(",")
        if header.lower().startswith("data:image/svg+xml"):
            return None
        try:
            data = base64.b64decode(payload) if ";base64" in header.lower() else unquote(payload).encode("utf-8")
        except Exception:
            data = asset.encode("utf-8")
        return "sha256:" + hashlib.sha256(data).hexdigest(), "embedded data image"

    parts = urlsplit(asset)
    if parts.scheme in {"http", "https"}:
        normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
        return "url:" + normalized, normalized

    clean = unquote(parts.path).replace("/", str(Path("/")))
    candidate = (deck_path.parent / clean).resolve()
    if candidate.is_file():
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        return "sha256:" + digest, str(candidate.relative_to(deck_path.parent) if candidate.is_relative_to(deck_path.parent) else candidate)
    normalized = str(Path(clean)).casefold()
    return "path:" + normalized, clean


uses = defaultdict(list)
labels = defaultdict(set)


def record(asset: str, slide_number: int, repeat_token: str, role: str, origin: str):
    result = fingerprint(asset)
    if result is None:
        return
    key, label = result
    uses[key].append((slide_number, repeat_token.strip(), role.strip().lower(), origin))
    labels[key].add(label)


for slide_number, slide in enumerate(slide_elements, 1):
    for element in [slide, *index.descendants(slide)]:
        if element.inert:
            continue
        if element.tag in {"img", "source", "image", "video"}:
            repeat_token = element.attr("data-repeat-ok")
            role = element.attr("data-image-role")
            for attribute in ("src", "href", "poster"):
                value = element.attr(attribute).strip()
                if value:
                    record(value, slide_number, repeat_token, role, f"<{attribute}> element")
            for candidate in element.attr("srcset").split(","):
                asset = candidate.strip().split(" ")[0].strip()
                if asset:
                    record(asset, slide_number, repeat_token, role, "srcset")

        for asset in css_urls(element.attr("style")):
            record(asset, slide_number, "", "background", "inline style")

# Raster slide imagery in global CSS is prohibited because ownership, layering, alt text,
# and cross-slide reuse cannot be determined reliably without a full browser CSS engine.
styles = "\n".join(re.findall(r'<style\b[^>]*>([\s\S]*?)</style>', html, re.I))
policy_errors = []
for asset in css_urls(styles):
    lowered = urlsplit(asset).path.lower()
    if asset.lower().startswith("data:image/svg+xml"):
        continue
    if asset.lower().startswith("data:image/") or re.search(r'\.(?:png|jpe?g|webp|avif|gif|bmp|tiff?)$', lowered):
        policy_errors.append(f"raster image must be an element inside .slide-media, not global CSS url(): {asset[:140]}")

errors = []
for key, occurrences in uses.items():
    unique_slides = sorted({slide for slide, _, _, _ in occurrences})
    if len(unique_slides) > 1:
        origins = sorted({origin for _, _, _, origin in occurrences})
        tokens = {token for _, token, _, _ in occurrences if token}
        roles = [role for _, _, role, _ in occurrences]
        allowed_pair = (
            len(unique_slides) == 2
            and len(tokens) == 1
            and all(token for _, token, _, _ in occurrences)
            and "thumbnail" in roles
            and any(role in {"hero", "detail"} for role in roles)
            and not any(role == "background" for role in roles)
        )
        if not allowed_pair:
            label = " | ".join(sorted(labels[key]))
            errors.append(f"{label} reused on slides {', '.join(map(str, unique_slides))} with roles {roles} ({'; '.join(origins)})")

if errors or policy_errors:
    for error in policy_errors + errors:
        print(f"ERROR: {error}")
    print("NOTE: script-created/computed imagery and visually similar re-encodes still require the all-slide visual review.")
    raise SystemExit(1)

print(f"OK: {deck_path} - no unapproved cross-slide image reuse")
