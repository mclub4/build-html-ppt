# Validation Contract

This file defines validation semantics. `scripts/validation_contract.json` is the machine-readable authority for the schema version, exact profile geometry, check sets, batch size, managed Playwright version, and standard cross-review sampling values. Scripts and tests must read that JSON rather than duplicate those values.

## Choose By Intent

New-presentation creation resolves audience and validation mode before work begins. If either is absent, ask every unresolved intake question in one opening message and stop before research, drafting, file creation, or asset generation. For Korean interaction, label the choices `빠른 검증 (Quick Draft)` and `정밀 검증 (Full Validation)` and state that the former is creation-only with no rendered validation. The user must choose a mode explicitly. Audience choices may include a domain team, company-wide concept sharing, executives, clients, or newcomers. If the user delegates audience choice with `청중은 알아서 해줘`, assume a general company-wide concept-sharing audience with mixed domain familiarity. Do not ask again for information already supplied, and do not split audience and mode questions across separate turns. Recognize answers from meaning and context rather than a keyword list, regular expression, or substring heuristic.

| Mode | Use when | New evidence |
| --- | --- | --- |
| Edit Only | The user primarily wants an ordinary revision and does not seek new assurance | None |
| 빠른 검증 (Quick Draft) | The user prioritizes iteration or a first usable version | None; creation only |
| 정밀 검증 (Full Validation) | The presentation is intended for delivery, publication, or a consequential decision, or strong assurance is requested | Automated geometry and AI review for every slide, independent review, final score |

Edit Only applies to an existing deck revision when the user asks for a change without requesting new validation evidence. It is not a substitute for asking the required new-deck mode question.

## Tool Preflight And Installation Consent

After the user chooses Full Validation, run this preflight before substantive work:

```bash
python3 scripts/check_environment.py
```

The script checks Python, Node.js, Playwright, Chromium, and screenshot capture without installing anything. If it fails, report the exact missing or incompatible components and ask whether the user wants them installed. Stop until the user gives explicit consent unless that consent was already part of the request. Do not run `npm install`, `npx playwright install`, an OS package manager, or elevated installation commands first. After approval, prefer the bundled user-scoped installer:

```bash
python3 scripts/install_browser_dependencies.py --consent
```

It installs the contract-pinned Playwright package and Chromium under `~/.build-html-slides/runtime`. Use `--with-deps` only when the user also approved Linux system-library installation, which may require elevated privileges. After installation, rerun the preflight. Do not begin Full Validation until it passes. Quick Draft skips this preflight because it performs no browser rendering or validation.

## Turnaround Envelope

Full Validation controls review depth, not research breadth, art direction, or media variety. It must not simplify an image-worthy physical, industrial, product, or research subject into a report made only of text, charts, tables, and generic SVGs.

**Full Validation: 70 minutes maximum for a 20-25 slide deck, settled brief to validated delivery. Quick Draft: 15 minutes maximum.** These are ceilings, not aspirations. `scripts/validation_contract.json` carries the same numbers under `time_budgets`, and `validate_all.py --status` prints them:

```text
BUDGET: full validation elapsed 41.3 min of 70 min for 22 slides - 28.7 min remaining
BUDGET: next step 'primary-review' is budgeted at 25 min
```

The printed clock starts at the first `validate_all.py` invocation, so research and authoring occupy the unmeasured head of the same 70 minutes; keep them under 20. The per-phase figures — `prepare` 15, `primary-review` 25, `verify` 3, `finalize-prepare` 5, `final-review` 18, `finalize-verify` 4 — are worst-case ceilings for one phase, not an addition sum to spend. A deck above 25 slides scales the allowance proportionally; a deck at or below 25 does not.

### Autonomous budget checkpoint

At 70% of the allowance, or as soon as `--status` reports under 20 minutes remaining, act without asking the user:

1. freeze asset discovery and use the candidates already downloaded;
2. drop `--responsive` and any exploratory profile;
3. keep cross-review to the generated pending batches only;
4. restrict the fix loop to slides with an open issue, warning, or reviewer `fail`;
5. finish and deliver, stating in the delivery summary what was reduced.

When `validate_all.py` prints `BUDGET: over budget - stop widening scope, finish the pending step, and reduce optional profiles or cross-review sampling on the next deck`, stop widening scope immediately. Do not ask whether to continue; a budget question spends the budget. Only a defect that would block delivery — a non-negotiable gate in `reviewer-gates.md` — may push past the ceiling, and it is reported as an overrun with its cause.

