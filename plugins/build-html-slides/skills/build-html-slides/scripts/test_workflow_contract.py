#!/usr/bin/env python3
"""Guard the user-confirmation and installation-consent workflow contract."""

from __future__ import annotations

import json
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
        self.assertIn("install_browser_dependencies.py --consent", skill)
        self.assertIn("install_browser_dependencies.py --consent", contract)

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
        self.assertIn("Image count alone does not make a slide critical", budget)
        machine_contract = json.loads(
            (ROOT / "scripts" / "validation_contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(machine_contract["review_batch_size"], 4)
        self.assertLess(machine_contract["standard_cross_review"]["sample_ratio"], 1)

    def test_full_validation_uses_one_entrypoint_and_bounded_time_target(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        for document in (skill, contract):
            self.assertIn("validate_all.py", document)
            self.assertIn("40-90 minutes", document)
        self.assertIn("20-25 slide deck", contract)
        self.assertIn("--phase finalize-prepare", contract)
        self.assertIn("--phase finalize-verify", contract)
        self.assertIn("generated quality score", contract)
        self.assertIn("`cross_review_batches`", contract)
        self.assertIn("browser-page-scale zoom150", (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    def test_machine_contract_owns_exact_validation_values(self) -> None:
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        machine = json.loads((ROOT / "scripts" / "validation_contract.json").read_text(encoding="utf-8"))
        self.assertIn("machine-readable authority", contract)
        self.assertEqual(machine["schema_version"], 10)
        self.assertEqual(machine["review_batch_size"], 4)
        self.assertEqual(machine["base_profiles"], ["normal", "short", "zoom150"])
        self.assertIn("font_integrity", machine["automation_checks_by_change"]["text"])
        self.assertEqual(machine["impact_scopes"], ["direct", "neighbors", "full"])
        self.assertEqual(
            machine["content_change_categories"],
            ["text", "image", "structure", "style", "runtime"],
        )
        self.assertRegex(machine["playwright_version"], r"^\d+\.\d+\.\d+$")

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
        self.assertIn("placeholder gate therefore runs once for every new or edited source", contract)
        self.assertIn("One occurrence blocks delivery", quality)
        self.assertIn("Choose the type system without asking a separate font question", typography)
        self.assertTrue((ROOT / "scripts" / "validate_placeholders.py").is_file())

    def test_typography_blocks_synthetic_bold_and_noop_emphasis(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        typography = (ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        shell = (ROOT / "assets" / "runtime-shell.html").read_text(encoding="utf-8")
        measure = (ROOT / "scripts" / "measure_text_bounds.js").read_text(encoding="utf-8")
        self.assertIn("font-synthesis: none", shell)
        self.assertIn("Use only weights present", skill)
        self.assertIn("Bundle a real bold/semibold face", typography)
        self.assertIn("has no visible emphasis", measure)
        self.assertIn("outside its declared local faces", measure)

    def test_incremental_contract_scopes_work_without_dropping_independent_review(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        review = (ROOT / "references" / "slide-by-slide-review.md").read_text(encoding="utf-8")
        self.assertIn("pure copy, image, or slide-local CSS refreshes only affected slides", skill)
        self.assertIn("**Direct impact:**", contract)
        self.assertIn("**Neighbor impact:**", contract)
        self.assertIn("**Full impact:**", contract)
        self.assertIn("intentional independent cross-validation", contract)
        self.assertIn("Focus that loop on the failed slide and check family", review)

    def test_consumer_travel_routes_to_destination_magazine(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        gallery = (ROOT / "references" / "theme-gallery.md").read_text(encoding="utf-8")
        playbook = (ROOT / "references" / "theme-playbook.md").read_text(encoding="utf-8")
        self.assertIn("ordinary leisure guides default to Destination Magazine", skill)
        self.assertIn("## 7. Destination Magazine", gallery)
        self.assertIn("Do not select Field Notes merely because the subject is travel", gallery)
        self.assertIn("### Travel routing", playbook)
        self.assertIn("Japanese travel does not automatically mean dark green", playbook)

    def test_installed_companions_are_routed_without_implicit_installation(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        architecture = (ROOT / "references" / "architecture-diagrams.md").read_text(encoding="utf-8")
        self.assertIn("## Optional Companion Routing", skill)
        self.assertIn("If `humanize-korean` is available", skill)
        self.assertIn("If `archify` is available", skill)
        self.assertIn("without waiting for a separate request", skill)
        self.assertIn("Availability is sufficient consent", skill)
        self.assertIn("Do not ask whether to use an already-installed", skill)
        self.assertIn("ask before installing", skill)
        self.assertIn("When `archify` is already available", architecture)
        self.assertIn("self-contained HTML output", architecture)
        self.assertIn("inline SVG", architecture)

    def test_relevant_photography_is_default_unless_pure_html_is_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        media = (ROOT / "references" / "media-strategy.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        self.assertIn("pure-HTML, image-free, or typography/diagram-only", skill)
        self.assertIn("perform a bounded search for relevant sourced photographs", media)
        self.assertIn("This is a relevance rule, not an image quota", media)
        self.assertIn("omit them when they add no information", quality)

    def test_physical_subjects_keep_real_world_or_scientific_imagery(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        media = (ROOT / "references" / "media-strategy.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        self.assertIn("Full Validation controls assurance depth, not research breadth, art direction, or visual-media variety", skill)
        self.assertIn("## Classify the visual job semantically", media)
        self.assertIn("AI-driven semiconductor market change", media)
        self.assertIn("Cancer treatment research and development", media)
        self.assertIn("four to eight distinct sourced visual anchors", media)
        self.assertIn("must not remove useful subject imagery", quality)

    def test_cover_is_a_first_class_design_and_review_contract(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cover = (ROOT / "references" / "cover-design.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        reviewer = (ROOT.parents[2] / "agents" / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("references/cover-design.md", skill)
        self.assertIn("highest-priority art-direction decision", cover)
        self.assertIn("at least two materially different cover directions", cover)
        self.assertIn("cover and closing are always visual-critical", contract)
        self.assertIn("merely acceptable cover", quality)
        self.assertIn("For slide 1, apply `cover-design.md`", reviewer)

    def test_existing_subjects_use_authentic_media_and_generated_support_is_bounded(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        generation = (ROOT / "references" / "image-generation.md").read_text(encoding="utf-8")
        media = (ROOT / "references" / "media-strategy.md").read_text(encoding="utf-8")
        cover = (ROOT / "references" / "cover-design.md").read_text(encoding="utf-8")
        reviewer = (ROOT.parents[2] / "agents" / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("generated art must never stand in for the real subject", skill)
        self.assertIn("data-media-purpose", skill)
        self.assertIn("fourth-generation girl-group introduction", generation)
        self.assertIn("1990s-2000s game retrospective", generation)
        self.assertIn("Existing entertainment catalog or nostalgia retrospective", media)
        self.assertIn("authentic sourced identity anchor", generation)
        self.assertIn("dedicated refinement pass", cover)
        self.assertIn("generated-only depiction of an existing named subject", reviewer)

    def test_idol_editorial_index_is_optional_job_based_vocabulary(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        gallery = (ROOT / "references" / "theme-gallery.md").read_text(encoding="utf-8")
        playbook = (ROOT / "references" / "theme-playbook.md").read_text(encoding="utf-8")
        self.assertIn("## 21. Idol Editorial Index", gallery)
        self.assertIn("use Idol Editorial Index only when the job is multi-subject", gallery)
        self.assertIn("Do not select Idol Editorial Index merely because an idol appears", playbook)
        self.assertIn("bespoke theme contract", skill)
        self.assertIn("not presets or a closed taxonomy", gallery)


if __name__ == "__main__":
    unittest.main()
