#!/usr/bin/env python3
"""Structural and offline-bundle validation for an HTML slide deck."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import deck_html


# A run of Hangul/CJK long enough that a text-encoding round trip is meaningful.
CJK_RUN = re.compile("[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3\u4e00-\u9fff\uf900-\ufaff]{2,}")
# C1 controls never appear in legitimate deck copy; they are decode debris.
C1_CONTROLS = re.compile("[\u0080-\u009f]")


def repairable_mojibake(text: str) -> tuple[str, str] | None:
    """Return (broken, repaired) when a run is provably a UTF-8 -> CP949 misdecode.

    A hardcoded blocklist of garbled syllables both misses most real mojibake and
    rejects legitimate hanja such as 吏. Re-encoding a run to CP949/EUC-KR and
    decoding the bytes as UTF-8 is a decision, not a guess: if the bytes decode
    to different Hangul, the run really is mojibake and the repaired text can be
    printed for the author.
    """
    for run in CJK_RUN.findall(text):
        for encoding in ("cp949", "euc-kr"):
            try:
                raw = run.encode(encoding)
            except UnicodeEncodeError:
                continue
            try:
                repaired = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if repaired != run and re.search(r"[가-힣]", repaired):
                return run, repaired
    return None


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
    # data-title must be counted on slide sections only. Counting it across any
    # <section> let a titleless slide pass whenever an unrelated section carried
    # one, which silently broke validate_speaker_notes.py and render_slides.js.
    slide_titles = deck_html.slide_titles(text)
    titles = sum(1 for title in slide_titles if title)

    if slides < 2:
        errors.append("at least two slides")
    if titles != len(slide_titles):
        errors.append(f"data-title on every slide ({titles}/{len(slide_titles)})")
    layer_parser = LayerParser()
    layer_parser.feed(text)
    if len(layer_parser.slides) != slides:
        errors.append(f"HTML parser slide count mismatch ({len(layer_parser.slides)}/{slides})")
    for index, record in enumerate(layer_parser.slides, 1):
        if record["media"] != 1 or record["content"] != 1:
            errors.append(f"slide {index} requires exactly one direct slide-media and slide-content ({record['media']}/{record['content']})")
        if record["bad_images"]:
            errors.append(f"slide {index} has raster/image elements outside slide-media: {', '.join(record['bad_images'])}")
    mojibake = repairable_mojibake(text)
    if "\ufffd" in text or C1_CONTROLS.search(text):
        errors.append("likely mojibake or replacement characters")
    elif mojibake:
        errors.append(
            "likely mojibake or replacement characters: "
            f"{mojibake[0]!r} decodes back to {mojibake[1]!r}"
        )

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
        # A reference is a URL, so it must be percent-decoded before it is used as a
        # filesystem path. Without this, the correct pair ("my image.webp" on disk,
        # "my%20image.webp" in the markup) was reported as a missing resource and no
        # deck with a space or non-ASCII asset name could pass.
        relative = unquote(urlsplit(src).path)
        if not relative:
            return
        local_path = (args.deck.parent / relative).resolve()
        if not local_path.is_relative_to(bundle_root):
            errors.append(f"resource escapes deck bundle ({kind}): {src}")
        elif not local_path.is_file():
            errors.append(f"missing local resource ({kind}): {src}")

    for tag in re.findall(r"<img\b[^>]*>", text, re.I):
        if not re.search(r"\balt\s*=\s*[\"'][^\"']*[\"']", tag, re.I):
            errors.append(f"image is missing alt attribute: {tag[:120]}")
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
    for variable in ("--font-display", "--font-body"):
        if not re.search(rf"{re.escape(variable)}\s*:\s*[^;}}]+", styles, re.I):
            errors.append(f"typography must declare {variable} for the selected theme")
    generic_families = {
        "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif",
        "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "fangsong", "inherit", "initial",
    }
    font_values = re.findall(
        r"(?:font-family|--font-(?:display|body))\s*:\s*([^;}}]+)", styles, re.I
    )
    named_families = []
    for value in font_values:
        for family in value.split(","):
            normalized = family.strip().strip("\"'").lower()
            if normalized and normalized not in generic_families and not normalized.startswith("var("):
                named_families.append(normalized)
    if not named_families:
        errors.append("typography needs a deliberate named display/body font stack, not generic system families only")
    if re.search(
        r"body\s*\{[^}]*font-family\s*:\s*(?:system-ui\s*,\s*)?(?:sans-serif|system-ui)\s*;",
        styles,
        re.I | re.S,
    ):
        errors.append("body typography must not remain a bare system-ui/sans-serif shell default")
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
    for class_value in re.findall(r"\bclass\s*=\s*[\"']([^\"']+)[\"']", text, re.I):
        classes = class_value.split()
        if "source" in classes and len(classes) > 1:
            errors.append(
                "reserved citation class .source must not be combined with component classes; "
                "use data-source-citation or a namespaced class such as .event-stream--source"
            )

    if errors:
        for item in errors:
            print(f"ERROR: missing or invalid: {item}")
        return 1
    print(f"OK: {args.deck} - {slides} slides, navigation/runtime markers present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
