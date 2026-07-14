#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


if len(sys.argv) != 2:
    fail("usage: validate_source_locality.py DECK.html")

path = Path(sys.argv[1]).resolve()
if not path.is_file():
    fail(f"deck not found: {path}")

html = path.read_text(encoding="utf-8")
lang_match = re.search(r"<html\b[^>]*\blang=[\"']([^\"']+)", html, re.I)
lang = lang_match.group(1).lower() if lang_match else ""
if not lang.startswith("ko"):
    print(f"OK: {path} - Korean-market locality check not applicable")
    raise SystemExit(0)

anchors = list(re.finditer(r"<a\b([^>]*)>", html, re.I))
local_links = []
foreign_links = []
for match in anchors:
    attrs = match.group(1)
    href_match = re.search(r"\bhref=[\"']([^\"']+)", attrs, re.I)
    if not href_match:
        continue
    href = href_match.group(1)
    if re.search(r"(?:\.kr/|/kr/|/ko/)", href, re.I):
        local_links.append(href)
    if re.search(r"/(?:us|en-us|jp|en-gb)/", href, re.I):
        if not re.search(r"\bdata-source-locality=[\"']foreign-secondary[\"']", attrs, re.I):
            foreign_links.append(href)

errors = []
if foreign_links:
    errors.append("Korean deck uses foreign-region audience links without data-source-locality=\"foreign-secondary\": " + ", ".join(sorted(set(foreign_links))))
if not local_links:
    errors.append("Korean deck has no target-region source links (.kr, /kr/, or /ko/)")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)

print(f"OK: {path} - Korean-market links prioritize target-region sources")
