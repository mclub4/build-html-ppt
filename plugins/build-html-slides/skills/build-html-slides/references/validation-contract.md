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

## Turnaround Envelope

Full Validation controls review depth, not research breadth, art direction, or media variety. It must not simplify an image-worthy physical, industrial, product, or research subject into a report made only of text, charts, tables, and generic SVGs. For a 20-25 slide deck, target 40-90 minutes from settled brief to validated delivery. Ordinary decks should stay near the lower half; image-heavy decks use the upper half. Reserve the final 25-35 minutes for settled rendering, batched AI inspection, focused fixes, one final score, and required cross-review. These are planning targets, not a forced process timeout.

For fan-art-heavy, image-collection, or "as many as possible" requests, `fan-art-budget.md` is mandatory. Check progress around 30-40 minutes or 40-50 candidates. Freeze a strong set when coverage is sufficient; continue only when the expected improvement justifies the remaining validation time. If the work is likely to exceed 90 minutes, explain the cause and ask whether to freeze the current set or continue. Do not add auxiliary source or per-image review agents in ordinary internal/private mode.

## Validation Workspace

Review evidence and temporary authoring files are internal working data, not presentation deliverables. By default, the renderer stores the latest evidence for each deck at:

```text
<agent-home>/build-html-slides/workspaces/<deck-id>/review/
```

Use `node scripts/render_slides.js --workspace-dir OUTPUT.html` to resolve the parent workspace. Store copy drafts in `drafts/` and contact sheets or disposable transforms in `tmp/`. Do not create these files beside the final HTML. Codex defaults to `~/.codex`; Claude Code defaults to `~/.claude`. `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `CLAUDE_HOME`, or `BUILD_HTML_SLIDES_AGENT_HOME` relocates the matching agent home; `BUILD_HTML_SLIDES_WORKSPACE_ROOT` overrides the workspace root directly.

The deck ID combines a readable filename with a hash of the absolute deck path, so decks with the same name do not collide. A full render replaces that deck's prior review directory; incremental renders reuse it. An explicit positional `REVIEW_DIR` remains supported for integrations.

After evidence is no longer needed, remove the default workspace with `node scripts/render_slides.js --clean-workspace OUTPUT.html`. Do not remove it before validation or while incremental revisions are expected.

## Canonical Profiles

Both rendered modes capture every slide at:

- `normal`: 1920×1080 viewport and screenshot, zoom 1;
- `short`: 1366×650 viewport and screenshot, zoom 1;
- `zoom150`: 1920×1080 layout viewport with Chromium page scale 1.5, a measured 1280×720 `visualViewport`, and a 1920×1080 screenshot. This is a browser zoom stress test, not a DPR-only capture.

Add `tablet` 1024×768 and `mobile` 390×844 only when responsive device support is requested. Additional exploratory sizes supplement rather than replace canonical evidence.

## Quick Draft

Run the deterministic deck, visible-placeholder/incomplete-asset gate, notes, source-cache, interaction semantics, real-browser navigation/print E2E, and Chromium geometry checks. The placeholder gate runs in both rendered modes and every `validate_all` phase, including navigation-only revisions, and blocks `PLACE NOTE`, image-here instructions, dummy asset markers, and other explicit unfinished media before AI review. Render all slides at all canonical profiles. Automated text bounds, container-density measurement, control geometry, and image geometry must complete before any AI inspection. Geometry issues block review; low-density container warnings route the affected slide and profile to AI inspection instead of failing automatically.

`data-placeholder-literal="true"` may exempt visible wording only when the slide is genuinely teaching or comparing placeholder behavior. It does not exempt suspicious class names, asset filenames, or media-state markers, and it must never be used to bypass an unfinished visual.

AI inspects only:

- cover and closing slides;
- slides explicitly marked `data-visual-critical="true"`;
- slides and profiles named by automation warnings.
- slides explicitly or automatically routed to identity review for `all` or `image` scope.

Critical slides inspect every generated profile. A warning-triggered ordinary slide inspects `normal` plus the warned profiles. Identity-required slides inspect at least `normal`, including Quick Draft, and require local canonical WebP references plus per-target cue-based verdicts. Identity review activates automatically from subject metadata, named-subject slide kinds, or character/person/profile markup; the slide flag is an explicit signal, not the only trigger. Missing identity metadata or reference files blocks AI review before batching. Other slides retain hash-bound captures and geometry results with `review_method: automated-geometry-only`; they must not claim an AI reviewer or observation.

Quick Draft does not calculate the 24-point quality score, run independent cross-reviews, or require multiple reviewer agents. Report the AI-inspected subset separately from all-slide automated coverage.

## Full Validation

Run all deterministic validators, source checks, and Chromium geometry checks. AI inspects `normal` for every slide and records `completion` for all/image scope. Any visible placeholder, empty media promise, or generic substitute for an expected real subject image blocks delivery regardless of the final quality score. Cover, closing, explicit critical slides, responsive targets, and warning-triggered profiles receive their adaptive stress profiles.

Choose review risk by reasoning about consequences, uncertainty, distribution, technical complexity, visual complexity, and audience sensitivity:

- `standard`: two primary visual reviewers;
- `high`: three primary visual reviewers.

Pass the decision to the renderer with `--review-risk standard|high`. Assign contiguous slide ranges. Vision batches contain at most four slides, independent of reviewer range size.

After fixes settle, run `--finalize`, assign an independent presentation editor, calculate the quality score once, and cross-review the cover, closing, and slides explicitly marked `data-visual-critical="true"` with a reviewer different from each slide's primary reviewer. CSS classes such as `logo`, `key-visual`, `title-art`, or `diagram` do not independently expand cross-review scope. Unresolved high/medium findings or a failing score block delivery.

## Commands

Quick Draft preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode quick --phase prepare
```

Full Validation preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --review-risk standard --phase prepare
```

After filling the listed AI batches, run `python3 scripts/validate_all.py OUTPUT.html --phase verify`. For Full Validation, then run `--phase finalize`, fill the one quality score and required cross-reviews, and run `--phase verify` once more. The entrypoint executes structure, placeholder completion, notes, source cache, reuse, locality, static interaction, browser E2E, render/geometry, and evidence checks in the required order. Use `--responsive` only for requested tablet/mobile support.

## Incremental Revision

After the initial render, use:

```bash
python3 scripts/validate_all.py OUTPUT.html --phase prepare \
  --mode quick|full --review-risk standard|high \
  --slides N --change-type text|image|navigation|all
```

The renderer refreshes changed slides and immediate neighbors. It fingerprints a CSS rule with exactly one matching slide, so a local style edit remains incremental. Shared styles, dynamic active-state selectors, runtime code, profile set, mode, review risk, or slide-title changes still force a full render when reuse is unsafe. Authors may also declare isolated rules with `<style data-slide-scope="N">`.

Run checks by change type:

| Change | Automated and AI scope |
| --- | --- |
| Text | text, text bounds, and container density |
| Image | crop, aspect ratio, resolution, content match, and completion |
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
