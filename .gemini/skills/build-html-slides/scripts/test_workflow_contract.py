#!/usr/bin/env python3
"""Guard the workflow contract, preferring measurement over prose matching.

This file used to be 228 assertions, 215 of which were `assertIn` string matches
against markdown. A string match proves a sentence exists; it never proves the
rule works. That is exactly how a self-contradicting reviewer scope survived a
green suite, and how a deck shipped after a "passing" Full Validation with four
naked-eye defects.

Every assertion here is now in one of three categories, and each test says which:

* **(a) behavioural** - the rule has an observable output signature, so the test
  drives the real checker, the real machine contract, or the real asset and
  asserts on what comes back. `BehaviouralContractTests`, `SuiteIntegrityTests`,
  and `GeneratedAgentPromptTests`.
* **(b) doc-only** - the rule is a judgment a machine cannot evaluate (consent,
  art direction, audience routing). It keeps a string assertion, anchored to the
  current authoritative wording, and every group names the single file that owns
  the rule. `DocumentedJudgmentTests`.
* **(c) deleted** - a deterministic gate replaced the prose, so asserting the
  prose would pin wording that no longer decides anything. Deletions are listed
  in `DELETED_ASSERTIONS` below with the reason, so the removal is reviewable
  rather than silent.

Counts, measured with `ast` rather than estimated:

    before   228 assertions in 27 tests, 215 of them assertIn/assertNotIn
    after    228 assertions in 46 tests
             (a) behavioural   59 across 22 tests
             (b) doc-only     169 across 24 tests, each group naming its owner
             (c) deleted       13 rules / ~24 assertions, in DELETED_ASSERTIONS
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REPO = ROOT.parents[2]
AGENTS = REPO / "agents"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# (c) Assertions deleted because a deterministic gate, not a paragraph, now owns
# the rule. Each entry is "old assertion -> what enforces it now".
DELETED_ASSERTIONS = {
    "40-90 minutes": "validation_contract.json time_budgets + validate_all.py --status",
    "checkpoints rather than hard caps": "time_budgets are ceilings; --status reports overrun",
    "planning targets, not a forced process timeout": "same",
    "planning targets, not hard limits": "same",
    "25-35 minutes / 40-50 works / 24-30 works": "the 25-minute media freeze checkpoint",
    "ask whether to continue discovery": "checkpoints act autonomously; asking is now a defect",
    "do not abruptly stop": "same",
    "routed to full-size AI contrast inspection": "measure_contrast.js proves the interval; only a straddling interval reaches a reviewer",
    "10-20 minutes (Quick Draft)": "time_budgets.quick.total_minutes",
    "Image count alone does not make a slide critical": "cross_review_routes in the machine contract",
    "openai.yaml assertIn x7": "generate_openai_agent.py --check; the prompt is generated from SKILL.md",
    "measure_text_bounds.js source strings x2": "test_measure_text_bounds.py drives the real script",
    "'no-op safety guard' / 'deliver immediately after implementation'": "validate_all.py --mode quick exits with QUICK_SKIP_MESSAGE at every phase",
}

RESERVED_OVERRIDES_ALLOWED = frozenset(
    {"setUp", "tearDown", "setUpClass", "tearDownClass", "maxDiff", "longMessage"}
)
LIFECYCLE_HOOKS = frozenset({"setUp", "tearDown", "setUpClass", "tearDownClass"})

# Gate thresholds live in references/reviewer-gates.md and
# scripts/validation_contract.json. The always-on Codex prompt must not restate
# one, because a restated number is a number that can go stale silently.
FORBIDDEN_PROMPT_THRESHOLDS = (
    "2px", "1.5px", "15%", "4.5:1", "3:1", "0.90", "280", "96px", "7%", "200×110",
)


def read(*parts: str) -> str:
    return ROOT.joinpath(*parts).read_text(encoding="utf-8")


def machine_contract() -> dict:
    return json.loads(read("scripts", "validation_contract.json"))


def run_script(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


class SuiteIntegrityTests(unittest.TestCase):
    """(a) The suite must not be able to report success without running.

    `test_record_review.py` defined a subprocess helper called `run` on a
    `TestCase`. `TestCase.__call__` dispatches through `self.run(result)`, so the
    helper swallowed the result object, shelled out, and returned a
    `CompletedProcess`. `testsRun` stayed at 0 and the suite printed OK. Four
    tests protecting "record_review.py never invents a verdict" had never
    executed. These tests make that class of failure impossible to reintroduce.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.modules = sorted(path.stem for path in SCRIPTS.glob("test_*.py"))

    def reserved_problems(self, klass: type) -> list[str]:
        """Names in a TestCase body that unittest would never dispatch as intended."""
        problems: list[str] = []
        for name in vars(klass):
            if name.startswith("__"):
                continue
            lowered = name.lower()
            if lowered.startswith("test") and not name.startswith("test"):
                problems.append(f"{klass.__name__}.{name} looks like a test but is never collected")
                continue
            if name.startswith("test"):
                continue
            if lowered in {hook.lower() for hook in LIFECYCLE_HOOKS} and name not in LIFECYCLE_HOOKS:
                problems.append(f"{klass.__name__}.{name} misspells a lifecycle hook and never runs")
                continue
            if name in RESERVED_OVERRIDES_ALLOWED:
                continue
            if hasattr(unittest.TestCase, name):
                problems.append(
                    f"{klass.__name__}.{name} shadows unittest.TestCase.{name}; "
                    "rename the helper"
                )
        return problems

    def test_the_reserved_name_checker_catches_the_historical_defect(self) -> None:
        class Shadowed(unittest.TestCase):  # pragma: no cover - inspected, never run
            def run(self, path, *arguments):  # type: ignore[override]
                return path

            def setup(self) -> None:
                pass

            def Test_thing(self) -> None:
                pass

        problems = " ".join(self.reserved_problems(Shadowed))
        self.assertIn("shadows unittest.TestCase.run", problems)
        self.assertIn("misspells a lifecycle hook", problems)
        self.assertIn("looks like a test but is never collected", problems)

    def test_every_test_module_contributes_at_least_one_collected_test(self) -> None:
        loader = unittest.TestLoader()
        empty = []
        for name in self.modules:
            module = importlib.import_module(f"scripts.{name}")
            if loader.loadTestsFromModule(module).countTestCases() == 0:
                empty.append(name)
        self.assertEqual(empty, [], f"test modules that collect zero tests: {empty}")

    def test_no_test_case_shadows_a_reserved_unittest_name(self) -> None:
        problems: list[str] = []
        for name in self.modules:
            module = importlib.import_module(f"scripts.{name}")
            for klass in vars(module).values():
                if (
                    isinstance(klass, type)
                    and issubclass(klass, unittest.TestCase)
                    and klass.__module__ == module.__name__
                ):
                    problems.extend(f"{name}: {problem}" for problem in self.reserved_problems(klass))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_every_test_case_still_dispatches_through_unittest_run(self) -> None:
        """A collected case whose `run` is not TestCase.run never increments testsRun."""
        loader = unittest.TestLoader()
        broken: list[str] = []
        for name in self.modules:
            module = importlib.import_module(f"scripts.{name}")
            for case in loader.loadTestsFromModule(module):
                for test in case:
                    if type(test).run is not unittest.TestCase.run:
                        broken.append(test.id())
        self.assertEqual(broken, [], f"cases that bypass the executed-test counter: {broken}")


