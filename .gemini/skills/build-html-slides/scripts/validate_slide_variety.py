#!/usr/bin/env python3
"""Deck-level gate against near-duplicate slide compositions.

A deck shipped two slides that were the same page twice: identical composition
skeleton, identical referenced image set, identical card and column counts, and
only the background colour differed. Prose told the reviewer to keep the deck
varied; the reviewer rationalised the repeat away. This converts that judgment
into a measurement.

A pair is flagged only when every structural dimension matches at once:

  1. both slides are substantive (>= minimum_structural_elements elements), so
     deliberate deck rhythm - repeated section dividers, chapter cards, quote
     slides - is out of scope by construction;
  2. neither slide declares an exempt slide kind (section/divider/chapter/
     interstitial/transition/quote) via data-slide-kind or a matching class;
  3. the element skeletons (tag + layout-class signature + depth, text removed)
     are at least skeleton_similarity_threshold similar;
  4. card counts and column counts are equal;
  5. the referenced asset sets are equal.

An intentional twin - a before/after pair, a repeated scoreboard - opts out by
carrying the same non-empty ``data-variety-ok`` token on both slides, mirroring
``data-repeat-ok`` in validate_image_reuse.py. The token is reported so the
opt-out stays visible in the log.

This is a deck-level check: it runs once per deck, not once per slide.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit


CONTRACT = json.loads((Path(__file__).with_name("validation_contract.json")).read_text(encoding="utf-8"))
SETTINGS = CONTRACT["slide_variety"]
SIMILARITY_THRESHOLD = float(SETTINGS["skeleton_similarity_threshold"])
MINIMUM_STRUCTURAL_ELEMENTS = int(SETTINGS["minimum_structural_elements"])
EXEMPT_SLIDE_KINDS = frozenset(SETTINGS["exempt_slide_kinds"])
OPT_OUT_ATTRIBUTE = str(SETTINGS["opt_out_attribute"])

VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "image", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
# Containers whose whole subtree is irrelevant to composition. These are never void,
# so their end tag always arrives and the skip window always closes.
IGNORED_CONTAINERS = frozenset({"script", "style", "template", "noscript"})
# Recorded nowhere because they carry no composition: they are line breaks, not boxes.
UNRECORDED_TAGS = frozenset({"br", "wbr"})
# Whole-token matches only: a ".card" element is one card, while its ".card-title"
# and ".card-media" children are parts of that card, not additional cards.
CARD_PATTERN = re.compile(r"^(?:[a-z0-9]+-)*(?:card|tile|panel|item|cell|chip|step)s?(?:-\d+)?$", re.I)
COLUMN_PATTERN = re.compile(
    r"^(?:[a-z0-9]+-)*(?:col|column|grid|split|two-up|three-up)s?(?:-\d+)?$", re.I
)
LAYOUT_PATTERN = re.compile(
    r"(?:^|-)(?:card|tile|panel|item|cell|box|stat|metric|feature|step|col|column|grid|columns|"
    r"split|row|list|media|figure|hero|chart|table|quote|callout|badge|footer|header|caption|"
    r"content|wrap|stack|flex|two-up|three-up)(?:-|$)",
    re.I,
)
URL_PATTERN = re.compile(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^\)"\']+))\s*\)', re.I)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def normalize_asset(value: str, deck_root: Path) -> str | None:
    asset = value.strip()
    if not asset or asset.startswith("#"):
        return None
    if asset.startswith("data:"):
        header, _, payload = asset.partition(",")
        if header.lower().startswith("data:image/svg+xml"):
            return None
        try:
            data = base64.b64decode(payload) if ";base64" in header.lower() else unquote(payload).encode("utf-8")
        except Exception:
            data = asset.encode("utf-8")
        return "sha256:" + hashlib.sha256(data).hexdigest()
    parts = urlsplit(asset)
    if parts.scheme in {"http", "https"}:
        return "url:" + urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
    clean = unquote(parts.path)
    if not clean:
        return None
    candidate = (deck_root / clean).resolve()
    if candidate.is_file():
        return "sha256:" + hashlib.sha256(candidate.read_bytes()).hexdigest()
    return "path:" + str(Path(clean)).casefold()


class VarietyParser(HTMLParser):
    def __init__(self, deck_root: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.deck_root = deck_root
        self.stack: list[str] = []
        self.slides: list[dict[str, object]] = []
        self.current: dict[str, object] | None = None
        self.slide_depth: int | None = None
        self.ignore_depth: int | None = None

    def start_slide(self, values: dict[str, str], classes: set[str]) -> None:
        kind = (values.get("data-slide-kind") or values.get("data-content-kind") or "").strip().lower()
        exempt = kind in EXEMPT_SLIDE_KINDS or any(
            token.casefold() in EXEMPT_SLIDE_KINDS
            or re.search(r"(?:^|-)(?:section|divider|chapter|interstitial|transition|quote)(?:-|$)", token, re.I)
            for token in classes
        )
        self.current = {
            "number": len(self.slides) + 1,
            "title": (values.get("data-title") or "").strip(),
            "exempt": bool(exempt),
            "opt_out": (values.get(OPT_OUT_ATTRIBUTE) or "").strip(),
            "skeleton": [],
            "assets": set(),
            "cards": 0,
            "columns": 0,
            "elements": 0,
        }
        self.slides.append(self.current)
        self.slide_depth = len(self.stack)

    def record_element(self, tag: str, values: dict[str, str], classes: set[str]) -> None:
        slide = self.current
        assert slide is not None
        layout = sorted({token.casefold() for token in classes if LAYOUT_PATTERN.search(token)})
        depth = len(self.stack) - (self.slide_depth or 0)
        slide["skeleton"].append(f"{tag}:{depth}:{'.'.join(layout)}")
        slide["elements"] = int(slide["elements"]) + 1
        if any(CARD_PATTERN.search(token) for token in classes):
            slide["cards"] = int(slide["cards"]) + 1
        if any(COLUMN_PATTERN.search(token) for token in classes):
            slide["columns"] = int(slide["columns"]) + 1
        for attribute in ("src", "href", "poster", "data-src"):
            value = values.get(attribute)
            if value and tag in {"img", "source", "image", "video", "audio"}:
                normalized = normalize_asset(value, self.deck_root)
                if normalized:
                    slide["assets"].add(normalized)
        srcset = values.get("srcset")
        if srcset:
            for candidate in srcset.split(","):
                token = candidate.strip().split(" ")[0] if candidate.strip() else ""
                normalized = normalize_asset(token, self.deck_root) if token else None
                if normalized:
                    slide["assets"].add(normalized)
        style = values.get("style") or ""
        for match in URL_PATTERN.finditer(style):
            raw = next(group for group in match.groups() if group is not None)
            normalized = normalize_asset(raw, self.deck_root)
            if normalized:
                slide["assets"].add(normalized)

    def handle_starttag(self, tag: str, attrs) -> None:
        values = {name: (value or "") for name, value in attrs}
        classes = set(values.get("class", "").split())
        if self.ignore_depth is None and tag in IGNORED_CONTAINERS:
            self.ignore_depth = len(self.stack)
        if tag == "section" and "slide" in classes:
            self.start_slide(values, classes)
        elif self.current is not None and self.ignore_depth is None and tag not in UNRECORDED_TAGS:
            self.record_element(tag, values, classes)
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for position in range(len(self.stack) - 1, -1, -1):
            if self.stack[position] == tag:
                del self.stack[position:]
                break
        if self.ignore_depth is not None and len(self.stack) <= self.ignore_depth:
            self.ignore_depth = None
        if tag == "section" and self.current is not None and self.slide_depth == len(self.stack):
            self.current = None
            self.slide_depth = None


def skeleton_similarity(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def describe(assets: set[str]) -> str:
    if not assets:
        return "no referenced media"
    return f"{len(assets)} shared asset(s)"


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: validate_slide_variety.py DECK.html")
    deck = Path(sys.argv[1]).resolve()
    if not deck.is_file():
        fail(f"deck not found: {deck}")
    parser = VarietyParser(deck.parent.resolve())
    parser.feed(deck.read_text(encoding="utf-8"))
    slides = parser.slides
    if not slides:
        fail("no slides found")

    candidates = [
        slide for slide in slides
        if not slide["exempt"] and int(slide["elements"]) >= MINIMUM_STRUCTURAL_ELEMENTS
    ]
    errors: list[str] = []
    approved: list[str] = []
    for position, left in enumerate(candidates):
        for right in candidates[position + 1 :]:
            if left["cards"] != right["cards"] or left["columns"] != right["columns"]:
                continue
            if left["assets"] != right["assets"]:
                continue
            ratio = skeleton_similarity(left["skeleton"], right["skeleton"])
            if ratio < SIMILARITY_THRESHOLD:
                continue
            pair = f"slides {left['number']} and {right['number']}"
            token = str(left["opt_out"])
            if token and token == right["opt_out"]:
                approved.append(f"{pair} repeat deliberately ({OPT_OUT_ATTRIBUTE}=\"{token}\")")
                continue
            errors.append(
                f"{pair} are near-duplicate compositions: skeleton similarity {ratio:.2f} "
                f">= {SIMILARITY_THRESHOLD:.2f}, {left['cards']} card(s), {left['columns']} column "
                f"container(s), and the same image set ({describe(left['assets'])}). "
                f"Titles: '{left['title']}' / '{right['title']}'. Rebuild one slide with a "
                f"different composition, or mark both with {OPT_OUT_ATTRIBUTE}=\"<reason>\" "
                "if the repeat is deliberate."
            )

    for note in approved:
        print(f"NOTICE: {note}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    exempt = len(slides) - len(candidates)
    print(
        f"OK: {deck} - {len(slides)} slides, {len(candidates)} substantive compositions compared "
        f"({exempt} light/section slide(s) exempt), no near-duplicate pairs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
