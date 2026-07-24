#!/usr/bin/env python3
"""Interaction-semantics gate for a deck's persistent navigation and controls.

Everything here works from the parsed document (deck_html), never from raw HTML
text. Raw-text scanning could not tell a live control from one inside an HTML
comment, a <script> string literal, or a <template>, and the old
80-character proximity window between getElementById and addEventListener
rejected the most ordinary way to write the deck runtime.

Behavioural proof that prev/next/full actually move the deck lives in
validate_browser_e2e.js; this file proves the deck is *structurally* wired.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import deck_html


ORDERED_NAV_IDS = ("prev", "pageInput", "total", "next", "full")
ICON_BUTTON_IDS = ("prev", "next", "full")
ACTION_ATTRIBUTES = ("data-goto", "data-next", "data-prev", "onclick")
CLICKABLE_CLASS = re.compile(r"(?:^|[-_])(?:cta|btn|button|clickable|link)$")
UTILITY_LABELS = (
    "표지로 돌아",
    "처음으로 돌아",
    "처음부터 다시",
    "다시 시작",
    "마지막 한 장",
    "마지막 장",
    "마지막 슬라이드",
    "끝으로 이동",
    "back to cover",
    "back to start",
    "restart",
    "view last slide",
    "last slide",
    "final slide",
)


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def check_navigation_panel(index: deck_html.DocumentIndex, errors: list[str]) -> None:
    panels = [
        element
        for element in index.by_tag("nav")
        if element.classes & {"nav", "controls"}
    ]
    if not panels:
        errors.append("missing persistent .nav or .controls panel")
        return
    panel = panels[0]
    children = index.descendants(panel)
    by_id = {child.identifier: child for child in children if child.identifier}

    positions = []
    for identifier in ORDERED_NAV_IDS:
        child = by_id.get(identifier)
        if child is None:
            errors.append(f"navigation panel is missing #{identifier}")
        else:
            positions.append(child.start)
    if len(positions) == len(ORDERED_NAV_IDS) and positions != sorted(positions):
        errors.append("navigation panel order must be previous, current input, total, next, fullscreen")

    page_input = by_id.get("pageInput")
    if page_input is None or page_input.tag != "input" or page_input.attr("type").lower() != "number":
        errors.append("#pageInput must be a numeric input")

    for identifier in ICON_BUTTON_IDS:
        button = by_id.get(identifier)
        if button is None or button.tag != "button":
            errors.append(f"#{identifier} must use an inline SVG icon")
            continue
        if not index.descendants(button, "svg"):
            errors.append(f"#{identifier} must use an inline SVG icon")


def check_elements(index: deck_html.DocumentIndex, errors: list[str]) -> None:
    source = index.source
    bound_ids = deck_html.bound_element_ids(index.inline_scripts())
    delegated = bool(
        re.search(
            r"dataset\s*\.\s*goto|getAttribute\s*\(\s*['\"]data-goto|\[data-goto\]",
            "\n".join(deck_html.strip_js_comments(script) for script in index.inline_scripts()),
        )
    )

    for element in index.elements:
        if element.inert:
            continue
        classes = {value.lower() for value in element.classes}
        if any(CLICKABLE_CLASS.search(value) for value in classes) and element.tag not in {"a", "button"}:
            errors.append(
                f"<{element.tag}> with interactive-looking class {sorted(classes)} must be <a> or <button>"
            )

        if element.tag == "a" and element.attr("href").strip() in {"", "#"}:
            errors.append("anchor is missing a real href")

        if element.tag == "button":
            has_action_data = any(element.has_attr(name) for name in ACTION_ATTRIBUTES)
            identifier = element.identifier
            if not has_action_data and identifier not in bound_ids:
                errors.append(
                    f"button {identifier if identifier else '(without id)'} has no detectable action"
                )

        if element.tag in {"a", "button"}:
            is_internal_jump = element.has_attr("data-goto") or bool(
                re.fullmatch(r"#(?:\d+|first|last)", element.attr("href").strip(), re.I)
            )
            if is_internal_jump and not element.has_attr("data-utility-nav-ok"):
                label = f"{element.attr('aria-label')} {element.inner_text(source)}"
                label = re.sub(r"\s+", " ", label).strip().lower()
                if any(token in label for token in UTILITY_LABELS):
                    errors.append(
                        "redundant utility jump CTA is not allowed while persistent navigation exists: "
                        f"{label!r}"
                    )
            if "cta" in classes and not any(
                "cta-inner" in child.classes for child in index.descendants(element)
            ):
                errors.append("CTA content must be wrapped in one .cta-inner group for rendered centering")

    uses_goto = any(
        element.has_attr("data-goto") for element in index.elements if not element.inert
    )
    if uses_goto and not delegated:
        errors.append("data-goto controls exist but no navigation handler was detected")


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: validate_interactions.py DECK.html")

    path = Path(sys.argv[1]).resolve()
    if not path.is_file():
        fail(f"deck not found: {path}")

    index = deck_html.parse(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    check_navigation_panel(index, errors)
    check_elements(index, errors)

    if errors:
        for error in dict.fromkeys(errors):
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {path} - interactive-looking elements have actionable semantics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