For fan-art-heavy, image-collection, or "as many as possible" requests, `fan-art-budget.md` is mandatory and its targets sit inside this same 70 minutes. Do not add auxiliary source or per-image review agents in ordinary internal/private mode.

## Validation Workspace

Review evidence and temporary authoring files are internal working data, not presentation deliverables. By default, the renderer stores the latest evidence for each deck at:

```text
<agent-home>/build-html-slides/workspaces/<deck-id>/review/
```

Use `node scripts/render_slides.js --workspace-dir OUTPUT.html` to resolve the parent workspace. Store copy drafts in `drafts/` and contact sheets or disposable transforms in `tmp/`. Do not create these files beside the final HTML. Codex defaults to `~/.codex`; Claude Code defaults to `~/.claude`; Gemini CLI defaults to `~/.gemini`. `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `CLAUDE_HOME`, `GEMINI_HOME`, or `BUILD_HTML_SLIDES_AGENT_HOME` relocates the matching agent home; `BUILD_HTML_SLIDES_WORKSPACE_ROOT` overrides the workspace root directly.

The deck ID combines a readable filename with a hash of the absolute deck path, so decks with the same name do not collide. A full render replaces that deck's prior review directory; incremental renders reuse it. An explicit positional `REVIEW_DIR` remains supported for integrations.

After evidence is no longer needed, remove the default workspace with `node scripts/render_slides.js --clean-workspace OUTPUT.html`. Do not remove it before validation or while incremental revisions are expected.

## Canonical Profiles

Full Validation captures every slide at:

- `normal`: 1920×1080 viewport and screenshot, zoom 1;
- `short`: 1366×650 viewport and screenshot, zoom 1;
- `zoom150`: 1920×1080 layout viewport with Chromium page scale 1.5, a measured 1280×720 `visualViewport`, and a 1920×1080 screenshot. This is a browser zoom stress test, not a DPR-only capture.

Add `tablet` 1024×768 and `mobile` 390×844 only when responsive device support is requested. Additional exploratory sizes supplement rather than replace canonical evidence.

## Quick Draft

Quick Draft is creation-only. Build the final HTML, sibling presenter notes, `sources.json`, and locally referenced assets, then deliver them without entering the validation pipeline.

Do not run `check_environment.py`, install Playwright or Chromium, invoke validation, open a browser, render screenshots, create a review workspace, execute deterministic gates, request AI visual inspection, calculate the 24-point score, or run independent cross-review. `validate_all.py --mode quick` exists only as an accidental-call guard and exits successfully before any preflight, render, validator, timing file, or review directory is created. Do not claim clipping, crop, interaction, identity, placeholder, font, or visual-quality assurance. Report explicitly that the deck was not rendered or validated. A later request may upgrade the same deck to Full Validation.

Quick Draft delivers in 15 minutes maximum for an ordinary 10-15 slide presentation. That is a ceiling. Follow `quick-draft-authoring.md`: copy the runtime shell, freeze shared tokens once, use four or five reusable composition families, limit bespoke treatment to the cover, closing, and at most two signature slides, bound ordinary image discovery, keep notes concise, and perform at most one combined Korean polishing pass after copy settles. Do not spend the saved validation time rebuilding every slide as a separate CSS system.

## Full Validation

The initial Full preparation runs the complete deterministic suite and Chromium geometry checks. The placeholder gate therefore runs once for every new or edited source before AI review and blocks `PLACE NOTE`, image-here instructions, dummy asset markers, CSS-generated placeholder copy, and other explicit unfinished media. `validate_slide_variety.py` runs once per deck on text, image, and structure changes and blocks a near-duplicate slide pair. Later edits run only gates that the typed change can affect. AI inspects `normal` for every refreshed slide and records `completion` for all/image scope.

Every slide/profile that produced at least one measured issue or warning also receives a boundary overlay capture at `review/<profile>/slide-NN-debug.png`, recorded at `captures.<profile>.debug_overlay` and `records[N].debug_captures.<profile>`. It draws the resolved containers, image boxes, text-line ink boxes, the reserved navigation zone, and the overflow or intersection region that caused the finding. Hand it to the reviewer with the warning text; a warned slide is adjudicated by the refute-or-confirm protocol in `reviewer-gates.md`, not by an ordinary pass. `short`, `zoom150`, tablet, and mobile remain automated geometry evidence for ordinary slides; AI opens those stress profiles only when the slide is visual-critical or that profile produced a warning. Any visible placeholder, empty media promise, or generic substitute for an expected real subject image blocks delivery regardless of the final quality score. The cover and closing are always visual-critical.

Choose review risk by reasoning about consequences, uncertainty, distribution, technical complexity, visual complexity, and audience sensitivity:

- `standard`: two primary visual reviewers;
- `high`: three primary visual reviewers.

Pass the decision to the renderer with `--review-risk standard|high`. Assign contiguous slide ranges. Vision batches contain at most four slides, independent of reviewer range size.

After fixes settle, run `--phase finalize-prepare`. This verifies iteration metadata, confirms the current source fingerprint, then generates the one quality-score record, bounded `cross_review_batches`, and a downscaled, lightly blurred squint contact sheet from the settled `normal` captures. It does not rerender slides. Assign an independent presentation editor and calculate the quality score once. The same editor inspects the squint sheet once for focal hierarchy, emphasis range, deck rhythm, and color/density balance, and records one concrete observation. Squint review cannot prove text overlap, line-break quality, crop, distortion, or overflow; those remain full-size responsibilities. Use the squint overview to identify weak or ambiguous slides for the quality notes. Cross-review membership is generated, never inferred: `required_cross_review_slides()` in `validate_visual_review.py` returns the union of visual-critical slides, identity-required slides, and automation-warning slides, and it does not read the review-risk argument at all. Complete exactly the generated pending batches and mark each finished batch `complete`. Do not add distributed ordinary-slide samples, and do not expand high-risk cross-review to every slide; high risk raises primary reviewer diversity instead. Every cross-reviewer must be outside the complete primary-reviewer set, not merely different from the primary reviewer assigned to that slide, and must enter with the cross-review lens in `reviewer-gates.md` rather than the primary checklist a second time. After a focused fix, passing cross-reviews for unchanged captures remain reusable only when their capture hashes, required profiles, checks, and reviewer independence still match; the changed or failed slides receive new cross-review records.

Delivery is blocked by any of: a deterministic issue, a deterministic warning with no `CONFIRM` or `REFUTE` observation on record, a reviewer `fail` in any primary or cross-review record, a quality score below 20/24 or any dimension below 2, or any non-negotiable gate in `reviewer-gates.md`. There is no severity taxonomy; neither reviewer emits one.

## Commands

Full Validation preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --review-risk standard --phase prepare
```

