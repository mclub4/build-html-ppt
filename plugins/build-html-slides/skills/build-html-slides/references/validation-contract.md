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

Full Validation controls review depth, not research breadth, art direction, or media variety. It must not simplify an image-worthy physical, industrial, product, or research subject into a report made only of text, charts, tables, and generic SVGs. For a 20-25 slide deck, target 40-90 minutes from settled brief to validated delivery. Ordinary decks should stay near the lower half; image-heavy decks use the upper half. Reserve the final 25-35 minutes for settled rendering, batched AI inspection, focused fixes, one final score, and required cross-review. These are planning targets, not a forced process timeout.

For fan-art-heavy, image-collection, or "as many as possible" requests, `fan-art-budget.md` is mandatory. Check progress around 30-40 minutes or 40-50 candidates. Freeze a strong set when coverage is sufficient; continue only when the expected improvement justifies the remaining validation time. If the work is likely to exceed 90 minutes, explain the cause and ask whether to freeze the current set or continue. Do not add auxiliary source or per-image review agents in ordinary internal/private mode.

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

For an ordinary 10-15 slide presentation, target roughly 10-20 minutes under normal local conditions. This is a planning target, not a timeout. Follow `quick-draft-authoring.md`: copy the runtime shell, freeze shared tokens once, use four or five reusable composition families, limit bespoke treatment to the cover, closing, and at most two signature slides, bound ordinary image discovery, keep notes concise, and perform at most one combined Korean polishing pass after copy settles. Do not spend the saved validation time rebuilding every slide as a separate CSS system.

## Full Validation

The initial Full preparation runs the complete deterministic suite and Chromium geometry checks. The placeholder gate therefore runs once for every new or edited source before AI review and blocks `PLACE NOTE`, image-here instructions, dummy asset markers, CSS-generated placeholder copy, and other explicit unfinished media. Later edits run only gates that the typed change can affect. AI inspects `normal` for every refreshed slide and records `completion` for all/image scope. `short`, `zoom150`, tablet, and mobile remain automated geometry evidence for ordinary slides; AI opens those stress profiles only when the slide is visual-critical or that profile produced a warning. Any visible placeholder, empty media promise, or generic substitute for an expected real subject image blocks delivery regardless of the final quality score. The cover and closing are always visual-critical.

Choose review risk by reasoning about consequences, uncertainty, distribution, technical complexity, visual complexity, and audience sensitivity:

- `standard`: two primary visual reviewers;
- `high`: three primary visual reviewers.

Pass the decision to the renderer with `--review-risk standard|high`. Assign contiguous slide ranges. Vision batches contain at most four slides, independent of reviewer range size.

After fixes settle, run `--phase finalize-prepare`. This verifies iteration metadata, confirms the current source fingerprint, then generates the one quality-score record, bounded `cross_review_batches`, and a downscaled, lightly blurred squint contact sheet from the settled `normal` captures. It does not rerender slides. Assign an independent presentation editor and calculate the quality score once. The same editor inspects the squint sheet once for focal hierarchy, emphasis range, deck rhythm, and color/density balance, and records one concrete observation. Squint review cannot prove text overlap, line-break quality, crop, distortion, or overflow; those remain full-size responsibilities. Use the squint overview to identify weak or ambiguous slides for the quality notes, but keep mandatory independent full-size cross-review focused on the cover, closing, explicit visual-critical/core slides, automation-warning slides, and identity-sensitive slides. Do not add distributed ordinary-slide samples, and do not expand high-risk cross-review to every slide; high risk already raises primary reviewer diversity. Every cross-reviewer must be outside the complete primary-reviewer set, not merely different from the primary reviewer assigned to that slide. This remains intentional independent cross-validation, not a duplicate full-deck inspection. After a focused fix, passing cross-reviews for unchanged captures remain reusable only when their capture hashes, required profiles, checks, and reviewer independence still match; the changed or failed slides receive new cross-review records. Unresolved high/medium findings or a failing score block delivery.

## Commands

