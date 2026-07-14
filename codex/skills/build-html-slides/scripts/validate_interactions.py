#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


if len(sys.argv) != 2:
    fail("usage: validate_interactions.py DECK.html")

path = Path(sys.argv[1]).resolve()
if not path.is_file():
    fail(f"deck not found: {path}")

html = path.read_text(encoding="utf-8")
errors = []

nav_match = re.search(r'<nav\b[^>]*class=["\'][^"\']*\b(?:nav|controls)\b[^"\']*["\'][^>]*>(.*?)</nav>', html, re.I | re.S)
if not nav_match:
    errors.append("missing persistent .nav or .controls panel")
else:
    nav_body = nav_match.group(1)
    ordered_ids = ["prev", "pageInput", "total", "next", "full"]
    positions = []
    for ident in ordered_ids:
        match = re.search(rf'\bid=["\']{ident}["\']', nav_body, re.I)
        if not match:
            errors.append(f"navigation panel is missing #{ident}")
        else:
            positions.append(match.start())
    if len(positions) == len(ordered_ids) and positions != sorted(positions):
        errors.append("navigation panel order must be previous, current input, total, next, fullscreen")
    page_input = re.search(r'<input\b[^>]*\bid=["\']pageInput["\'][^>]*>', nav_body, re.I)
    if not page_input or not re.search(r'\btype=["\']number["\']', page_input.group(0), re.I):
        errors.append("#pageInput must be a numeric input")
    for ident in ("prev", "next", "full"):
        button = re.search(rf'<button\b[^>]*\bid=["\']{ident}["\'][^>]*>(.*?)</button>', nav_body, re.I | re.S)
        if not button or not re.search(r'<svg\b', button.group(1), re.I):
            errors.append(f"#{ident} must use an inline SVG icon")

for match in re.finditer(r"<([a-z][a-z0-9:-]*)\b([^>]*)>", html, re.I):
    tag = match.group(1).lower()
    attrs = match.group(2)
    class_match = re.search(r"\bclass=[\"']([^\"']*)", attrs, re.I)
    classes = class_match.group(1).lower().split() if class_match else []
    looks_clickable = any(re.search(r"(?:^|[-_])(cta|btn|button|clickable|link)$", c) for c in classes)

    if looks_clickable and tag not in {"a", "button"}:
        errors.append(f"<{tag}> with interactive-looking class {classes} must be <a> or <button>")

    if tag == "a":
        href = re.search(r"\bhref=[\"']([^\"']*)", attrs, re.I)
        if not href or href.group(1).strip() in {"", "#"}:
            errors.append("anchor is missing a real href")

    if tag == "button":
        has_action_data = re.search(r"\b(?:data-goto|data-next|data-prev|onclick)\b", attrs, re.I)
        ident = re.search(r"\bid=[\"']([^\"']+)", attrs, re.I)
        bound_by_id = False
        if ident:
            token = re.escape(ident.group(1))
            bound_by_id = bool(re.search(rf"(?:\b{token}\b|getElementById\([\"']{token}[\"']\)).{{0,80}}(?:onclick|addEventListener)", html, re.I | re.S))
        if not has_action_data and not bound_by_id:
            errors.append(f"button {ident.group(1) if ident else '(without id)'} has no detectable action")

if re.search(r"\bdata-goto=", html, re.I):
    has_delegate = re.search(r"(?:dataset\.goto|getAttribute\([\"']data-goto|\[data-goto\])", html, re.I)
    if not has_delegate:
        errors.append("data-goto controls exist but no navigation handler was detected")

utility_labels = (
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
for match in re.finditer(r"<(a|button)\b([^>]*)>(.*?)</\1>", html, re.I | re.S):
    tag, attrs, body = match.groups()
    is_internal_jump = bool(
        re.search(r"\bdata-goto=", attrs, re.I)
        or re.search(r"\bhref=[\"']#(?:\d+|first|last)[\"']", attrs, re.I)
    )
    if not is_internal_jump or re.search(r"\bdata-utility-nav-ok\b", attrs, re.I):
        continue
    aria = re.search(r"\baria-label=[\"']([^\"']*)", attrs, re.I)
    label = f"{aria.group(1) if aria else ''} {re.sub(r'<[^>]+>', ' ', body)}"
    label = re.sub(r"\s+", " ", label).strip().lower()
    if any(token in label for token in utility_labels):
        errors.append(f"redundant utility jump CTA is not allowed while persistent navigation exists: {label!r}")

for match in re.finditer(r"<(a|button)\b([^>]*)\bclass=[\"']([^\"']*\bcta\b[^\"']*)[\"']([^>]*)>(.*?)</\1>", html, re.I | re.S):
    body = match.group(5)
    if not re.search(r"\bclass=[\"'][^\"']*\bcta-inner\b", body, re.I):
        errors.append("CTA content must be wrapped in one .cta-inner group for rendered centering")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)

print(f"OK: {path} - interactive-looking elements have actionable semantics")
