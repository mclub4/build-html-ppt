#!/usr/bin/env python3
"""Guard the user-confirmation and installation-consent workflow contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_new_presentation_resolves_audience_and_mode_together(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        for document in (skill, contract):
            self.assertIn("audience", document)
            self.assertIn("validation mode", document)
            self.assertIn("one opening message", document)
            self.assertIn("청중은 알아서 해줘", document)
            self.assertIn("general company-wide concept-sharing audience", document)
            self.assertIn("빠른 검증 (Quick Draft)", document)
            self.assertIn("정밀 검증 (Full Validation)", document)
            self.assertIn("creation-only", document)
        self.assertIn("Require an explicit mode choice and do not silently infer it", skill)
        self.assertIn("The user must choose a mode explicitly", contract)

    def test_quick_draft_skips_validation_and_full_requires_preflight(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        self.assertIn("this is a creation-only mode with no rendered validation", skill)
        self.assertIn("only a no-op safety guard", skill)
        self.assertIn("deliver immediately after implementation without running any validation command", skill)
        self.assertIn("Quick Draft is creation-only", contract)
        self.assertIn("Do not run `check_environment.py`", contract)
        self.assertIn("accidental-call guard", contract)
        self.assertIn("Do not run `check_environment.py`", skill)
        self.assertIn("After the user chooses Full Validation", skill)
        self.assertIn("After the user chooses Full Validation", contract)
        self.assertIn("python3 scripts/check_environment.py", skill)
        self.assertIn("python3 scripts/check_environment.py", contract)
        self.assertIn("explicit installation consent", skill)
        self.assertIn("explicit consent", contract)
        self.assertIn("Never run `npm install`", skill)
        self.assertIn("Do not run `npm install`", contract)
        self.assertIn("install_browser_dependencies.py --consent", skill)
        self.assertIn("install_browser_dependencies.py --consent", contract)

    def test_quick_draft_uses_bounded_shared_authoring_path(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        quick = (ROOT / "references" / "quick-draft-authoring.md").read_text(encoding="utf-8")
        shell = (ROOT / "assets" / "runtime-shell.html").read_text(encoding="utf-8")
        prompt = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("four or five reusable composition families", skill)
        self.assertIn("at most two signature slides", skill)
        self.assertIn("10-20 minutes", contract)
        self.assertIn("never recreate the stage fitter", quick)
        self.assertIn("Do not write hundreds of lines of slide-specific CSS", quick)
        self.assertIn("four or five reusable composition families", prompt)
        for helper in (
            ".layout-hero",
            ".layout-split",
            ".layout-editorial",
            ".layout-columns",
            ".layout-gallery",
        ):
            self.assertIn(helper, shell)

    def test_large_area_palette_roles_require_provenance(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        playbook = (ROOT / "references" / "theme-playbook.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        prompt = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("palette provenance", skill)
        self.assertIn("Palette provenance and area", playbook)
        self.assertIn("Unsupported high-chroma colors", skill)
        self.assertIn("one-off high-chroma full-slide reset", quality)
        self.assertIn("Large high-chroma surfaces", visual)
        self.assertIn("unsupported high-chroma colors remain small accents", prompt)

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
        self.assertEqual(
            machine_contract["cross_review_routes"],
            {
                "visual_critical": True,
                "automation_warning": True,
                "identity_required": True,
            },
        )

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
        self.assertEqual(machine["schema_version"], 13)
        self.assertEqual(machine["review_batch_size"], 4)
        self.assertEqual(machine["base_profiles"], ["normal", "short", "zoom150"])
        self.assertIn("font_integrity", machine["automation_checks_by_change"]["text"])
        self.assertIn("contrast", machine["automation_checks_by_change"]["text"])
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
        self.assertIn("every family actually used", typography)
        self.assertTrue((ROOT / "scripts" / "validate_fonts.py").is_file())

    def test_review_recording_status_and_timings_are_documented(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "validation-contract.md").read_text(encoding="utf-8")
        for document in (skill, contract):
            self.assertIn("record_review.py", document)
            self.assertIn("--status", document)
            self.assertIn("timings.json", document)
        self.assertTrue((ROOT / "scripts" / "record_review.py").is_file())

    def test_contrast_and_alt_are_blocking_or_explicitly_deferred(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        self.assertIn("missing alt text blocks Full Validation", skill)
        self.assertIn("4.5:1", visual)
        self.assertIn("3:1", visual)
        self.assertIn("routed to full-size AI contrast inspection", visual)
        self.assertTrue((ROOT / "scripts" / "measure_contrast.js").is_file())

    def test_unfamiliar_term_notes_are_semantic_audience_aware_and_sparse(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        audience = (ROOT / "references" / "audience-story-routing.md").read_text(encoding="utf-8")
        korean = (ROOT / "references" / "korean-copy.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        self.assertIn("semantic terminology burden list", skill)
        self.assertIn("Do not run a keyword, acronym, capitalization, or frequency parser", audience)
        self.assertIn("first meaningful occurrence", audience)
        self.assertIn("NXT컨소시엄", audience)
        self.assertIn("KDX", audience)
        self.assertIn("One or two notes on a slide is normally enough", audience)
        self.assertIn("용어 — 이 발표에서 뜻하는 역할", korean)
        self.assertIn("Decision-critical unfamiliar terms", visual)
        self.assertIn("unnecessary glossary notes", quality)

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

    def test_available_companions_and_bundled_archify_are_routed_automatically(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        architecture = (ROOT / "references" / "architecture-diagrams.md").read_text(encoding="utf-8")
        archify_skill = (ROOT.parent / "archify" / "SKILL.md").read_text(encoding="utf-8")
        archify_utils = (
            ROOT.parent / "archify" / "renderers" / "shared" / "utils.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("## Companion Skill Routing", skill)
        self.assertIn("If `humanize-korean` is available", skill)
        self.assertIn("Bundled distributions include `archify`", skill)
        self.assertIn("without waiting for a separate request", skill)
        self.assertIn("Availability is sufficient consent", skill)
        self.assertIn("Do not ask whether to use an available", skill)
        self.assertIn("never install software during deck work", skill)
        self.assertIn("Supported distributions bundle `archify`", architecture)
        self.assertIn("Do not load its full instructions during ordinary deck planning", skill)
        self.assertIn("Technical vocabulary alone is never sufficient", skill)
        self.assertIn("skip Archify entirely", skill)
        self.assertIn("Do not implement a keyword, substring, regex, quota", architecture)
        self.assertIn("export_archify_asset.js", architecture)
        self.assertTrue((ROOT / "scripts" / "export_archify_asset.js").is_file())
        self.assertIn("self-contained HTML output", architecture)
        self.assertIn("one pure SVG plus an exact-size WebP", architecture)
        self.assertNotIn("archify-repo.architecture.json", archify_skill)
        self.assertNotIn("maka-architecture.architecture.json", archify_skill)
        self.assertNotIn("archify-repo-grid.architecture.json", archify_skill)
        self.assertNotIn("examples/web-app.html", archify_skill)
        self.assertIn("examples/web-app.architecture.json", archify_skill)
        self.assertIn("examples/production-deployment.architecture.json", archify_skill)
        self.assertIn("examples/web-app-rendered.html", archify_skill)
        self.assertIn('data-theme="light"', archify_utils)

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

    def test_visuals_are_selected_by_claim_contribution_not_photo_presence(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        media = (ROOT / "references" / "media-strategy.md").read_text(encoding="utf-8")
        generation = (ROOT / "references" / "image-generation.md").read_text(encoding="utf-8")
        quick = (ROOT / "references" / "quick-draft-authoring.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        reviewer = (ROOT.parents[2] / "agents" / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        editor = (ROOT.parents[2] / "agents" / "build-html-slides-quality-editor.md").read_text(encoding="utf-8")
        self.assertIn("evidence, identity, mechanism, concept, or atmosphere", skill)
        self.assertIn("## Require a visual contribution", media)
        self.assertIn("stock substitution test", media)
        self.assertIn("Financial education or fintech explainer", media)
        self.assertIn("generated concept illustration", generation)
        self.assertIn("interchangeable stock photography", quick)
        self.assertIn("Generic stock photography occupies main explanatory space", quality)
        self.assertIn("Every main visual has a legible job", visual)
        self.assertIn("## Media Contribution Gate", reviewer)
        self.assertIn("## Media Contribution Gate", editor)

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

    def test_technology_theme_routing_allows_deliberate_dark_without_topic_noun_default(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        gallery = (ROOT / "references" / "theme-gallery.md").read_text(encoding="utf-8")
        playbook = (ROOT / "references" / "theme-playbook.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        visual_qa = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        prompt = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        editor = (ROOT.parents[2] / "agents" / "build-html-slides-quality-editor.md").read_text(encoding="utf-8")
        self.assertIn("Technology is a subject domain, not a visual theme", playbook)
        self.assertIn("evidence-led schematic direction", skill)
        self.assertIn("contemporary editorial or geometric direction", skill)
        self.assertIn("Dark-led directions remain valid", skill)
        self.assertIn("## 22. Paper Systems", gallery)
        self.assertIn("## 23. Interface Lab", gallery)
        self.assertIn("## 24. Human Infrastructure", gallery)
        self.assertIn("technology vocabulary alone is not enough", gallery)
        self.assertIn("A dark-led presentation is fully valid", playbook)
        self.assertIn("generic template behavior", quality)
        self.assertIn("Darkness itself is not a failure", quality)
        self.assertIn("dark-console fingerprint", visual_qa)
        self.assertIn("Both dark-led and paper-led systems remain valid", prompt)
        self.assertIn("Different card counts are not layout rhythm", editor)

    def test_contemporary_art_direction_rejects_pale_card_walls_and_generic_type(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        candidates = (ROOT / "references" / "design-candidate-search.md").read_text(encoding="utf-8")
        playbook = (ROOT / "references" / "theme-playbook.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        typography = (ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        prompt = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        editor = (ROOT.parents[2] / "agents" / "build-html-slides-quality-editor.md").read_text(encoding="utf-8")
        self.assertIn("Paper Systems is one candidate, not the corrective default", skill)
        self.assertIn("pale report with repeated top-title-plus-card rows", skill)
        self.assertIn("Different panel counts still count as the same composition", quality)
        self.assertIn("roughly one third of body slides", quality)
        self.assertIn("same family, width, and texture", typography)
        self.assertIn("contemporary editorial", candidates)
        self.assertIn("single rounded sans for every role", playbook)
        self.assertIn("different card counts are not layout rhythm", editor.lower())
        self.assertIn("Paper Systems is a candidate", prompt)

    def test_term_notes_are_micro_annotations_and_source_classes_are_reserved(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        audience = (ROOT / "references" / "audience-story-routing.md").read_text(encoding="utf-8")
        typography = (ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        prompt = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        density = (ROOT / "scripts" / "measure_container_density.js").read_text(encoding="utf-8")
        self.assertIn("data-term-note", skill)
        self.assertIn("data-source-citation", skill)
        self.assertIn("never as a large card", skill)
        self.assertIn("no large white card", audience)
        self.assertIn("audience term notes: typically 10–12px", typography)
        self.assertIn("large annotation card", visual)
        self.assertIn("never combine the generic .source citation class", prompt)
        self.assertIn("rendered-surface", density)
        self.assertIn("term note must remain a compact caption", density)

    def test_prompt_residue_stays_private_and_notes_reserve_navigation_space(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cover = (ROOT / "references" / "cover-design.md").read_text(encoding="utf-8")
        audience = (ROOT / "references" / "audience-story-routing.md").read_text(encoding="utf-8")
        korean = (ROOT / "references" / "korean-copy.md").read_text(encoding="utf-8")
        typography = (ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        quick = (ROOT / "references" / "quick-draft-authoring.md").read_text(encoding="utf-8")
        quality = (ROOT / "references" / "quality-bar.md").read_text(encoding="utf-8")
        visual = (ROOT / "references" / "visual-qa.md").read_text(encoding="utf-8")
        shell = (ROOT / "assets" / "runtime-shell.html").read_text(encoding="utf-8")
        reviewer = (ROOT.parents[2] / "agents" / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        editor = (ROOT.parents[2] / "agents" / "build-html-slides-quality-editor.md").read_text(encoding="utf-8")
        self.assertIn("Separate private authoring constraints", skill)
        self.assertIn("The authoring brief is private", cover)
        self.assertIn("Separate authoring instructions from audience copy", audience)
        self.assertIn("제작 프롬프트를 화면 문구로 옮기지 않기", korean)
        self.assertIn("개념 강의 + 팀 활동", quick)
        self.assertIn("280×84px", typography)
        self.assertIn("lower-right navigation exclusion zone", quality)
        self.assertIn("Footer term notes terminate before", visual)
        self.assertIn("--nav-exclusion-width: 280px", shell)
        self.assertIn(".nav-safe-note", shell)
        self.assertIn("## Prompt And Navigation Gate", reviewer)
        self.assertIn("## Prompt And Navigation Gate", editor)


if __name__ == "__main__":
    unittest.main()
