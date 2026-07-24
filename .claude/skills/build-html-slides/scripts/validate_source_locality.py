#!/usr/bin/env python3
"""Korean-market source locality gate.

Links are classified by parsing the URL, not by string-matching a trailing
slash. `https://www.example.co.kr` and `https://example.co.kr/` are the same
source; the old `\\.kr/` pattern only recognised the second one, so a deck that
cited Korean sources without trailing slashes was told it had none.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

import deck_html


LOCAL_PATH_SEGMENTS = {"kr", "ko", "ko-kr", "kr-ko"}
FOREIGN_PATH_SEGMENTS = {"us", "en-us", "jp", "en-gb"}
FOREIGN_EXEMPTION = "foreign-secondary"


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def path_segments(url: str) -> list[str]:
    return [segment.lower() for segment in urlsplit(url).path.split("/") if segment]


def is_local(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    if host == "kr" or host.endswith(".kr"):
        return True
    return any(segment in LOCAL_PATH_SEGMENTS for segment in path_segments(url))


def is_foreign_region(url: str) -> bool:
    return any(segment in FOREIGN_PATH_SEGMENTS for segment in path_segments(url))


def main() -> int:
    if len(sys.argv) != 2:
        fail("usage: validate_source_locality.py DECK.html")

    path = Path(sys.argv[1]).resolve()
    if not path.is_file():
        fail(f"deck not found: {path}")

    html = path.read_text(encoding="utf-8")
    index = deck_html.parse(html)
    root = next((element for element in index.elements if element.tag == "html"), None)
    lang = (root.attr("lang").lower() if root else "")
    if not lang.startswith("ko"):
        print(f"OK: {path} - Korean-market locality check not applicable")
        return 0

    local_links: list[str] = []
    foreign_links: list[str] = []
    for anchor in index.by_tag("a"):
        href = anchor.attr("href").strip()
        if not href or href.startswith("#"):
            continue
        if is_local(href):
            local_links.append(href)
        if is_foreign_region(href) and not is_local(href):
            if anchor.attr("data-source-locality").strip().lower() != FOREIGN_EXEMPTION:
                foreign_links.append(href)

    errors = []
    if foreign_links:
        errors.append(
            'Korean deck uses foreign-region audience links without data-source-locality="foreign-secondary": '
            + ", ".join(sorted(set(foreign_links)))
        )
    if not local_links:
        errors.append("Korean deck has no target-region source links (.kr, /kr/, or /ko/)")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {path} - Korean-market links prioritize target-region sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
