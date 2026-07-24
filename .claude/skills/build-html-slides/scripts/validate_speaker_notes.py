#!/usr/bin/env python3
"""Presenter-notes gate: one numbered note section per slide, titles must agree.

Slide titles come from deck_html.slide_titles, the same helper validate_deck.py
uses. The previous local regex required class="slide" to appear before
data-title, so the two validators could disagree about the titles of one deck
and this gate would silently audit the wrong slides.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import deck_html


MIN_BULLETS = 5


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def main() -> int:
    if len(sys.argv) != 3:
        fail("usage: validate_speaker_notes.py DECK.html DECK-notes.md")

    deck_path, notes_path = (Path(value) for value in sys.argv[1:])
    if not deck_path.is_file():
        fail(f"deck not found: {deck_path}")
    if not notes_path.is_file():
        fail(f"speaker notes not found: {notes_path}")

    deck = deck_path.read_text(encoding="utf-8")
    notes = notes_path.read_text(encoding="utf-8")

    titles = deck_html.slide_titles(deck)
    if not titles:
        fail("no slide titles found in deck")
    untitled = [index for index, title in enumerate(titles, 1) if not title]
    if untitled:
        fail(
            "every slide needs data-title before presenter notes can be matched; "
            f"missing on slide(s) {', '.join(map(str, untitled))}"
        )

    section_matches = list(re.finditer(r"^##\s+(\d+)\.\s+(.+?)\s*$", notes, re.M))
    if len(section_matches) != len(titles):
        fail(f"notes sections ({len(section_matches)}) do not match slides ({len(titles)})")

    for index, (match, slide_title) in enumerate(zip(section_matches, titles), 1):
        number, note_title = match.groups()
        if int(number) != index:
            fail(f"expected note section {index}, found {number}")
        if note_title.strip() != slide_title.strip():
            fail(f"slide {index} title mismatch: deck='{slide_title}', notes='{note_title}'")
        body_start = match.end()
        body_end = section_matches[index].start() if index < len(section_matches) else len(notes)
        body = notes[body_start:body_end]
        bullet_count = len(re.findall(r"^\s*[-*]\s+\S+", body, re.M))
        if bullet_count < MIN_BULLETS:
            fail(f"slide {index} needs at least five note bullets; found {bullet_count}")

    print(f"OK: {notes_path} - {len(titles)} slide-note sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