class GeneratedAgentPromptTests(unittest.TestCase):
    """(a) agents/openai.yaml is generated from SKILL.md, so it cannot drift.

    Codex loads `default_prompt` always-on, against the same budgets as everyone
    else. It used to be a hand-maintained restatement of the whole rule set that
    lagged SKILL.md by 13 commits, protected only by seven `assertIn` checks that
    could catch deletion but never contradiction.
    """

    GENERATOR = REPO / "scripts" / "generate_openai_agent.py"
    TARGET = ROOT / "agents" / "openai.yaml"

    def test_regenerating_reproduces_the_committed_file_exactly(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.GENERATOR), "--check"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_generator_fails_loudly_when_an_anchor_disappears(self) -> None:
        source = self.GENERATOR.read_text(encoding="utf-8")
        self.assertIn("class MissingAnchor", source)
        self.assertIn("raise MissingAnchor", source)

    def test_the_prompt_carries_the_same_budgets_as_the_machine_contract(self) -> None:
        prompt = self.TARGET.read_text(encoding="utf-8")
        budgets = machine_contract()["time_budgets"]
        self.assertIn(f"Full Validation: {budgets['full']['total_minutes']} minutes", prompt)
        self.assertIn(f"Quick Draft: {budgets['quick']['total_minutes']} minutes", prompt)
        low, high = budgets["slide_range"]
        self.assertIn(f"{low}-{high} slide deck", prompt)

    def test_the_prompt_restates_no_gate_threshold(self) -> None:
        prompt = self.TARGET.read_text(encoding="utf-8")
        restated = [value for value in FORBIDDEN_PROMPT_THRESHOLDS if value in prompt]
        self.assertEqual(restated, [], f"the always-on prompt restates gate thresholds: {restated}")
        self.assertIn("reviewer-gates.md", prompt)

    def test_the_prompt_is_smaller_than_the_hand_written_one_it_replaced(self) -> None:
        # The hand-written default_prompt was 8153 bytes of always-on context.
        self.assertLess(len(self.TARGET.read_bytes()), 8153)

    def test_the_prompt_still_routes_intake_modes_and_reviewer_independence(self) -> None:
        prompt = self.TARGET.read_text(encoding="utf-8")
        for token in (
            "빠른 검증 (Quick Draft)",
            "정밀 검증 (Full Validation)",
            "one opening message",
            "record_review.py",
            "reviewer_ref",
            "CONFIRM: or REFUTE:",
        ):
            self.assertIn(token, prompt)


