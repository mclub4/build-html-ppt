#!/usr/bin/env python3
"""Structural and offline-bundle validation for an HTML slide deck."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED = {
    "HTML doctype": r"<!doctype\s+html",
    "viewport meta": r"<meta[^>]+name=[\"']viewport[\"']",
    "slide sections": r"<section[^>]+class=[\"'][^\"']*\bslide\b",
    "active slide": r"<section[^>]+class=[\"'][^\"']*\bslide\b[^\"']*\bactive\b|<section[^>]+class=[\"'][^\"']*\bactive\b[^\"']*\bslide\b",
    "keyboard handler": r"addEventListener\s*\(\s*[\"']keydown[\"']",
    "left arrow": r"ArrowLeft",
    "right arrow": r"ArrowRight",
    "visual viewport responsive fit": r"visualViewport",
    "reduced motion": r"prefers-reduced-motion",
    "progress element": r"id=[\"']progress[\"']",
    "editable page input": r"<input[^>]+id=[\"']pageInput[\"'][^>]+type=[\"']number[\"']|<input[^>]+type=[\"']number[\"'][^>]+id=[\"']pageInput[\"']",
}


class LayerParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "image", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, set[str]]] = []
        self.slides: list[dict] = []
        self.current: dict | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())
        if tag == "section" and "slide" in classes:
            self.current = {"depth": len(self.stack), "media": 0, "content": 0, "media_depth": None, "bad_images": []}
            self.slides.append(self.current)
        elif self.current is not None:
            child_depth = len(self.stack)
            if child_depth == self.current["depth"] + 1:
                if "slide-media" in classes:
                    self.current["media"] += 1
                    self.current["media_depth"] = child_depth
                if "slide-content" in classes:
                    self.current["content"] += 1
            if tag in {"img", "picture", "image"}:
                inside_media = any("slide-media" in ancestor_classes for _, ancestor_classes in self.stack)
                inside_content = any("slide-content" in ancestor_classes for _, ancestor_classes in self.stack)
                foreground_classes = {
                    "key-visual",
                    "safe-media",
                    "logo",
                    "title-art",
                    "diagram",
                    "ui-screenshot",
                }
                allowed_foreground = bool(classes & foreground_classes) or any(
                    ancestor_classes & foreground_classes for _, ancestor_classes in self.stack
                )
                if not inside_media and not (inside_content and allowed_foreground):
                    self.current["bad_images"].append(tag)
        if tag not in self.VOID_TAGS:
            self.stack.append((tag, classes))

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for position in range(len(self.stack) - 1, -1, -1):
            if self.stack[position][0] == tag:
                del self.stack[position:]
                break
        if tag == "section" and self.current is not None and len(self.stack) == self.current["depth"]:
            self.current = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", type=Path)
    args = parser.parse_args()
    if not args.deck.is_file():
        print(f"ERROR: file not found: {args.deck}")
        return 2

    try:
        text = args.deck.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"ERROR: deck is not valid UTF-8: {exc}")
        return 1
    errors = [name for name, pattern in REQUIRED.items() if not re.search(pattern, text, re.I | re.S)]
    scale_divisor = r"(?:\d+(?:\.\d+)?|[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)"
    legacy_scale = re.search(
        rf"Math\.min\(\s*(?:window\.)?innerWidth\s*/\s*{scale_divisor}\s*,\s*(?:window\.)?innerHeight\s*/\s*{scale_divisor}\s*\)",
        text,
        re.I,
    )
    direct_inner_ratio = re.search(
        rf"=\s*(?:window\.)?inner(?:Width|Height)\s*/\s*{scale_divisor}",
        text,
        re.I,
    )
    if legacy_scale or direct_inner_ratio:
        errors.append("fixed-stage scale must use visualViewport with documentElement fallback, not a direct innerWidth/innerHeight ratio")
    if re.search(r"\.(?:key-visual|logo|title-art|safe-media)[^{]*{[^}]*object-fit\s*:\s*cover", text, re.I | re.S):
        errors.append("key visual, logo, title art, and safe media must not use object-fit: cover")
    if re.search(r"<(?:img|image)\b[^>]*class=[\"'][^\"']*(?:key-visual|logo|title-art|safe-media)[^\"']*[\"'][^>]*style=[\"'][^\"']*object-fit\s*:\s*cover", text, re.I | re.S):
        errors.append("meaningful foreground media must not use inline object-fit: cover")
    slides = len(re.findall(r"<section[^>]+class=[\"'][^\"']*\bslide\b", text, re.I))
    titles = len(re.findall(r"<section[^>]+data-title=[\"'][^\"']+[\"']", text, re.I))

    if slides < 2:
        errors.append("at least two slides")
    if titles != slides:
        errors.append(f"data-title on every slide ({titles}/{slides})")
    layer_parser = LayerParser()
    layer_parser.feed(text)
    if len(layer_parser.slides) != slides:
        errors.append(f"HTML parser slide count mismatch ({len(layer_parser.slides)}/{slides})")
    for index, record in enumerate(layer_parser.slides, 1):
        if record["media"] != 1 or record["content"] != 1:
            errors.append(f"slide {index} requires exactly one direct slide-media and slide-content ({record['media']}/{record['content']})")
        if record["bad_images"]:
            errors.append(f"slide {index} has raster/image elements outside slide-media: {', '.join(record['bad_images'])}")
    if "\ufffd" in text or re.search(r"(?:\?쒖|\?먮|吏|寃쎄)", text):
        errors.append("likely mojibake or replacement characters")

    bundle_root = args.deck.parent.resolve()

    raster_extensions = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp", ".avif", ".apng"}

    def check_image_format(src: str, kind: str) -> None:
        lowered = src.lower()
        if lowered.startswith("data:image/"):
            if not (lowered.startswith("data:image/webp") or lowered.startswith("data:image/svg+xml")):
                errors.append(f"raster image must be WebP ({kind}): embedded {src.split(';', 1)[0]}")
            return
        if re.match(r"(?:blob:|#|https?://)", src, re.I):
            return
        suffix = Path(unquote(urlsplit(src).path)).suffix.lower()
        if suffix in raster_extensions:
            errors.append(f"raster image must be WebP ({kind}): {src}")
        elif suffix and suffix not in {".webp", ".svg"}:
            errors.append(f"unsupported slide image format; use WebP or SVG ({kind}): {src}")
        elif not suffix:
            errors.append(f"slide image must have a .webp or .svg extension ({kind}): {src}")

    def check_resource(src: str, kind: str) -> None:
        if re.match(r"(?:data:|blob:|#)", src, re.I):
            return
        if re.match(r"https?://", src, re.I):
            errors.append(f"remote runtime dependency is not offline-portable ({kind}): {src}")
            return
        local_path = (args.deck.parent / src.split("#", 1)[0].split("?", 1)[0]).resolve()
        if not local_path.is_relative_to(bundle_root):
            errors.append(f"resource escapes deck bundle ({kind}): {src}")
        elif not local_path.is_file():
            errors.append(f"missing local resource ({kind}): {src}")

    for tag in re.findall(r"<img\b[^>]*>", text, re.I):
        if not re.search(r"\balt\s*=\s*[\"'][^\"']*[\"']", tag, re.I):
            print(f"WARNING: image is missing alt text: {tag[:120]}")
        match = re.search(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        if not match:
            errors.append("image without src")
            continue
        src = match.group(1)
        check_resource(src, "img src")
        check_image_format(src, "img src")

        reference = re.search(r"\bdata-identity-reference\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        if reference:
            value = reference.group(1)
            check_resource(value, "data-identity-reference")
            parsed = urlsplit(value)
            suffix = Path(unquote(parsed.path)).suffix.lower()
            if parsed.scheme or parsed.netloc or suffix != ".webp":
                errors.append(f"identity reference must be a local WebP: {value}")

    for tag_name, attribute in (("source", "src"), ("video", "poster"), ("script", "src"), ("image", "href")):
        for tag in re.findall(rf"<{tag_name}\b[^>]*>", text, re.I):
            match = re.search(rf"\b{attribute}\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
            if match:
                value = match.group(1)
                check_resource(value, f"{tag_name} {attribute}")
                if tag_name in {"video", "image"} or (tag_name == "source" and Path(unquote(urlsplit(value).path)).suffix.lower() in raster_extensions | {".webp", ".svg"}):
                    check_image_format(value, f"{tag_name} {attribute}")
    for tag in re.findall(r"<(?:img|source)\b[^>]*>", text, re.I):
        match = re.search(r"\bsrcset\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        if match:
            for candidate in match.group(1).split(","):
                value = candidate.strip().split()[0]
                if value:
                    check_resource(value, "srcset")
                    check_image_format(value, "srcset")
    for tag in re.findall(r"<link\b[^>]*>", text, re.I):
        rel = re.search(r"\brel\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        href = re.search(r"\bhref\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
        if rel and href and any(token in rel.group(1).lower().split() for token in ("stylesheet", "preload", "icon")):
            value = href.group(1)
            check_resource(value, f"link rel={rel.group(1)}")
            if "icon" in rel.group(1).lower().split():
                check_image_format(value, f"link rel={rel.group(1)}")
    styles = "\n".join(re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", text, re.I))
    for match in re.finditer(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^\)"\']+))\s*\)', styles, re.I):
        value = next(group for group in match.groups() if group is not None).strip()
        if value and not value.startswith("#") and not value.lower().startswith("%23"):
            check_resource(value, "CSS url()")
            suffix = Path(unquote(urlsplit(value).path)).suffix.lower()
            if value.lower().startswith("data:image/") or suffix in raster_extensions | {".webp", ".svg"}:
                check_image_format(value, "CSS url()")
            is_raster_data = value.lower().startswith("data:image/") and not value.lower().startswith("data:image/svg+xml")
            if is_raster_data or suffix in raster_extensions | {".webp"}:
                errors.append(f"raster image must be an element inside .slide-media, not CSS url(): {value[:140]}")
    if re.search(r"https?://", text, re.I):
        print("WARNING: external URL text found; citations are allowed, runtime dependencies are errors.")
    if re.search(r"<section[^>]*>\s*</section>", text, re.I | re.S):
        print("WARNING: empty slide found.")

    if errors:
        for item in errors:
            print(f"ERROR: missing or invalid: {item}")
        return 1
    print(f"OK: {args.deck} - {slides} slides, navigation/runtime markers present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
