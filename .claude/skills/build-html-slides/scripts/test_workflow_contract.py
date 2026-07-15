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

    def test_fan_art_targets_are_checkpoints_and_do_not_expand_review_implicitly(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        budget = (ROOT / "references" / "fan-art-budget.md").read_text(encoding="utf-8")
        self.assertIn("checkpoints rather than hard caps", skill)
        self.assertIn("planning targets, not a forced process timeout", contract)
        self.assertIn("planning targets, not hard limits", budget)
        self.assertIn("25-35 minutes", budget)
        self.assertIn("40-50 works", budget)
        self.assertIn("24-30 works", budget)
        self.assertIn("ask whether to continue discovery", budget)
        self.assertIn("do not abruptly stop", budget)
        self.assertIn('Only `data-visual-critical="true"`', budget)

    def test_full_validation_uses_one_entrypoint_and_bounded_time_target(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        for document in (skill, contract):
            self.assertIn("validate_all.py", document)
            self.assertIn("40-90 minutes", document)
        self.assertIn("20-25 slide deck", contract)
        self.assertIn("browser-page-scale zoom150", (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    def test_identity_review_is_automatic_and_webp_grounded(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        identity = (ROOT / "references" / "identity-review.md").read_text(encoding="utf-8")
        self.assertIn("automatically activated", skill)
        self.assertIn("Omitting the slide flag does not bypass review", identity)
        self.assertIn("local WebP reference", identity)

    def test_placeholders_are_blocked_and_typography_is_selected_proactively(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        typography = (ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        self.assertIn("Placeholders may exist only in the private authoring workspace", skill)
        self.assertIn("placeholder gate runs in every phase and mode", contract)
        self.assertIn("One occurrence blocks delivery", quality)
        self.assertIn("Choose the type system without asking a separate font question", typography)
        self.assertTrue((ROOT / "scripts" / "validate_placeholders.py").is_file())


if __name__ == "__main__":
    unittest.main()
