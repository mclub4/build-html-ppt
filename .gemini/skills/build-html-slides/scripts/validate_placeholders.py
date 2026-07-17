#!/usr/bin/env python3
"""Reject visible placeholders and incomplete asset markers in a slide deck."""

from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "image", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
SUPPRESSED_TAGS = {"script", "style", "template", "noscript"}
VISIBLE_PATTERNS = (
    ("PLACE NOTE", re.compile(r"\bplace\s*[-_]?\s*note\b", re.I)),
    ("placeholder", re.compile(r"\bplace\s*holder\b|\bplaceholder\b|플레이스\s*홀더", re.I)),
    ("lorem ipsum", re.compile(r"\blorem\s+ipsum\b", re.I)),
    (
        "unfinished media instruction",
        re.compile(
            r"\b(?:image|photo|picture|visual|graphic|asset)\s*"
            r"(?:here|pending|placeholder|to\s+come|todo|tbd)\b"
            r"|\b(?:insert|add|replace)\s+(?:an?\s+)?(?:image|photo|picture|visual|graphic|asset)\b",
            re.I,
        ),
    ),
    (
        "unfinished Korean media instruction",
        re.compile(
            r"(?:이미지|사진|비주얼|그래픽|삽화)\s*(?:자리|삽입|추가|예정|대기|필요)"
            r"|(?:임시|대체)\s*(?:이미지|사진|비주얼|그래픽|삽화)"
            r"|(?:추후|나중에)\s*(?:이미지|사진|비주얼|그래픽|삽화)?\s*(?:삽입|추가|교체)",
            re.I,
        ),
    ),
    ("unfinished task token", re.compile(r"(?:^|\s)(?:TODO|TBD)(?:\s|$)", re.I)),
    (
        "template token",
        re.compile(
            r"\{\{\s*(?:image|photo|picture|visual|graphic|asset|title|subtitle|copy)\b[^}]*\}\}"
            r"|\[\s*(?:image|photo|picture|visual|graphic|asset)\s+(?:here|pending)\s*\]",
            re.I,
        ),
    ),
)
ATTRIBUTE_MARKER = re.compile(
    r"(?:^|[\s_./-])(?:"
    r"placeholder|place[\s_-]?note|"
    r"dummy[\s_-]?(?:image|photo|picture|visual|graphic|asset)|"
    r"(?:image|photo|picture|visual|graphic|asset)[\s_-]?(?:placeholder|pending|todo|tbd)|"
    r"(?:temp|temporary|fallback)[\s_-](?:image|photo|picture|visual|art|graphic|asset)"
    r")(?:$|[\s_./-])",
    re.I,
)
INSPECTED_ATTRIBUTES = {"class", "id", "src", "srcset", "href", "poster", "alt", "aria-label"}
INSPECTED_DATA_ATTRIBUTES = {"data-title", "data-placeholder", "data-asset-state", "data-media-state"}


class PlaceholderParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.slide_count = 0
        self.text_by_slide: dict[int, list[str]] = {}
        self.attribute_findings: list[tuple[int, str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        classes = set(values.get("class", "").split())
        parent = self.stack[-1] if self.stack else {"slide": 0, "suppressed": False, "literal": False}
        slide = int(parent["slide"])
        if tag == "section" and "slide" in classes:
            self.slide_count += 1
            slide = self.slide_count
            self.text_by_slide.setdefault(slide, [])
        suppressed = bool(parent["suppressed"] or tag in SUPPRESSED_TAGS)
        literal = bool(parent["literal"] or values.get("data-placeholder-literal") == "true")
        if slide and not suppressed:
            for name, value in attrs:
                if not value or (name not in INSPECTED_ATTRIBUTES and name not in INSPECTED_DATA_ATTRIBUTES):
                    continue
                if ATTRIBUTE_MARKER.search(value):
                    self.attribute_findings.append((slide, name, value.strip()[:140]))
        if tag not in VOID_TAGS:
            self.stack.append({"tag": tag, "slide": slide, "suppressed": suppressed, "literal": literal})

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if not self.stack:
            return
        frame = self.stack[-1]
        if frame["slide"] and not frame["suppressed"] and not frame["literal"] and data.strip():
            self.text_by_slide[int(frame["slide"])].append(data)


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def generated_css_content(source: str) -> list[str]:
    values: list[str] = []
    for stylesheet in re.findall(r"<style\b[^>]*>([\s\S]*?)</style>", source, re.I):
        stylesheet = re.sub(r"/\*[\s\S]*?\*/", "", stylesheet)
        for match in re.finditer(r"\bcontent\s*:\s*([\"'])(.*?)\1", stylesheet, re.I | re.S):
            values.append(match.group(2))
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", type=Path)
    args = parser.parse_args()
    if not args.deck.is_file():
        print(f"ERROR: file not found: {args.deck}")
        return 2
    try:
        source = args.deck.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"ERROR: deck is not valid UTF-8: {exc}")
        return 1

    document = PlaceholderParser()
    document.feed(source)
    findings: list[str] = []
    for slide, chunks in document.text_by_slide.items():
        visible_text = compact(" ".join(chunks))
        for label, pattern in VISIBLE_PATTERNS:
            match = pattern.search(visible_text)
            if match:
                excerpt = compact(visible_text[max(0, match.start() - 28):match.end() + 28])
                findings.append(f"slide {slide} contains blocked {label} text: {excerpt!r}")
    for slide, attribute, value in document.attribute_findings:
        findings.append(f"slide {slide} contains a placeholder marker in {attribute}: {value!r}")
    for value in generated_css_content(source):
        visible_text = compact(value)
        for label, pattern in VISIBLE_PATTERNS:
            if pattern.search(visible_text):
                findings.append(f"stylesheet generates blocked {label} text: {visible_text[:140]!r}")

    findings = list(dict.fromkeys(findings))
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        print("ERROR: replace every placeholder with finished content or remove/recompose the unfinished visual slot")
        return 1
    print(f"OK: {args.deck} - no visible placeholder or incomplete-asset marker found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
