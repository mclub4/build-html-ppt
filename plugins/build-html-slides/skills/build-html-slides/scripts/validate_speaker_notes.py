#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


if len(sys.argv) != 3:
    fail("usage: validate_speaker_notes.py DECK.html DECK-notes.md")

deck_path, notes_path = map(Path, sys.argv[1:])
if not deck_path.is_file():
    fail(f"deck not found: {deck_path}")
if not notes_path.is_file():
    fail(f"speaker notes not found: {notes_path}")

deck = deck_path.read_text(encoding="utf-8")
notes = notes_path.read_text(encoding="utf-8")
titles = re.findall(r'<section\b[^>]*class=["\'][^"\']*\bslide\b[^"\']*["\'][^>]*data-title=["\']([^"\']+)', deck, re.I)
if not titles:
    fail("no slide titles found in deck")

section_matches = list(re.finditer(r'^##\s+(\d+)\.\s+(.+?)\s*$', notes, re.M))
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
    bullet_count = len(re.findall(r'^\s*[-*]\s+\S+', body, re.M))
    if bullet_count < 5:
        fail(f"slide {index} needs at least five note bullets; found {bullet_count}")

print(f"OK: {notes_path} - {len(titles)} slide-note sections")
