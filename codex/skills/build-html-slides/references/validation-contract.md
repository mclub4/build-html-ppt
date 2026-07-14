# Validation Contract

This file is the single source of truth for validation modes, render profiles, AI review routing, reviewer count, incremental checks, and finalization.

## Choose By Intent

New-deck creation requires an explicit user choice between Quick Draft and Full Validation. If the user has not already chosen, present both modes with their validation scope and relative turnaround, ask once, and stop before research, drafting, file creation, or asset generation. Do not silently infer the mode. Recognize an explicit choice from meaning and context rather than a keyword list, regular expression, or substring heuristic.

| Mode | Use when | New evidence |
| --- | --- | --- |
| Edit Only | The user primarily wants an ordinary revision and does not seek new assurance | None |
| Quick Draft | The user prioritizes iteration or a first usable version | Automated geometry for every slide; adaptive AI subset |
| Full Validation | The deck is intended for delivery, publication, or a consequential decision, or strong assurance is requested | Automated geometry and AI review for every slide, independent review, final score |

Edit Only applies to an existing deck revision when the user asks for a change without requesting new validation evidence. It is not a substitute for asking the required new-deck mode question.

## Tool Preflight And Installation Consent

After the user chooses Quick Draft or Full Validation, run this shared preflight before substantive work:

```bash
python3 scripts/check_environment.py
```

The script checks Python, Node.js, Playwright, Chromium, and screenshot capture without installing anything. If it fails, report the exact missing or incompatible components and ask whether the user wants them installed. Stop until the user gives explicit consent unless that consent was already part of the request. Do not run `npm install`, `npx playwright install`, an OS package manager, or elevated installation commands first. After approved installation, rerun the preflight. Do not begin either rendered mode until it passes.

## Validation Workspace

Review evidence and temporary authoring files are internal working data, not presentation deliverables. By default, the renderer stores the latest evidence for each deck at:

```text
~/.codex/build-html-slides/workspaces/<deck-id>/review/
```

Use `node scripts/render_slides.js --workspace-dir OUTPUT.html` to resolve the parent workspace. Store copy drafts in `drafts/` and contact sheets or disposable transforms in `tmp/`. Do not create these files beside the final HTML. `CODEX_HOME` relocates the Codex root; `BUILD_HTML_SLIDES_WORKSPACE_ROOT` overrides the workspace root.

The deck ID combines a readable filename with a hash of the absolute deck path, so decks with the same name do not collide. A full render replaces that deck's prior review directory; incremental renders reuse it. An explicit positional `REVIEW_DIR` remains supported for integrations.

After evidence is no longer needed, remove the default workspace with `node scripts/render_slides.js --clean-workspace OUTPUT.html`. Do not remove it before validation or while incremental revisions are expected.

## Canonical Profiles

Both rendered modes capture every slide at:

- `normal`: 1920×1080 viewport and screenshot, zoom 1;
- `short`: 1366×650 viewport and screenshot, zoom 1;
- `zoom150`: 1280×720 CSS viewport, 1920×1080 screenshot, zoom 1.5.

Add `tablet` 1024×768 and `mobile` 390×844 only when responsive device support is requested. Additional exploratory sizes supplement rather than replace canonical evidence.

## Quick Draft

Run the deterministic deck, notes, interaction, source-cache, and Chromium geometry checks. Render all slides at all canonical profiles. Automated text bounds, control geometry, and image geometry must pass before any AI inspection.

AI inspects only:

- cover and closing slides;
- slides explicitly marked `data-visual-critical="true"`;
- slides and profiles named by automation warnings.

Critical slides inspect every generated profile. A warning-triggered ordinary slide inspects `normal` plus the warned profiles. Other slides retain hash-bound captures and geometry results with `review_method: automated-geometry-only`; they must not claim an AI reviewer or observation.

Quick Draft does not calculate the 24-point quality score, run independent cross-reviews, or require multiple reviewer agents. Report the AI-inspected subset separately from all-slide automated coverage.

## Full Validation

Run all deterministic validators, source checks, and Chromium geometry checks. AI inspects `normal` for every slide. Cover, closing, explicit critical slides, responsive targets, and warning-triggered profiles receive their adaptive stress profiles.

Choose review risk by reasoning about consequences, uncertainty, distribution, technical complexity, visual complexity, and audience sensitivity:

- `standard`: two primary visual reviewers;
- `high`: three primary visual reviewers.

Pass the decision to the renderer with `--review-risk standard|high`. Assign contiguous slide ranges. Vision batches contain at most four slides, independent of reviewer range size.

After fixes settle, run `--finalize`, assign an independent presentation editor, calculate the quality score once, and cross-review the cover, closing, and marked critical slides with a reviewer different from each slide's primary reviewer. Unresolved high/medium findings or a failing score block delivery.

## Commands

Quick Draft:

```bash
node scripts/render_slides.js OUTPUT.html --mode quick
python3 scripts/validate_visual_review.py OUTPUT.html
```

Full Validation:

```bash
node scripts/render_slides.js OUTPUT.html --mode full --review-risk standard
python3 scripts/validate_visual_review.py OUTPUT.html
node scripts/render_slides.js OUTPUT.html --finalize
python3 scripts/validate_visual_review.py OUTPUT.html
```

Use `--responsive` only for requested tablet/mobile support.

## Incremental Revision

After the initial render, use:

```bash
node scripts/render_slides.js OUTPUT.html \
  --mode quick|full --review-risk standard|high \
  --slides N --change-type text|image|navigation|all
```

The renderer refreshes changed slides and immediate neighbors. It forces a full render when global styles, runtime, profile set, mode, review risk, or slide titles make reuse unsafe.

Run checks by change type:

| Change | Automated and AI scope |
| --- | --- |
| Text | text and text bounds |
| Image | crop, aspect ratio, and resolution |
| Navigation | controls and interaction |
| Mixed/global | all checks |

Do not recalculate the quality score during the fix loop. Full Validation scores only after the settled final render.

## Evidence Meaning

The manifest proves that captures came from the current HTML/local assets, match canonical profiles, passed deterministic geometry, and are bound to review records. Reviewer labels and observations remain agent-provided records; do not describe them as cryptographic proof that a particular model or person opened the files.

## Delivery Language

- Edit Only: state that no new render or validation was performed.
- Quick Draft: report all-slide automated coverage and the exact AI-inspected slides.
- Full Validation: report review risk, reviewer count, AI coverage, final score, and any limitation.

Never report stale captures as current evidence or imply a broader validation scope than was performed.