After filling the listed AI batches, run `python3 scripts/validate_all.py OUTPUT.html --phase verify`, then run `--phase finalize-prepare`, inspect and record the generated `squint_review`, generated quality score, and `cross_review_batches`, and run `--phase finalize-verify`. Use `python3 scripts/validate_all.py OUTPUT.html --status` at any point to list pending batches, the appropriate `record_review.py` subcommand, the latest recorded duration, and the next validation phase. `record_review.py` accepts only explicit reviewer observations and complete check sets; it does not inspect images or generate PASS verdicts. `prepare` executes change-relevant deterministic gates and rendering; `verify` checks refreshed captures and any previously blocked captures entering AI review, while other retained evidence receives metadata checks only; `finalize-prepare` performs the one settled Chromium source-fingerprint confirmation and prepares final records plus the squint artifact without rerendering slides; `finalize-verify` checks every capture hash plus HTML/local-file freshness without recomputing the same browser fingerprint. Use `--responsive` only for requested tablet/mobile support. Every Full Validation phase appends command-level durations to `review/timings.json`, and `--status` reports elapsed time against the 70-minute allowance plus the next phase's ceiling. Treat both as binding and apply the autonomous budget checkpoint above when the remainder runs short.

Full Validation requires the display, body, and mono families actually used by visible slide text to resolve to local redistribution-compatible WOFF2 files inside the deck bundle. The renderer records computed family/weight usage in `review.json`; declared fonts with no loaded matching face and platform/system fallbacks fail portability assurance. Meaningful images require non-empty alt text.

`measure_contrast.js` no longer defers a whole class of backdrops. It walks the real paint stack under each text line, samples image pixels, bounds gradient stops componentwise, composites scrims, and bounds anything still unknown by pure black and pure white, producing a provable `[worst, best]` contrast interval against the required 4.5:1 for body text and 3:1 for large text. `worst >= required` passes silently and `best < required` blocks with `…: text contrast is at most N:1 against every backdrop this text can sit on`. Only an interval that straddles the requirement reaches a reviewer, as an `UNDECIDABLE contrast` warning that names the cause, the measured range, the sample count, and the worst point, and that ends with `Reviewer MUST open the full-size capture and either CONFIRM or REFUTE this overlap with a location-specific observation naming what sits behind the text at that position; "looks fine", "intentional", or a restatement of this warning is not an accepted answer.` Answer it exactly that way.

