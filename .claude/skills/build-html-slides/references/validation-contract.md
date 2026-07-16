# Validation Contract

This file defines validation semantics. `scripts/validation_contract.json` is the machine-readable authority for the schema version, exact profile geometry, check sets, batch size, managed Playwright version, and standard cross-review sampling values. Scripts and tests must read that JSON rather than duplicate those values.

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

The script checks Python, Node.js, Playwright, Chromium, and screenshot capture without installing anything. If it fails, report the exact missing or incompatible components and ask whether the user wants them installed. Stop until the user gives explicit consent unless that consent was already part of the request. Do not run `npm install`, `npx playwright install`, an OS package manager, or elevated installation commands first. After approval, prefer the bundled user-scoped installer:

```bash
python3 scripts/install_browser_dependencies.py --consent
```

It installs the contract-pinned Playwright package and Chromium under `~/.build-html-slides/runtime`. Use `--with-deps` only when the user also approved Linux system-library installation, which may require elevated privileges. After installation, rerun the preflight. Do not begin either rendered mode until it passes.

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

During `prepare`, run the deterministic deck and visible-placeholder/incomplete-asset gates, plus only the notes, source, image, or browser-interaction gates relevant to the detected source change. The placeholder gate therefore runs once for every new or edited source before AI review, not again in evidence-only phases. It blocks `PLACE NOTE`, image-here instructions, dummy asset markers, CSS-generated placeholder copy, and other explicit unfinished media. Initial renders capture all slides at all canonical profiles. Automated text bounds, rendered-line composition, cross-layer occlusion, container-density measurement, control geometry, and image geometry must complete before any AI inspection; incremental renders execute only the geometry families relevant to the detected edit. The rendered-line pass blocks Korean display orphans, punctuation-only final lines, colliding glyph rows, sibling text intersections, navigation-covered copy, and opaque unrelated layers covering text. Geometry failures block review. Low-density surfaces and meaningful `object-fit: cover` crops are warnings that route the affected slide and profile to AI inspection, because automation can detect risk but cannot decide semantic crop quality.

`data-placeholder-literal="true"` may exempt visible wording only when the slide is genuinely teaching or comparing placeholder behavior. It does not exempt suspicious class names, asset filenames, or media-state markers, and it must never be used to bypass an unfinished visual.

AI inspects only:

- cover and closing slides;
- slides explicitly marked `data-visual-critical="true"`;
- slides and profiles named by automation warnings.
- slides explicitly or automatically routed to identity review for `all` or `image` scope.

The cover and closing are always visual-critical and cannot be downgraded to automation-only. Critical slides inspect every generated profile. A warning-triggered ordinary slide inspects `normal` plus the warned profiles. Identity-required slides inspect at least `normal`, including Quick Draft, and require local canonical WebP references plus per-target cue-based verdicts. Identity review activates automatically from subject metadata, named-subject slide kinds, or character/person/profile markup; the slide flag is an explicit signal, not the only trigger. Missing identity metadata or reference files blocks AI review before batching. Other slides retain hash-bound captures and geometry results with `review_method: automated-geometry-only`; they must not claim an AI reviewer or observation.

Quick Draft does not calculate the 24-point quality score, run independent cross-reviews, or require multiple reviewer agents. Report the AI-inspected subset separately from all-slide automated coverage.

## Full Validation

The initial Full preparation runs the complete deterministic suite and Chromium geometry checks. Later edits run only gates that the typed change can affect. AI inspects `normal` for every refreshed slide and records `completion` for all/image scope. Any visible placeholder, empty media promise, or generic substitute for an expected real subject image blocks delivery regardless of the final quality score. Cover, closing, explicit critical slides, and warning-triggered profiles receive their adaptive stress profiles. When responsive support was requested, tablet/mobile captures remain automated evidence for ordinary slides and become AI-required only for critical or warning-routed slides.

Choose review risk by reasoning about consequences, uncertainty, distribution, technical complexity, visual complexity, and audience sensitivity:

- `standard`: two primary visual reviewers;
- `high`: three primary visual reviewers.

Pass the decision to the renderer with `--review-risk standard|high`. Assign contiguous slide ranges. Vision batches contain at most four slides, independent of reviewer range size.

After fixes settle, run `--phase finalize-prepare`. This verifies iteration metadata, confirms the current source fingerprint, then generates the one quality-score record and bounded `cross_review_batches` without rerendering. Assign an independent presentation editor and calculate the quality score once. At standard risk, use a deck-wide overview for rhythm and media balance, then open full-size cover, closing, critical/warning, generated sample, and suspected weak slides; do not repeat every ordinary primary review merely to calculate the score. For standard risk, cross-review cover, closing, explicit visual-critical slides, automation-warning slides, and a deterministic distributed sample of ordinary slides. For high risk, cross-review every slide. Exact sampling values come from `validation_contract.json`. Every cross-reviewer must be outside the complete primary-reviewer set, not merely different from the primary reviewer assigned to that slide. This is intentional independent cross-validation, not a redundant machine rerun. After a focused fix, passing cross-reviews for unchanged captures remain reusable only when their capture hashes, required profiles, checks, and reviewer independence still match; the changed or failed slides receive new cross-review records. Unresolved high/medium findings or a failing score block delivery.

## Commands

Quick Draft preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode quick --phase prepare
```

Full Validation preparation:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --review-risk standard --phase prepare
```

After filling the listed AI batches, run `python3 scripts/validate_all.py OUTPUT.html --phase verify`. Quick Draft ends there. For Full Validation, then run `--phase finalize-prepare`, fill the generated quality score and `cross_review_batches`, and run `--phase finalize-verify`. `prepare` executes change-relevant deterministic gates and rendering; `verify` checks refreshed captures and any previously blocked captures entering AI review, while other retained evidence receives metadata checks only; `finalize-prepare` performs the one settled Chromium source-fingerprint confirmation and prepares final records without rerendering; `finalize-verify` checks every capture hash plus HTML/local-file freshness without recomputing the same browser fingerprint. Use `--responsive` only for requested tablet/mobile support.

## Incremental Revision

After the initial render, use:

```bash
python3 scripts/validate_all.py OUTPUT.html --phase prepare \
  --mode quick|full --review-risk standard|high \
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

Do not recalculate the quality score during the fix loop. Full Validation scores only after the settled final render. A failed automated check blocks AI review; after repair, rerun only the failed/changed slide scope and relevant geometry family. A failed primary or cross-review verdict requires a new capture and inspection for the implicated slide, but does not invalidate unrelated current captures or valid independent cross-reviews.

Any reviewer FAIL is monotonic for that render: do not rewrite it to PASS. Fix the deck, rerun `prepare`, inspect the new capture hashes, and record a new verdict. A shared CSS, runtime, or layout-family edit invalidates every affected slide review; do not preserve or reconstruct old observations. Review JSON is evidence output, not a checklist to complete programmatically.

## Evidence Meaning

The manifest proves that captures came from the current HTML/local assets, match canonical profiles, passed deterministic geometry, and are bound to review records. Reviewer labels and observations remain agent-provided records; do not describe them as cryptographic proof that a particular model or person opened the files.

## Delivery Language

- Edit Only: state that no new render or validation was performed.
- Quick Draft: report all-slide automated coverage and the exact AI-inspected slides.
- Full Validation: report review risk, reviewer count, AI coverage, final score, and any limitation.

Never report stale captures as current evidence or imply a broader validation scope than was performed.
