#!/usr/bin/env python3
"""Tests for canonical slide navigation interactions."""

from __future__ import annotations

import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_interactions.py"
BROWSER_VALIDATOR = ROOT / "scripts" / "validate_browser_e2e.js"
TEMPLATE = ROOT / "assets" / "runtime-shell.html"


class InteractionTests(unittest.TestCase):
    def validate(self, html: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(html, encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_navigation_passes(self) -> None:
        result = self.validate(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_text_arrow_navigation_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
            "←",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("#prev must use an inline SVG icon", result.stdout)

    def test_cached_node_with_named_handler_passes(self) -> None:
        """Idiomatic JS: cache the node up top, bind a named handler further down."""
        html = TEMPLATE.read_text(encoding="utf-8")
        html = html.replace(
            "      prev.addEventListener('click', () => show(index - 1));\n"
            "      next.addEventListener('click', () => show(index + 1));\n",
            "",
            1,
        )
        html = html.replace(
            "      full.addEventListener('click',",
            "      function goPrevious() { show(index - 1); }\n"
            "      function goNext() { show(index + 1); }\n"
            "      // spacing that used to break the 80-character proximity window\n"
            "      const NAVIGATION_STEP_COMMENT = 'previous and next are wired below';\n"
            "      prevButton.addEventListener('click', goPrevious);\n"
            "      nextButton.addEventListener('click', goNext);\n"
            "      full.addEventListener('click',",
            1,
        )
        html = html.replace(
            "      const prev = document.getElementById('prev');\n"
            "      const next = document.getElementById('next');",
            "      const prevButton = document.getElementById('prev');\n"
            "      const nextButton = document.getElementById('next');\n"
            "      const prev = prevButton;\n"
            "      const next = nextButton;",
            1,
        )
        self.assertIn("prevButton.addEventListener", html)
        result = self.validate(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_commented_out_anchor_is_ignored(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<!-- <a href="#">draft link kept for reference</a> -->',
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_anchor_inside_script_string_literal_is_ignored(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "      addEventListener('resize', fit);",
            "      const TEMPLATE_SNIPPET = '<a href=\"#\">placeholder</a>';\n"
            "      void TEMPLATE_SNIPPET;\n"
            "      addEventListener('resize', fit);",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_empty_anchor_still_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->", '<a href="#">dead link</a>', 1
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("anchor is missing a real href", result.stdout)

    def test_unbound_button_still_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<button id="orphanAction" type="button">Do the thing</button>',
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("orphanAction", result.stdout)
        self.assertIn("no detectable action", result.stdout)

    def test_button_mentioned_only_in_a_comment_still_fails(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<button id="orphanAction" type="button">Do the thing</button>',
            1,
        ).replace(
            "      addEventListener('resize', fit);",
            "      // orphanAction.addEventListener('click', () => {});\n"
            "      addEventListener('resize', fit);",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 1)
        self.assertIn("orphanAction", result.stdout)

    def test_button_bound_through_a_binding_helper_passes(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<button id="replay" type="button">Replay</button>',
            1,
        ).replace(
            "      addEventListener('resize', fit);",
            "      const bind = (element, handler) => { element.addEventListener('click', handler); };\n"
            "      const replayButton = document.getElementById('replay');\n"
            "      bind(replayButton, () => show(0));\n"
            "      addEventListener('resize', fit);",
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_button_inside_template_is_not_audited(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "<!-- SLIDE_2_CONTENT -->",
            '<template id="rowTemplate"><button class="row-btn">Inert</button></template>',
            1,
        )
        result = self.validate(html)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_browser(self, html: str) -> subprocess.CompletedProcess[str]:
        if shutil.which("node") is None:
            self.skipTest("Node.js is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "deck.html"
            deck.write_text(html, encoding="utf-8")
            return subprocess.run(
                ["node", str(BROWSER_VALIDATOR), str(deck)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_template_navigation_and_print_pass_browser_e2e(self) -> None:
        result = self.run_browser(TEMPLATE.read_text(encoding="utf-8"))
        if "Playwright is not installed" in result.stderr:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("print layout passed E2E", result.stdout)

    def test_broken_next_handler_fails_browser_e2e(self) -> None:
        html = TEMPLATE.read_text(encoding="utf-8").replace(
            "next.addEventListener('click', () => show(index + 1));",
            "next.addEventListener('click', () => {});",
            1,
        )
        result = self.run_browser(html)
        if "Playwright is not installed" in result.stderr:
            self.skipTest(result.stderr.strip())
        self.assertEqual(result.returncode, 1)
        self.assertIn("next button produced inconsistent navigation state", result.stderr)


if __name__ == "__main__":
    unittest.main()