Full Validation preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --review-risk standard --phase prepare
```

After filling the listed AI batches, run `python3 scripts/validate_all.py OUTPUT.html --phase verify`, then run `--phase finalize-prepare`, inspect and record the generated `squint_review`, generated quality score, and `cross_review_batches`, and run `--phase finalize-verify`. Use `python3 scripts/validate_all.py OUTPUT.html --status` at any point to list pending batches, the appropriate `record_review.py` subcommand, the latest recorded duration, and the next validation phase. `record_review.py` accepts only explicit reviewer observations and complete check sets; it does not inspect images or generate PASS verdicts. `prepare` executes change-relevant deterministic gates and rendering; `verify` checks refreshed captures and any previously blocked captures entering AI review, while other retained evidence receives metadata checks only; `finalize-prepare` performs the one settled Chromium source-fingerprint confirmation and prepares final records plus the squint artifact without rerendering slides; `finalize-verify` checks every capture hash plus HTML/local-file freshness without recomputing the same browser fingerprint. Use `--responsive` only for requested tablet/mobile support. Every Full Validation phase appends command-level durations to `review/timings.json`; this diagnoses slow research/render/review loops but imposes no hard stop.

Full Validation requires the display, body, and mono families actually used by visible slide text to resolve to local redistribution-compatible WOFF2 files inside the deck bundle. The renderer records computed family/weight usage in `review.json`; declared fonts with no loaded matching face and platform/system fallbacks fail portability assurance. Meaningful images require non-empty alt text. Solid-background text receives automatic WCAG contrast checks at 4.5:1 for body text and 3:1 for large text; image, gradient, transparency, blend, and unresolved overlapping-media cases remain explicit full-size AI contrast checks.

## Incremental Revision

After the initial render, use:

```bash
python3 scripts/validate_all.py OUTPUT.html --phase prepare \
  --mode full --review-risk standard|high \
  --slides N --change-type text|image|navigation|all
```

`--change-type` is a performance hint, not trusted proof. Before choosing validators, `validate_all.py` compares typed per-slide text, media, structure, slide-local style, shared-style, runtime, linked-source, and local-asset fingerprints. It uses the actual detected type even when the hint was broader or wrong.

- **Direct impact:** pure copy, image, title, or slide-local CSS changes refresh the requested and actually changed slides only. A CSS rule that matches a finite subset of slides refreshes that subset.
- **Neighbor impact:** structure, order, transition, or adjacency-sensitive changes refresh affected slides plus immediate neighbors.
- **Full impact:** shared CSS that affects the whole deck, dynamic active-state selectors, runtime/navigation code, profile set, mode, review risk, slide-count changes, or unsafe deck-wide dependencies refresh every slide.

Linked CSS is read through Chromium CSSOM and attributed to matching slides when possible. CSS background assets and inline-style assets inherit the same scope. Authors may also declare isolated rules with `<style data-slide-scope="N">`. The classifier cache is reused by the renderer only while the deck and every tracked local file retain the same size, mtime, and ctime.

Run checks by change type:

| Change | Automated and AI scope |
| --- | --- |
| Text | text, text bounds, and container density |
| Image | crop, aspect ratio, resolution, content match, and completion |
| Navigation | controls and interaction |
| Mixed/global | all checks |

Do not recalculate the quality score during the fix loop. Full Validation scores only after the settled final render. A failed automated check blocks AI review; after repair, rerun only the failed/changed slide scope and relevant geometry family. When a prior manifest contains slide-specific automation, primary-review, cross-review, or quality failures and the HTML changed, `validate_all.py --phase prepare --mode full` automatically scopes an omitted `--slides` argument to those failed slides. Typed source classification still widens adjacency, shared CSS, runtime, profile, or deck-wide changes when required. A failed primary or cross-review verdict requires a new capture and inspection for the implicated slide, but does not invalidate unrelated current captures or valid independent cross-reviews.

Any reviewer FAIL is monotonic for that render: do not rewrite it to PASS. Fix the deck, rerun `prepare`, inspect the new capture hashes, and record a new verdict. A shared CSS, runtime, or layout-family edit invalidates every affected slide review; do not preserve or reconstruct old observations. Review JSON is evidence output, not a checklist to complete programmatically.

## Evidence Meaning

The manifest proves that captures came from the current HTML/local assets, match canonical profiles, passed deterministic geometry, and are bound to review records. Reviewer labels and observations remain agent-provided records; do not describe them as cryptographic proof that a particular model or person opened the files.

## Delivery Language

- Edit Only: state that no new render or validation was performed.
- Quick Draft: state that no browser render, automated validation, AI visual review, or quality score was performed.
- Full Validation: report review risk, reviewer count, AI coverage, final score, and any limitation.

Never report stale captures as current evidence or imply a broader validation scope than was performed.