class BehaviouralContractTests(unittest.TestCase):
    """(a) Rules with an observable signature, driven through the real checker."""

    def test_quick_mode_performs_no_work_at_any_phase(self) -> None:
        import scripts.validate_all as validate_all

        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "OUTPUT.html"
            deck.write_text("<html><body></body></html>", encoding="utf-8")
            for phase in ("prepare", "verify", "finalize-prepare", "finalize-verify"):
                result = run_script("validate_all.py", str(deck), "--mode", "quick", "--phase", phase)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(validate_all.QUICK_SKIP_MESSAGE, result.stdout)
            self.assertEqual(
                sorted(item.name for item in Path(temporary).iterdir()),
                ["OUTPUT.html"],
                "quick mode wrote a workspace, timings file, or review directory",
            )

    def test_every_deterministic_gate_named_by_the_skill_is_actually_wired(self) -> None:
        import scripts.validate_all as validate_all

        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "OUTPUT.html"
            deck.write_text("<html></html>", encoding="utf-8")
            wired = {
                Path(command[1]).name
                for _, command in validate_all.deterministic_commands(
                    deck, deck.with_name("OUTPUT-notes.md"), deck.with_name("sources.json"), "all",
                    browser_e2e=True,
                )
            }
        for gate in (
            "validate_deck.py",
            "validate_placeholders.py",
            "validate_slide_variety.py",
            "validate_fonts.py",
            "validate_speaker_notes.py",
            "validate_source_locality.py",
            "validate_image_reuse.py",
            "validate_interactions.py",
        ):
            self.assertIn(gate, wired)

    def test_slide_variety_runs_for_text_image_and_structure_changes(self) -> None:
        import scripts.validate_all as validate_all

        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "OUTPUT.html"
            deck.write_text("<html></html>", encoding="utf-8")
            for change in ("text", "image", "structure"):
                names = {
                    Path(command[1]).name
                    for _, command in validate_all.deterministic_commands(
                        deck, deck.with_name("n.md"), deck.with_name("s.json"), "all",
                        content_changes=[change],
                    )
                }
                self.assertIn("validate_slide_variety.py", names, change)

    def test_the_placeholder_gate_blocks_a_visible_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            deck = Path(temporary) / "OUTPUT.html"
            deck.write_text(
                "<html><body>"
                '<section class="slide" data-title="One"><div class="slide-content">'
                "<h1>One</h1><p>PLACE NOTE: add the product photo here</p>"
                "</div></section></body></html>",
                encoding="utf-8",
            )
            result = run_script("validate_placeholders.py", str(deck))
            self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_record_review_cannot_pass_a_slide_with_a_failing_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "review.json"
            manifest.write_text(json.dumps({
                "review_batches": [{"id": "b1", "slides": [1], "status": "pending"}],
                "automation_gate": {"status": "pass", "checks": [], "failures": [], "warnings": []},
                "slides": [{
                    "slide": 1, "review_batch_id": "b1", "required_ai_profiles": ["normal"],
                    "inspected_profiles": [], "debug_captures": {},
                    "checks": {"crop": "pending", "text": "pending"}, "status": "pending",
                }],
            }), encoding="utf-8")
            result = run_script(
                "record_review.py", str(manifest), "slide", "--slide", "1",
                "--reviewer", "vr", "--reviewer-ref", "vr-01", "--status", "pass",
                "--inspected", "normal", "--check", "crop=pass", "--check", "text=fail",
                "--observation", "The caption overlaps the product photo along its lower edge.",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("status=pass requires every explicit check to pass", result.stderr)
            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8"))["slides"][0]["status"], "pending"
            )

    def test_machine_contract_owns_every_exact_validation_value(self) -> None:
        machine = machine_contract()
        self.assertEqual(machine["schema_version"], 13)
        self.assertEqual(machine["review_batch_size"], 4)
        self.assertEqual(machine["base_profiles"], ["normal", "short", "zoom150"])
        self.assertEqual(machine["impact_scopes"], ["direct", "neighbors", "full"])
        self.assertEqual(
            machine["content_change_categories"],
            ["text", "image", "structure", "style", "runtime"],
        )
        self.assertEqual(
            machine["cross_review_routes"],
            {"visual_critical": True, "automation_warning": True, "identity_required": True},
        )
        self.assertIn("font_integrity", machine["automation_checks_by_change"]["text"])
        self.assertIn("contrast", machine["automation_checks_by_change"]["text"])
        self.assertRegex(machine["playwright_version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(machine["slide_variety"]["skeleton_similarity_threshold"], 0.90)
        self.assertEqual(machine["slide_variety"]["minimum_structural_elements"], 8)

    def test_time_budgets_are_ceilings_the_documents_agree_with(self) -> None:
        budgets = machine_contract()["time_budgets"]
        self.assertEqual(budgets["full"]["total_minutes"], 70)
        self.assertEqual(budgets["quick"]["total_minutes"], 15)
        self.assertEqual(budgets["slide_range"], [20, 25])
        skill = read("SKILL.md")
        self.assertIn("Full Validation: 70 minutes for a 20-25 slide deck. Quick Draft: 15 minutes.", skill)
        self.assertIn("These are ceilings, not aspirations.", skill)
        # The plan table must stay inside the contract's per-phase ceilings.
        self.assertLessEqual(sum(budgets["full"]["phases"].values()), 70)

    def test_check_tuples_are_read_from_the_machine_contract_not_typed_by_hand(self) -> None:
        machine = machine_contract()["checks_by_change"]
        self.assertEqual(machine["all"][-3:], ["contrast", "density", "controls"])
        self.assertEqual(machine["text"], ["text", "text_bounds", "contrast", "density"])
        self.assertEqual(machine["navigation"], ["controls"])
        skill = read("SKILL.md")
        gates = read("references", "reviewer-gates.md")
        for scope, checks in machine.items():
            rendered = ", ".join(f"`{name}`" for name in checks)
            self.assertIn(rendered, skill, scope)
            self.assertIn(rendered, gates, scope)

    def test_the_recorder_enforces_the_tuple_exactly_and_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "review.json"
            manifest.write_text(json.dumps({
                "review_batches": [{"id": "b1", "slides": [1], "status": "pending"}],
                "automation_gate": {"status": "pass", "checks": [], "failures": [], "warnings": []},
                "slides": [{
                    "slide": 1, "review_batch_id": "b1", "required_ai_profiles": ["normal"],
                    "inspected_profiles": [], "debug_captures": {},
                    "checks": {"crop": "pending", "text": "pending"}, "status": "pending",
                }],
            }), encoding="utf-8")
            result = run_script(
                "record_review.py", str(manifest), "slide", "--slide", "1",
                "--reviewer", "vr", "--reviewer-ref", "vr-01", "--status", "pass",
                "--inspected", "normal", "--check", "crop=pass", "--check", "contrast=pass",
                "--observation", "The caption clears the navigation zone on the lower right.",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exactly once", result.stderr)

    def test_the_navigation_exclusion_zone_has_one_numeric_source(self) -> None:
        shell = read("assets", "runtime-shell.html")
        geometry = read("scripts", "measure_geometry.js")
        gates = read("references", "reviewer-gates.md")
        self.assertIn("--nav-exclusion-width: 280px", shell)
        self.assertIn("--nav-exclusion-height: 84px", shell)
        self.assertIn("NAV_EXCLUSION_FALLBACK_WIDTH", geometry)
        self.assertIn("--nav-exclusion-width", geometry)
        self.assertIn("280×84px", gates)
        self.assertIn(".nav-safe-note", shell)
        self.assertIn("data-nav-exclusion-ok", geometry)

    def test_the_runtime_shell_still_blocks_synthetic_weights(self) -> None:
        shell = read("assets", "runtime-shell.html")
        self.assertIn("font-synthesis: none", shell)
        for helper in (
            ".layout-hero", ".layout-split", ".layout-editorial",
            ".layout-columns", ".layout-gallery",
        ):
            self.assertIn(helper, shell)

    def test_every_gate_script_the_documents_name_exists_on_disk(self) -> None:
        for script in (
            "validate_placeholders.py", "validate_fonts.py", "validate_slide_variety.py",
            "record_review.py", "measure_contrast.js", "measure_geometry.js",
            "measure_image_geometry.js", "measure_text_bounds.js",
            "measure_container_density.js", "export_archify_asset.js",
        ):
            self.assertTrue((SCRIPTS / script).is_file(), script)


class DocumentedJudgmentTests(unittest.TestCase):
    """(b) Rules no machine can evaluate. Each test names the file that owns one."""

    def test_intake_resolves_audience_and_mode_together(self) -> None:
        # Owner: SKILL.md "Decide The Work Mode"; mirrored in validation-contract.md.
        skill = read("SKILL.md")
        contract = read("references", "validation-contract.md")
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

    def test_installation_always_needs_explicit_consent(self) -> None:
        # Owner: SKILL.md "Phase 0 - Preflight". Consent is not machine-checkable.
        skill = read("SKILL.md")
        contract = read("references", "validation-contract.md")
        self.assertIn("After the user chooses Full Validation", skill)
        self.assertIn("After the user chooses Full Validation", contract)
        self.assertIn("python3 scripts/check_environment.py", contract)
        self.assertIn("check_environment.py", skill)
        self.assertIn("Never run `npm install`", skill)
        self.assertIn("Do not run `npm install`", contract)
        self.assertIn("install_browser_dependencies.py", skill)
        self.assertIn("install_browser_dependencies.py --consent", contract)
        self.assertIn("Quick Draft is creation-only", contract)
        self.assertIn("accidental-call guard", contract)

    def test_quick_draft_uses_a_bounded_shared_authoring_path(self) -> None:
        # Owner: references/quick-draft-authoring.md.
        quick = read("references", "quick-draft-authoring.md")
        contract = read("references", "validation-contract.md")
        self.assertIn("four or five reusable composition families", quick)
        self.assertIn("never recreate the stage fitter", quick)
        self.assertIn("Do not write hundreds of lines of slide-specific CSS", quick)
        self.assertIn("15 minutes", contract)

    def test_large_area_palette_roles_require_provenance(self) -> None:
        # Owner: SKILL.md "Art Direction"; vocabulary in theme-playbook.md.
        self.assertIn("palette provenance", read("SKILL.md"))
        self.assertIn("Unsupported high-chroma colors", read("SKILL.md"))
        self.assertIn("Palette provenance and area", read("references", "theme-playbook.md"))
        self.assertIn("one-off high-chroma full-slide reset", read("references", "quality-bar.md"))
        self.assertIn("Large high-chroma surfaces", read("references", "visual-qa.md"))

    def test_identity_review_is_automatic_and_webp_grounded(self) -> None:
        # Owner: references/identity-review.md.
        identity = read("references", "identity-review.md")
        self.assertIn("automatically activated", read("SKILL.md"))
        self.assertIn("Omitting the slide flag does not bypass review", identity)
        self.assertIn("local WebP reference", identity)

    def test_placeholders_are_forbidden_in_the_deliverable(self) -> None:
        # Owner: SKILL.md "Asset Contract" item 12; the gate is tested behaviourally above.
        self.assertIn("Placeholders may exist only in the private authoring workspace", read("SKILL.md"))
        self.assertIn("One occurrence blocks delivery", read("references", "quality-bar.md"))

    def test_typography_is_chosen_without_a_separate_question(self) -> None:
        # Owner: references/style-presets.md.
        typography = read("references", "style-presets.md")
        self.assertIn("Choose the type system without asking a separate font question", typography)
        self.assertIn("Bundle a real bold/semibold face", typography)
        self.assertIn("every family actually used", typography)
        self.assertIn("Use only weights present", read("SKILL.md"))

    def test_review_recording_and_timings_are_documented(self) -> None:
        # Owner: references/validation-contract.md.
        for document in (read("SKILL.md"), read("references", "validation-contract.md")):
            self.assertIn("record_review.py", document)
            self.assertIn("--status", document)
            self.assertIn("timings.json", document)

    def test_refute_or_confirm_is_the_documented_adjudication(self) -> None:
        # Owner: references/reviewer-gates.md; both reviewer agents cite it.
        gates = read("references", "reviewer-gates.md")
        self.assertIn("refute-or-confirm", gates)
        self.assertIn("CONFIRM: ", gates)
        self.assertIn("REFUTE: ", gates)
        self.assertIn("slide-NN-debug.png", gates)
        for agent in ("build-html-slides-visual-reviewer.md", "build-html-slides-quality-editor.md"):
            body = (AGENTS / agent).read_text(encoding="utf-8")
            self.assertIn("`CONFIRM: `", body)
            self.assertIn("`REFUTE: `", body)
            self.assertIn("slide-NN-debug.png", body)

    def test_alt_text_and_contrast_obligations_remain_stated(self) -> None:
        # Owner: SKILL.md "Art Direction" (alt text) and references/visual-qa.md (contrast).
        visual = read("references", "visual-qa.md")
        self.assertIn("missing alt text blocks Full Validation", read("SKILL.md"))
        self.assertIn("4.5:1", visual)
        self.assertIn("3:1", visual)

    def test_unfamiliar_term_notes_are_semantic_audience_aware_and_sparse(self) -> None:
        # Owner: references/audience-story-routing.md.
        audience = read("references", "audience-story-routing.md")
        self.assertIn("semantic terminology burden list", read("SKILL.md"))
        self.assertIn("Do not run a keyword, acronym, capitalization, or frequency parser", audience)
        self.assertIn("first meaningful occurrence", audience)
        self.assertIn("NXT컨소시엄", audience)
        self.assertIn("KDX", audience)
        self.assertIn("One or two notes on a slide is normally enough", audience)
        self.assertIn("용어 — 이 발표에서 뜻하는 역할", read("references", "korean-copy.md"))
        self.assertIn("Decision-critical unfamiliar terms", read("references", "visual-qa.md"))
        self.assertIn("unnecessary glossary notes", read("references", "quality-bar.md"))

    def test_term_notes_are_micro_annotations_and_source_classes_are_reserved(self) -> None:
        # Owner: SKILL.md "Story And Copy"; the size rule is measured by the density gate.
        skill = read("SKILL.md")
        self.assertIn("data-term-note", skill)
        self.assertIn("data-source-citation", skill)
        self.assertIn("never as a large card", skill)
        self.assertIn("no large white card", read("references", "audience-story-routing.md"))
        self.assertIn("audience term notes: typically 10–12px", read("references", "style-presets.md"))
        self.assertIn("large annotation card", read("references", "visual-qa.md"))
        density = read("scripts", "measure_container_density.js")
        self.assertIn("term note must remain a compact caption", density)

    def test_incremental_scopes_do_not_drop_independent_review(self) -> None:
        # Owner: references/validation-contract.md.
        contract = read("references", "validation-contract.md")
        self.assertIn("**Direct impact:**", contract)
        self.assertIn("**Neighbor impact:**", contract)
        self.assertIn("**Full impact:**", contract)
        self.assertIn("valid independent cross-reviews", contract)
        self.assertIn("data-slide-scope", read("SKILL.md"))
        self.assertIn("Focus that loop on the failed slide and check family",
                      read("references", "slide-by-slide-review.md"))

    def test_theme_routing_is_semantic_not_topic_noun_driven(self) -> None:
        # Owner: references/theme-playbook.md; theme-gallery.md is vocabulary only.
        playbook = read("references", "theme-playbook.md")
        gallery = read("references", "theme-gallery.md")
        skill = read("SKILL.md")
        self.assertIn("Technology is a subject domain, not a visual theme", playbook)
        self.assertIn(
            "A dark-led system, a paper-led system, and an image-led system are equally valid",
            playbook,
        )
        self.assertIn("Do not select Field Notes merely because the subject is travel", playbook)
        self.assertIn("do not select it merely because an idol appears", playbook)
        self.assertIn("### Travel routing", playbook)
        self.assertIn("Japanese travel does not automatically mean dark green", playbook)
        self.assertIn("ordinary leisure guides default to Destination Magazine", skill)
        self.assertIn("evidence-led schematic direction", skill)
        self.assertIn("Dark-led directions remain valid", skill)
        self.assertIn("## 7. Destination Magazine", gallery)
        self.assertIn("## 21. Idol Editorial Index", gallery)
        self.assertIn("## 22. Paper Systems", gallery)
        self.assertIn("## 23. Interface Lab", gallery)
        self.assertIn("## 24. Human Infrastructure", gallery)
        self.assertIn("not presets or a closed taxonomy", gallery)

    def test_contemporary_art_direction_rejects_pale_card_walls(self) -> None:
        # Owner: SKILL.md "Art Direction"; quality-bar.md holds the review phrasing.
        skill = read("SKILL.md")
        self.assertIn("Paper Systems is one candidate, not the corrective default", skill)
        self.assertIn("pale report with repeated top-title-plus-card rows", skill)
        self.assertIn("roughly one third of body slides", skill)
        self.assertIn("Different panel counts still count as the same composition",
                      read("references", "quality-bar.md"))
        self.assertIn("Darkness itself is not a failure", read("references", "quality-bar.md"))
        self.assertIn("dark-console fingerprint", read("references", "visual-qa.md"))
        self.assertIn("same family, width, and texture", read("references", "style-presets.md"))
        self.assertIn("contemporary editorial", read("references", "design-candidate-search.md"))
        self.assertIn("one rounded sans for every role", read("references", "theme-playbook.md"))
        editor = (AGENTS / "build-html-slides-quality-editor.md").read_text(encoding="utf-8")
        self.assertIn("different card counts are not layout rhythm", editor.lower())

    def test_companions_are_routed_automatically_and_never_installed_silently(self) -> None:
        # Owner: SKILL.md "Companion Skill Routing".
        skill = read("SKILL.md")
        architecture = read("references", "architecture-diagrams.md")
        self.assertIn("## Companion Skill Routing", skill)
        self.assertIn("If `humanize-korean` is available", skill)
        self.assertIn("Bundled distributions include `archify`", skill)
        self.assertIn("without waiting for a separate request", skill)
        self.assertIn("Availability is sufficient consent", skill)
        self.assertIn("Do not ask whether to use an available", skill)
        self.assertIn("never install software during deck work", skill)
        self.assertIn("Do not load its full instructions during ordinary deck planning", skill)
        self.assertIn("Technical vocabulary alone is never sufficient", skill)
        self.assertIn("skip Archify entirely", skill)
        self.assertIn("Supported distributions bundle `archify`", architecture)
        self.assertIn("Do not implement a keyword, substring, regex, quota", architecture)
        self.assertIn("export_archify_asset.js", architecture)
        self.assertIn("self-contained HTML output", architecture)
        self.assertIn("one pure SVG plus an exact-size WebP", architecture)

    def test_bundled_archify_examples_stay_in_sync(self) -> None:
        # Owner: codex/skills/archify/SKILL.md.
        archify = (ROOT.parent / "archify" / "SKILL.md").read_text(encoding="utf-8")
        utils = (ROOT.parent / "archify" / "renderers" / "shared" / "utils.mjs").read_text(encoding="utf-8")
        for stale in (
            "archify-repo.architecture.json",
            "maka-architecture.architecture.json",
            "archify-repo-grid.architecture.json",
            "examples/web-app.html",
        ):
            self.assertNotIn(stale, archify)
        self.assertIn("examples/web-app.architecture.json", archify)
        self.assertIn("examples/production-deployment.architecture.json", archify)
        self.assertIn("examples/web-app-rendered.html", archify)
        self.assertIn('data-theme="light"', utils)

    def test_relevant_photography_is_the_default(self) -> None:
        # Owner: references/media-strategy.md.
        media = read("references", "media-strategy.md")
        self.assertIn("pure-HTML, image-free, or typography/diagram-only", read("SKILL.md"))
        self.assertIn("perform a bounded search for relevant sourced photographs", media)
        self.assertIn("This is a relevance rule, not an image quota", media)
        self.assertIn("omit them when they add no information", read("references", "quality-bar.md"))

    def test_physical_subjects_keep_real_world_or_scientific_imagery(self) -> None:
        # Owner: references/media-strategy.md.
        media = read("references", "media-strategy.md")
        skill = read("SKILL.md")
        self.assertIn(
            "Full Validation controls assurance depth, not research breadth, art direction, "
            "or visual-media variety",
            skill,
        )
        self.assertIn("## Classify the visual job semantically", media)
        self.assertIn("AI-driven semiconductor market change", media)
        self.assertIn("Cancer treatment research and development", media)
        self.assertIn("four to eight distinct sourced visual anchors", media)
        self.assertIn("must not remove useful subject imagery", read("references", "quality-bar.md"))

    def test_visuals_are_selected_by_claim_contribution(self) -> None:
        # Owner: references/media-strategy.md "Require a visual contribution".
        media = read("references", "media-strategy.md")
        self.assertIn("evidence, identity, mechanism, concept, or atmosphere", read("SKILL.md"))
        self.assertIn("## Require a visual contribution", media)
        self.assertIn("stock substitution test", media)
        self.assertIn("Financial education or fintech explainer", media)
        self.assertIn("generated concept illustration", read("references", "image-generation.md"))
        self.assertIn("interchangeable stock photography", read("references", "quick-draft-authoring.md"))
        self.assertIn("Generic stock photography occupies main explanatory space",
                      read("references", "quality-bar.md"))
        self.assertIn("Every main visual has a legible job", read("references", "visual-qa.md"))
        for agent in ("build-html-slides-visual-reviewer.md", "build-html-slides-quality-editor.md"):
            self.assertIn("## Media Contribution Gate", (AGENTS / agent).read_text(encoding="utf-8"))

    def test_cover_is_a_first_class_design_and_review_contract(self) -> None:
        # Owner: references/cover-design.md.
        cover = read("references", "cover-design.md")
        self.assertIn("references/cover-design.md", read("SKILL.md"))
        self.assertIn("highest-priority art-direction decision", cover)
        self.assertIn("at least two materially different cover directions", cover)
        self.assertIn("cover and closing are always visual-critical", read("references", "validation-contract.md"))
        self.assertIn("merely acceptable cover", read("references", "quality-bar.md"))
        reviewer = (AGENTS / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("For slide 1, apply `cover-design.md`", reviewer)

    def test_existing_subjects_use_authentic_media(self) -> None:
        # Owner: references/image-generation.md.
        generation = read("references", "image-generation.md")
        skill = read("SKILL.md")
        self.assertIn("generated art must never stand in for the real subject", skill)
        self.assertIn("data-media-purpose", skill)
        self.assertIn("fourth-generation girl-group introduction", generation)
        self.assertIn("1990s-2000s game retrospective", generation)
        self.assertIn("authentic sourced identity anchor", generation)
        self.assertIn("Existing entertainment catalog or nostalgia retrospective",
                      read("references", "media-strategy.md"))
        self.assertIn("dedicated refinement pass", read("references", "cover-design.md"))
        reviewer = (AGENTS / "build-html-slides-visual-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("generated-only depiction of an existing named subject", reviewer)

    def test_high_volume_sourced_media_has_a_numeric_trigger(self) -> None:
        # Owner: references/high-volume-media-workflow.md.
        workflow = read("references", "high-volume-media-workflow.md")
        self.assertIn("references/high-volume-media-workflow.md", read("SKILL.md"))
        self.assertIn("Deep-research and regenerate only flagged candidates", read("SKILL.md"))
        self.assertIn("## 1. Freeze a media roster", workflow)
        self.assertIn("up to twelve", workflow)
        self.assertIn("12 or more", workflow)
        self.assertIn("products, food, artworks, athletes", workflow)
        self.assertIn("Quick Draft", workflow)
        self.assertIn("Full Validation", workflow)
        self.assertIn("duplicate_hashes", read("scripts", "build_media_contact_sheet.js"))

    def test_prompt_residue_stays_private_and_notes_clear_the_navigation_zone(self) -> None:
        # Owner: SKILL.md "Story And Copy"; the zone itself is measured, not argued.
        skill = read("SKILL.md")
        self.assertIn("Separate private authoring constraints", skill)
        self.assertIn("lower-right navigation exclusion zone", skill)
        self.assertIn("The authoring brief is private", read("references", "cover-design.md"))
        self.assertIn("Separate authoring instructions from audience copy",
                      read("references", "audience-story-routing.md"))
        self.assertIn("제작 프롬프트를 화면 문구로 옮기지 않기", read("references", "korean-copy.md"))
        self.assertIn("개념 강의 + 팀 활동", read("references", "quick-draft-authoring.md"))
        self.assertIn("280×84px", read("references", "style-presets.md"))
        self.assertIn("lower-right navigation exclusion zone", read("references", "visual-qa.md"))
        for agent in ("build-html-slides-visual-reviewer.md", "build-html-slides-quality-editor.md"):
            self.assertIn("## Prompt Residue Gate", (AGENTS / agent).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
