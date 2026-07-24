#!/usr/bin/env python3
"""Shared, parser-based HTML access for the deterministic deck validators.

Every validator that needs to know "what elements does this deck actually
contain" must go through this module instead of pattern-matching raw HTML.
Raw-HTML regex scanning cannot tell a live element from one that sits inside an
HTML comment, a <script> string literal, or a <template>, and it makes attribute
order significant.  Both classes of bug have shipped broken decks before, so the
extraction below is the single source of truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "image", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Tags whose children are inert: they never render as deck interaction targets.
INERT_ANCESTORS = {"template", "script", "style", "noscript"}


@dataclass
class Element:
    """One start tag and the source span it encloses."""

    tag: str
    attrs: dict[str, str]
    start: int
    content_start: int
    content_end: int
    end: int
    depth: int
    ancestors: tuple[str, ...] = ()
    raw: str = ""

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    @property
    def identifier(self) -> str:
        return (self.attrs.get("id") or "").strip()

    def attr(self, name: str) -> str:
        value = self.attrs.get(name)
        return "" if value is None else value

    def has_attr(self, name: str) -> bool:
        return name in self.attrs

    def has_class(self, name: str) -> bool:
        return name in self.classes

    @property
    def inert(self) -> bool:
        return any(tag in INERT_ANCESTORS for tag in self.ancestors)

    def inner_html(self, source: str) -> str:
        return source[self.content_start:self.content_end]

    def inner_text(self, source: str) -> str:
        body = self.inner_html(source)
        body = re.sub(r"<!--[\s\S]*?-->", " ", body)
        body = re.sub(r"<(script|style)\b[^>]*>[\s\S]*?</\1>", " ", body, flags=re.I)
        body = re.sub(r"<[^>]+>", " ", body)
        return re.sub(r"\s+", " ", body).strip()

    def contains(self, other: "Element") -> bool:
        return self.content_start <= other.start < self.content_end


class DocumentIndex(HTMLParser):
    """Positional element index for a deck document."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._line_starts = [0]
        for match in re.finditer(r"\n", source):
            self._line_starts.append(match.end())
        self.elements: list[Element] = []
        self.comments: list[str] = []
        self._open: list[Element] = []
        self.feed(source)
        self.close()
        for element in self._open:
            element.content_end = len(source)
            element.end = len(source)
        self._open = []

    # -- position helpers -------------------------------------------------
    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _open_tags(self) -> tuple[str, ...]:
        return tuple(element.tag for element in self._open)

    # -- HTMLParser hooks -------------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        start = self._offset()
        raw = self.get_starttag_text() or f"<{tag}>"
        content_start = start + len(raw)
        element = Element(
            tag=tag,
            attrs={name: ("" if value is None else value) for name, value in attrs},
            start=start,
            content_start=content_start,
            content_end=content_start,
            end=content_start,
            depth=len(self._open),
            ancestors=self._open_tags(),
            raw=raw,
        )
        self.elements.append(element)
        if tag not in VOID_TAGS:
            self._open.append(element)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS and self._open and self._open[-1].tag == tag:
            self._open.pop()

    def handle_endtag(self, tag: str) -> None:
        start = self._offset()
        closing = self.source.find(">", start)
        end = len(self.source) if closing < 0 else closing + 1
        for position in range(len(self._open) - 1, -1, -1):
            if self._open[position].tag == tag:
                for unclosed in self._open[position + 1:]:
                    unclosed.content_end = start
                    unclosed.end = start
                element = self._open[position]
                element.content_end = start
                element.end = end
                del self._open[position:]
                return

    def handle_comment(self, data: str) -> None:
        self.comments.append(data)

    # -- queries ----------------------------------------------------------
    def by_tag(self, *tags: str, live_only: bool = True) -> list[Element]:
        wanted = {tag.lower() for tag in tags}
        return [
            element
            for element in self.elements
            if element.tag in wanted and (not live_only or not element.inert)
        ]

    def descendants(self, parent: Element, *tags: str) -> list[Element]:
        wanted = {tag.lower() for tag in tags}
        return [
            element
            for element in self.elements
            if element is not parent
            and parent.contains(element)
            and (not wanted or element.tag in wanted)
        ]

    def slides(self) -> list[Element]:
        return [
            element
            for element in self.elements
            if element.tag == "section" and "slide" in element.classes and not element.inert
        ]

    def inline_scripts(self) -> list[str]:
        return [
            element.inner_html(self.source)
            for element in self.elements
            if element.tag == "script" and not element.attr("src").strip()
        ]


def parse(source: str) -> DocumentIndex:
    return DocumentIndex(source)


