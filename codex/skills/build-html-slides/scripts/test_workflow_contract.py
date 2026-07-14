#!/usr/bin/env python3
"""Guard the user-confirmation and installation-consent workflow contract."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_new_deck_requires_explicit_mode_choice(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        self.assertIn("For every new deck, require an explicit mode choice", skill)
        self.assertIn("Do not silently infer a mode", skill)
        self.assertIn("New-deck creation requires an explicit user choice", contract)
        self.assertIn("Do not silently infer the mode", contract)

    def test_both_rendered_modes_require_preflight_and_install_consent(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        for document in (skill, contract):
            self.assertIn("Quick Draft or Full Validation", document)
            self.assertIn("python3 scripts/check_environment.py", document)
        self.assertIn("explicit installation consent", skill)
        self.assertIn("explicit consent", contract)
        self.assertIn("Never run `npm install`", skill)
        self.assertIn("Do not run `npm install`", contract)


if __name__ == "__main__":
    unittest.main()