## Incremental Revision

After the initial render, ordinary revisions may run `prepare` without `--slides`. When a current review manifest exists, `validate_all.py` always compares the new source fingerprints first and automatically supplies the directly changed slide set to the renderer. Use an explicit `--slides` hint when the intended edit scope is already known or when recovering a failed slide:

```bash
python3 scripts/validate_all.py OUTPUT.html --phase prepare \
  --mode full --review-risk standard|high \
  --slides N --change-type text|image|navigation|all
```

`--change-type` is a performance hint, not trusted proof. Before choosing validators, `validate_all.py` compares typed per-slide text, media, structure, slide-local style, shared-style, runtime, linked-source, and local-asset fingerprints. It uses the actual detected type even when the hint was broader or wrong.

- **Direct impact:** pure copy, image, title, or slide-local CSS changes refresh the requested and actually changed slides only. A CSS rule that matches a finite subset of slides refreshes that subset.
- **Neighbor impact:** structure, order, transition, or adjacency-sensitive changes refresh affected slides plus immediate neighbors.
- **Full impact:** shared CSS that affects the whole deck, dynamic active-state selectors, runtime/navigation code, profile set, mode, review risk, slide-count changes, or unsafe deck-wide dependencies refresh every slide.

Linked and embedded CSS is read through Chromium CSSOM and attributed to the slide containing each actually matched element, including selectors rooted at a slide ID or `data-*` attribute. CSS background assets and inline-style assets inherit the same scope. For complex selectors, pseudo-elements, or rules prepared before their target markup exists, declare the dependency explicitly with `<style data-slide-scope="N">`. Keep shared theme/runtime rules in ordinary shared style blocks; do not create one CSS file per slide. The classifier cache is reused by the renderer only while the deck and every tracked local file retain the same size, mtime, and ctime.

Run checks by change type:

| Change | AI check tuple, in contract order | Deterministic gates |
| --- | --- | --- |
| Text | text, text_bounds, contrast, density | text_bounds, font_integrity, contrast, container_density |
| Image | crop, aspect_ratio, resolution, content_match, completion | image_geometry |
| Navigation | controls | controls |
| Mixed/global | crop, aspect_ratio, resolution, content_match, completion, overflow, occlusion, text, text_bounds, contrast, density, controls | text_bounds, font_integrity, contrast, container_density, controls, image_geometry |

Text, image, and structure changes also run the deck-level `validate_slide_variety.py` gate. `reviewer-gates.md` holds the same tuples with the reason each check exists; `scripts/validation_contract.json` is the machine authority and the validator compares the recorded tuple exactly and order-sensitively.

Do not recalculate the quality score during the fix loop. Full Validation scores only after the settled final render. A failed automated check blocks AI review; after repair, rerun only the failed/changed slide scope and relevant geometry family. When a prior manifest contains slide-specific automation, primary-review, cross-review, or quality failures and the HTML changed, `validate_all.py --phase prepare --mode full` automatically scopes an omitted `--slides` argument to those failed slides. Typed source classification still widens adjacency, shared CSS, runtime, profile, or deck-wide changes when required. A failed primary or cross-review verdict requires a new capture and inspection for the implicated slide, but does not invalidate unrelated current captures or valid independent cross-reviews.

Any reviewer FAIL is monotonic for that render: do not rewrite it to PASS. Fix the deck, rerun `prepare`, inspect the new capture hashes, and record a new verdict. A shared CSS, runtime, or layout-family edit invalidates every affected slide review; do not preserve or reconstruct old observations. Review JSON is evidence output, not a checklist to complete programmatically.

## Evidence Meaning

The manifest proves that captures came from the current HTML/local assets, match canonical profiles, passed deterministic geometry, and are bound to review records. Reviewer labels and observations remain agent-provided records; do not describe them as cryptographic proof that a particular model or person opened the files.

## Delivery Language

- Edit Only: state that no new render or validation was performed.
- Quick Draft: state that no browser render, automated validation, AI visual review, or quality score was performed.
- Full Validation: report review risk, reviewer count, AI coverage, final score, and any limitation.

Never report stale captures as current evidence or imply a broader validation scope than was performed.
