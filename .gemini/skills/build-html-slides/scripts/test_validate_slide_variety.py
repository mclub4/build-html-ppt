#!/usr/bin/env python3
"""Regression tests for the deck-level near-duplicate composition gate."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate_slide_variety.py")
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "runtime-shell.html"


def card_slide(
    title: str,
    *,
    background: str = "#ffffff",
    images: tuple[str, ...] = ("assets/product.webp",),
    cards: int = 3,
    attributes: str = "",
    body: str | None = None,
) -> str:
    blocks = []
    for index in range(cards):
        image = images[index % len(images)] if images else ""
        media = f'<img class="card-media" src="{image}" alt="">' if image else ""
        blocks.append(
            f'<article class="card"><div class="card-figure">{media}</div>'
            f'<h3 class="card-title">Item {index + 1}</h3>'
            f'<p class="card-copy">{body or title} detail line {index + 1}</p>'
            f'<span class="card-price">{1000 + index}</span></article>'
        )
    return (
        f'<section class="slide" data-title="{title}"{attributes} style="background:{background}">'
        f'<div class="slide-content"><h2 class="section-heading">{title}</h2>'
        f'<div class="card-grid columns-3">{"".join(blocks)}</div></div></section>'
    )


def deck(*slides: str) -> str:
    return f"<!doctype html><html><body>{''.join(slides)}</body></html>"


class SlideVarietyTests(unittest.TestCase):
    def run_validator(self, html: str, assets: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in assets:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(relative.encode("utf-8"))
            target = root / "deck.html"
            target.write_text(html, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(target)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_shipped_defect_two_pages_differing_only_in_background(self) -> None:
        html = deck(
            card_slide("Lineup A"),
            card_slide("Lineup A repeat", background="#101820"),
        )
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("slides 1 and 2 are near-duplicate compositions", result.stdout)
        self.assertIn("3 card(s)", result.stdout)
        self.assertIn("1 shared asset(s)", result.stdout)

    def test_different_image_sets_are_not_duplicates(self) -> None:
        html = deck(
            card_slide("Lineup A", images=("assets/one.webp",)),
            card_slide("Lineup B", images=("assets/two.webp",)),
        )
        result = self.run_validator(html, ("assets/one.webp", "assets/two.webp"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no near-duplicate pairs", result.stdout)

    def test_different_card_counts_are_not_duplicates(self) -> None:
        html = deck(card_slide("Lineup A", cards=3), card_slide("Lineup B", cards=4))
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_repeated_section_dividers_are_deliberate_rhythm(self) -> None:
        divider = (
            '<section class="slide section-divider" data-slide-kind="section" data-title="Chapter {n}">'
            '<div class="slide-content"><p class="eyebrow">Part {n}</p><h2>Chapter {n}</h2></div></section>'
        )
        html = deck(
            divider.replace("{n}", "1"),
            card_slide("Lineup A"),
            divider.replace("{n}", "2"),
            card_slide("Lineup B", images=("assets/two.webp",)),
            divider.replace("{n}", "3"),
        )
        result = self.run_validator(html, ("assets/product.webp", "assets/two.webp"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("light/section slide(s) exempt", result.stdout)

    def test_light_slides_below_the_element_floor_are_exempt(self) -> None:
        quote = (
            '<section class="slide" data-title="Quote {n}"><div class="slide-content">'
            '<blockquote>Line {n}</blockquote></div></section>'
        )
        html = deck(quote.replace("{n}", "1"), quote.replace("{n}", "2"))
        result = self.run_validator(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_matching_opt_out_token_allows_a_deliberate_twin(self) -> None:
        html = deck(
            card_slide("Before", attributes=' data-variety-ok="before-after"'),
            card_slide("After", attributes=' data-variety-ok="before-after"', background="#101820"),
        )
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('data-variety-ok="before-after"', result.stdout)

    def test_opt_out_on_only_one_slide_still_fails(self) -> None:
        html = deck(
            card_slide("Before", attributes=' data-variety-ok="before-after"'),
            card_slide("After"),
        )
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("near-duplicate compositions", result.stdout)

    def test_restructured_slide_clears_the_gate(self) -> None:
        restructured = (
            '<section class="slide" data-title="Lineup B"><div class="slide-content">'
            '<h2 class="section-heading">Lineup B</h2>'
            '<figure class="hero-figure"><img class="hero-media" src="assets/product.webp" alt="">'
            '<figcaption class="hero-caption">Flagship</figcaption></figure>'
            '<ul class="spec-list"><li class="spec-row">Spec one</li><li class="spec-row">Spec two</li>'
            '<li class="spec-row">Spec three</li></ul>'
            '<p class="footnote">Price shown before tax.</p></div></section>'
        )
        html = deck(card_slide("Lineup A"), restructured)
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_shell_template_passes(self) -> None:
        result = self.run_validator(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inline_script_and_line_breaks_do_not_blind_the_parser(self) -> None:
        noisy = card_slide("Lineup A").replace(
            '<div class="slide-content">',
            '<div class="slide-content"><br><script>const x = "<div class=\'card\'>";</script>',
            1,
        )
        html = deck(noisy, card_slide("Lineup A repeat", background="#101820"))
        result = self.run_validator(html, ("assets/product.webp",))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("near-duplicate compositions", result.stdout)

    def test_deck_without_slides_fails_clearly(self) -> None:
        result = self.run_validator("<!doctype html><html><body><p>none</p></body></html>")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no slides found", result.stdout)


if __name__ == "__main__":
    unittest.main()