def slide_titles(source: str) -> list[str]:
    """One entry per `<section class="slide">`, empty string when data-title is absent.

    Attribute order is irrelevant because this reads parsed attributes, so
    validate_deck.py and validate_speaker_notes.py can never disagree about the
    titles of the same deck.
    """
    return [element.attr("data-title").strip() for element in parse(source).slides()]


_JS_TOKEN = re.compile(
    r"""
    (?P<line>//[^\n]*)
  | (?P<block>/\*[\s\S]*?\*/)
  | (?P<dquote>"(?:\\.|[^"\\\n])*")
  | (?P<squote>'(?:\\.|[^'\\\n])*')
  | (?P<template>`(?:\\.|[^`\\])*`)
  | (?P<regex>/(?![/*])(?:\\.|\[(?:\\.|[^\]\\])*\]|[^/\\\n])+/[gimsuyd]*)
    """,
    re.X,
)


def strip_js_comments(code: str) -> str:
    """Remove JS comments while preserving string literals verbatim.

    String literals are scanned as whole tokens so that a `//` or `/*` inside a
    quoted selector cannot swallow the rest of the file.
    """

    def replace(match: re.Match[str]) -> str:
        if match.lastgroup in {"line", "block"}:
            return " "
        return match.group(0)

    return _JS_TOKEN.sub(replace, code)


def _matched_block(code: str, open_index: int) -> str:
    depth = 0
    for position in range(open_index, len(code)):
        character = code[position]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return code[open_index:position + 1]
    return code[open_index:]


def binding_helper_names(code: str) -> set[str]:
    """Names of functions whose own body attaches an event listener."""
    names: set[str] = set()
    declarations = re.finditer(
        r"(?:function\s+(?P<fn>[A-Za-z_$][\w$]*)\s*\()"
        r"|(?:(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
        r"(?:async\s+)?(?:function\b[^(]*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>))",
        code,
    )
    for match in declarations:
        name = match.group("fn") or match.group("name")
        if not name:
            continue
        brace = code.find("{", match.end())
        if brace < 0:
            continue
        body = _matched_block(code, brace)
        if re.search(r"addEventListener\s*\(|\.\s*on[a-z]+\s*=", body):
            names.add(name)
    return names


_LOOKUP = (
    r"document\s*\.\s*(?:"
    r"getElementById\s*\(\s*(?P<q1>['\"])(?P<id1>[^'\"]+)(?P=q1)\s*\)"
    r"|querySelector\s*\(\s*(?P<q2>['\"])\s*#(?P<id2>[A-Za-z_][\w:.-]*)\s*(?P=q2)\s*\)"
    r")"
)


def bound_element_ids(scripts: list[str]) -> set[str]:
    """Element ids that inline script demonstrably wires to an event handler.

    Handles the idiomatic shape the old 80-character proximity window rejected:
    cache the node in a variable at the top of the IIFE, bind a handler further
    down.  Also handles direct chaining, object-literal grouping, array
    `forEach` binding, and passing the node to a helper that binds internally.
    """
    code = "\n".join(strip_js_comments(script) for script in scripts)
    if not code.strip():
        return set()

    bound: set[str] = set()
    aliases: dict[str, set[str]] = {}

    for match in re.finditer(_LOOKUP, code):
        element_id = match.group("id1") or match.group("id2")
        if not element_id:
            continue
        tail = code[match.end():match.end() + 40]
        if re.match(r"\s*(?:\?\.)?\s*(?:addEventListener\s*\(|on[a-z]+\s*=)", tail):
            bound.add(element_id)
        head = code[max(0, match.start() - 120):match.start()]
        alias = re.search(r"([A-Za-z_$][\w$]*)\s*[=:]\s*$", head)
        if alias:
            aliases.setdefault(element_id, set()).add(alias.group(1))

    helpers = binding_helper_names(code)
    for element_id, names in aliases.items():
        for name in names:
            token = re.escape(name)
            direct = re.search(
                rf"(?<![\w$]){token}\s*(?:\?\.)?\s*\.?\s*"
                rf"(?:addEventListener\s*\(|on[a-z]+\s*=)",
                code,
            )
            grouped = re.search(
                rf"\[[^\]\n]*(?<![\w$]){token}(?![\w$])[^\]\n]*\]\s*\.\s*for[Ee]ach\s*\(",
                code,
            )
            handed_off = any(
                re.search(
                    rf"(?<![\w$]){re.escape(helper)}\s*\([^()]*(?<![\w$]){token}(?![\w$])",
                    code,
                )
                for helper in helpers
            )
            if direct or grouped or handed_off:
                bound.add(element_id)
                break
    return bound
