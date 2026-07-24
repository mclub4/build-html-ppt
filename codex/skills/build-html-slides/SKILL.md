---
name: build-html-slides
description: Create or revise offline-portable HTML presentation bundles with audience-aware story structure, topic-specific art direction, WebP imagery, viewport-safe 16:9 playback, presenter notes, keyboard/direct-page navigation, and proportional Chromium visual QA. Use for HTML slide decks, PPT-like presentations, promotional or technical decks, system diagrams, keynote-style HTML, or revisions to an existing deck.
---

# Build HTML Slides

Create a self-contained presentation bundle with:

- one HTML deck;
- local assets when needed;
- sibling `OUTPUT-notes.md` presenter notes;
- sibling `sources.json` when raster assets are used.

Treat every slide as a fixed 16:9 presentation canvas, not a scrolling webpage. Presenter notes are mandatory for new decks in every mode.

## Resolve Paths Before Any Command

The working directory is the user's project, not this skill. Every `scripts/…` and `references/…` path in this file is relative to the skill root — the directory that contains this `SKILL.md`. Resolve that root once, as an absolute path, and prefix every command with it:

```bash
SKILL_DIR=/absolute/path/to/build-html-slides   # the directory holding this SKILL.md
python3 "$SKILL_DIR/scripts/check_environment.py"
```

Typical roots are `~/.codex/skills/build-html-slides`, `~/.claude/skills/build-html-slides`, `~/.gemini/skills/build-html-slides`, or the copy inside a bundled plugin. Confirm the real path from the file you are reading; do not assume one.

Deck, notes, and asset paths stay relative to the user's project. Never `cd` into the skill directory to shorten a command — the deck argument would then resolve against the wrong tree. Every example below uses `$SKILL_DIR` for skill files and `OUTPUT.html` for the user's deck.

## Keep Working Files Out Of The Deliverable

Do not create `review/`, `copy-draft.md`, contact sheets, render logs, or temporary screenshots beside the final deck. Resolve the deck workspace with:

```bash
node "$SKILL_DIR/scripts/render_slides.js" --workspace-dir OUTPUT.html
```

The default is `<agent-home>/build-html-slides/workspaces/<deck-id>/`, with `review/`, `drafts/`, and `tmp/` beneath it. Put outlines and copy drafts in `drafts/`, contact sheets and disposable transforms in `tmp/`. `validation-contract.md` documents the agent homes and the environment overrides.

The deliverable directory contains only the HTML deck, presenter notes, `sources.json` when used, and assets the deck references. Keep the workspace for incremental revisions; remove it only when the user asks or the evidence is stale:

```bash
node "$SKILL_DIR/scripts/render_slides.js" --clean-workspace OUTPUT.html
```

## Decide The Work Mode

Read `references/validation-contract.md` before substantial work.

Resolve two intake fields before researching, drafting, creating files, or generating assets: intended audience and validation mode. Ask every unresolved intake question together in one opening message. Require an explicit mode choice and do not silently infer it; interpret both answers semantically rather than with a keyword table or substring parser. `validation-contract.md` holds the audience options and the Korean mode labels; `청중은 알아서 해줘` means a general company-wide concept-sharing audience with mixed domain familiarity.

- **Edit Only**: an ordinary revision where the user wants a change, not new assurance. Make the edit; create no render or validation pass. Update notes when the story, claim, order, or talk track changed. Disclose that the revision was not re-rendered.
- **빠른 검증 (Quick Draft)**: the user prioritizes iteration, exploration, a first usable version, or the shortest turnaround. Despite the user-facing name, this is a creation-only mode with no rendered validation. Build the HTML, presenter notes, sources cache, and required assets, then stop. Do not run `check_environment.py`, install browser dependencies, open Chromium, render screenshots, run deterministic validators, invoke AI visual review, calculate a quality score, or request independent review. `validate_all.py --mode quick` is only a no-op safety guard: it exits before preflight, rendering, or review-workspace creation at every `--phase`. Follow `references/quick-draft-authoring.md`. Keep design ambition high through hierarchy, imagery, typography, and one or two memorable moments rather than building every slide from scratch. Disclose clearly that the result was not rendered or validated.
- **정밀 검증 (Full Validation)**: the output is for real delivery, publication, or a consequential decision, or strong assurance was requested. Render every slide at the canonical profiles, inspect every slide's `normal` capture with AI, route stress profiles to AI only for visual-critical or automation-warning slides, score the settled deck once, and use the bundled independent reviewer subagents.

After the user chooses Full Validation, infer standard or high review risk from consequences, factual uncertainty, technical or visual complexity, audience sensitivity, and distribution scope. Standard uses two primary reviewers; high uses three. Ask only if the risk level itself stays materially ambiguous.

## Reading Plan

Load a reference at the moment its decision arrives, never as a block up front. Reading every reference before slide one costs more context than the deck itself.

Read once, before substantial work: `references/validation-contract.md`.

| Read | When |
| --- | --- |
| `audience-story-routing.md` | build step 2, every new deck |
| `subject-routing.md`, `design-candidate-search.md` | build step 3, every new deck |
| `theme-playbook.md` | only when the three `suggest_design_directions.py` candidates do not settle the theme contract |
| `theme-gallery.md` | only when you need concrete vocabulary for one already-chosen direction. It is a vocabulary list, not a taxonomy; never read it to *pick* a direction, and never load it together with the playbook by default |
| `cover-design.md` | when writing the cover brief, and again when reviewing slide 1 |
| `style-presets.md` | build step 4, before touching the runtime shell |
| `media-strategy.md` | build step 5, every deck with raster media |
| `chart-selection.md` and `suggest_chart.py` | whenever a slide is about to carry a chart |
| `architecture-diagrams.md` | only after the diagram gate in Companion Skill Routing passes |
| `asset-discovery.md` | before searching factual imagery of a named subject |
| `high-volume-media-workflow.md` | when more than roughly a dozen distinct sourced images are in play |
| `fan-art-budget.md` | before searching fan art or an "as many as possible" collection |
| `identity-review.md` | when a slide claims a named character or real person |
| `image-generation.md` | only when original non-factual raster art is actually wanted |
| `source-locality.md` | for market-specific prices, availability, schedules, regulation, or launch facts |
| `korean-copy.md` | for Korean decks |
| `reviewer-gates.md` | the authoritative check tuples, gate thresholds, escape hatches, and refute-or-confirm procedure. Read before dispatching reviewers, and hand its path to every reviewer |
| `slide-by-slide-review.md` | at the primary review phase, before dispatching reviewers |
| `visual-qa.md` | at the primary review phase, and when triaging any reported defect |
| `quality-bar.md` | Full Validation only, at final review; also handed to the quality editor |
| `quick-draft-authoring.md` | Quick Draft only |

Tools: `validate_all.py` is the canonical phase entrypoint; `check_environment.py` and `install_browser_dependencies.py` handle the preflight; `render_slides.js` produces captures, debug overlays, and the geometry gates, and `validate_visual_review.py` enforces their evidence contract; `validate_deck.py`, `validate_placeholders.py`, `validate_slide_variety.py`, `validate_fonts.py`, `validate_speaker_notes.py`, `validate_source_locality.py`, `validate_image_reuse.py`, `validate_interactions.py`, and `validate_browser_e2e.js` are the deterministic gates; `record_review.py` transcribes reviewer output without ever creating a verdict; `source_cache.py` is the hash-bound provenance cache; `build_media_contact_sheet.js` and `export_archify_asset.js` prepare media; `suggest_design_directions.py` and `suggest_chart.py` are bounded recommendation tools.

## Build Workflow

1. Inspect supplied files and successful prior decks. Extract useful rhythm, density, composition range, and interaction behavior without copying identity or defects.
2. Read `references/audience-story-routing.md`. Identify audience groups, decision owner, desired room outcome, baseline knowledge, likely objections, locale, and distribution scope. Order information for the actual room; put shared stakes and decisions before specialist depth when that improves attention. Build a semantic terminology burden list: at the first meaningful occurrence, add a compact audience-facing note only for an unfamiliar acronym, entity, market, regulation, product, or internal shorthand whose meaning is necessary to understand the slide. Omit notes for terms the named audience can reasonably know, terms already defined in visible copy, and incidental names. Do not use a keyword list or annotate every acronym.
3. Read `references/subject-routing.md` and `references/design-candidate-search.md`. Semantically select one subject family, one primary communication job, audience, evidence obligations, and the density/media/variance/motion dials. Do not classify the raw prompt with keyword, substring, regex, or BM25 rules. Run `python3 "$SKILL_DIR/scripts/suggest_design_directions.py"` for three materially different candidates, compare them against the real brief, and reject at least one with a concrete reason before writing a one-line theme contract covering mood, named display/body font stacks, palette roles, shape language, imagery, density, and motion. The top score is not an automatic selection. Read `theme-playbook.md` only if those three do not settle the contract, and `theme-gallery.md` only for vocabulary on the direction already chosen. For a technology deck, compare an evidence-led schematic direction, a contemporary editorial or geometric direction, and an authentic-media or interface direction when the subject supports them; Paper Systems is one candidate, not the corrective default for avoiding dark consoles. Combine compatible grammar or write a bespoke theme contract when that produces a better deck. Reject any direction whose likely body becomes a pale report with repeated top-title-plus-card rows. Record the chosen luminosity, visual motif, typography contrast, and evidence form. Write a separate cover brief from `references/cover-design.md`, compare at least two materially different slide-1 directions, and implement the stronger one. Choose several body composition families rather than repeating one card grid. Unless the user supplied a brand type system, infer a language- and topic-appropriate pairing without asking a separate font question.
4. Read `references/style-presets.md`. Copy `assets/runtime-shell.html` to the output path and replace all placeholder sections while preserving the stage fitter and navigation runtime. The shell has no art direction; replace its neutral font variables and styling with the chosen theme system. Treat shared runtime and footer classes as reserved. Do not reuse generic names such as `.source`, `.active`, `.left`, `.right`, `.nav`, or `.counter` as component modifiers; namespace slide components such as `.event-stream--source`.
5. Read `references/media-strategy.md`, then plan official/supplied/sourced/generated assets and diagrams. Unless the user explicitly requests a pure-HTML, image-free, or typography/diagram-only deck, search for relevant sourced photographs or factual imagery before settling the visual plan. Use what materially improves identification, evidence, scale, context, human stakes, or atmosphere; omit photography where it adds no information. When the deck introduces an existing named or released person, group, game, product, place, event, interface, or work, complete the factual asset search before considering ImageGen; generated art must never stand in for the real subject.
6. Before producing slide bodies, settle shared typography, embedded WOFF2 faces, 1280×720 stage scaling, content-safe bounds, and the navigation footprint in the runtime shell. **This is the foundation freeze.** Every later shared-CSS or runtime edit invalidates every capture and every review record bound to it; see Fix In Batches, Render Once. Then implement semantic `<section class="slide" data-title="…">` elements, each with exactly one direct `.slide-media` and one `.slide-content` child. Keep meaningful copy and non-croppable visuals in the content-safe layer. Declare `data-media-purpose` on every meaningful image — the geometry gate treats an undeclared image as meaningful and measures it for prominence.
7. Create `OUTPUT-notes.md` from `assets/speaker-notes-template.md`, using the exact slide number and `data-title`; a missing `data-title` is a hard gate failure. Quick Draft notes support roughly 30–60 seconds per slide; Full Validation may use 30–90 when the material warrants it. Include purpose/audience, talk track, emphasis, transition, and only necessary source/caveat guidance without repeating slide text.
8. For Quick Draft, deliver immediately after implementation without running any validation command or creating review evidence. For Full Validation, run the phase sequence below.
9. Deliver the HTML, notes, sources cache, asset provenance, selected mode, and only the checks actually performed. Report the validation workspace separately; never present it as a deliverable.

## Full Validation Phases

Run these in order. Each phase states its precondition, its exact command, what to do with the output, and what blocks progress. `python3 "$SKILL_DIR/scripts/validate_all.py" OUTPUT.html --status` prints the pending batches, the required check tuple per slide, the elapsed budget, and the next phase at any point.

### Phase 0 — Preflight

- **Precondition:** the user chose Full Validation; no substantive deck work has started.
- **Command:** `python3 "$SKILL_DIR/scripts/check_environment.py"`
- **Output:** on pass, continue. On failure, report the exact missing or incompatible components and ask whether the user wants them installed.
- **Blocks:** everything. The preflight never installs software. Never run `npm install`, `npx playwright install`, an OS package manager, or an elevated command without explicit installation consent. After approval, prefer `python3 "$SKILL_DIR/scripts/install_browser_dependencies.py" --consent`, adding `--with-deps` only if system-library installation was also approved. Rerun the preflight and start deck work only after it passes.

### Phase 1 — prepare

- **Precondition:** the HTML, `OUTPUT-notes.md`, `sources.json`, and every local asset exist on disk, and the current editing round is finished.
- **Command:**

  ```bash
  python3 "$SKILL_DIR/scripts/validate_all.py" OUTPUT.html \
    --mode full --review-risk standard --phase prepare
  ```

  Use `--review-risk high` for high risk. On a revision whose scope is already known, add `--slides 7,9-11 --change-type text|image|navigation|all`. `--slides` is valid only during `prepare`.
- **Output:** the deterministic gates run first, then Chromium renders every in-scope slide, runs the measured geometry gates, and writes `review/review.json`, the profile captures, and the debug overlay captures. The phase ends with `NEXT: complete only the AI batches listed in …`.
- **Blocks:** a failing deterministic gate aborts before rendering. A failing `automation_gate` blocks AI review — do not open captures while it is failing. Fix the source and rerun this phase; do not proceed.

On a revision with a current manifest, `validate_all.py` classifies typed source fingerprints even when `--slides` is omitted and supplies the changed slide set itself; `validation-contract.md` documents the direct/neighbor/full impact rules it applies. Keep theme and runtime rules in ordinary shared style blocks and put complex slide-only rules in `<style data-slide-scope="N">` so the classifier can scope them; do not split every slide into a separate CSS file.

### Phase 2 — primary review dispatch

- **Precondition:** phase 1 exited 0.
- **Command:** none. Run `--status` to list the pending batches, then dispatch the reviewer subagents as described in Reviewer Dispatch and transcribe what they return with `record_review.py`.
- **Output:** one recorded slide review per slide listed in `review_batches`.
- **Blocks:** phase 3 fails while any generated batch is unfilled. Never bulk-fill records, synthesize a PASS observation, or overwrite a reviewer FAIL.

### Phase 3 — verify

- **Precondition:** every generated primary batch is recorded.
- **Command:** `python3 "$SKILL_DIR/scripts/validate_all.py" OUTPUT.html --phase verify`
- **Output:** it checks refreshed captures and any previously blocked capture entering AI review; other retained evidence receives metadata checks only.
- **Blocks:** any reviewer FAIL. A FAIL is monotonic for that render — fix the deck, return to phase 1 with the implicated `--slides`, and record a new verdict against the new capture hash. Do not restart unaffected machine checks and do not discard valid cross-reviews whose capture hashes are still current.

### Phase 4 — finalize-prepare

- **Precondition:** zero open FAILs, the deck is settled, and no further shared-CSS or runtime edit is planned.
- **Command:** `python3 "$SKILL_DIR/scripts/validate_all.py" OUTPUT.html --phase finalize-prepare`
- **Output:** it verifies iteration metadata, confirms the settled source fingerprint, then generates — without rerendering any slide — one downscaled, lightly blurred squint contact sheet from the existing `normal` captures, one quality-score record, and the bounded `cross_review_batches`.
- **Blocks:** any shared-CSS or runtime edit after this point changes every capture hash and therefore discards the entire independent primary review. See Fix In Batches, Render Once before making one.

Cross-review covers only the cover, closing, explicit visual-critical or core slides, automation-warning slides, and identity-sensitive slides. Never add ordinary distributed samples to raise the reviewer count. Squint review is an auxiliary deck-wide check; it never replaces full-size inspection for text overlap, awkward line breaks, crop, distortion, or overflow.

### Phase 5 — final review dispatch

- **Precondition:** phase 4 exited 0.
- **Command:** none. Invoke `build-html-slides-quality-editor` once and record its `squint`, `quality`, and `cross-slide` output.
- **Blocks:** phase 6 fails while the squint record, the score, or any pending cross-review batch is missing.

### Phase 6 — finalize-verify

- **Precondition:** the squint record, the single quality score, and every pending cross-review are recorded.
- **Command:** `python3 "$SKILL_DIR/scripts/validate_all.py" OUTPUT.html --phase finalize-verify`
- **Output:** it checks every capture hash plus HTML and local-file freshness.
- **Blocks:** delivery. A total below 20/24, any dimension below 2, or an unresolved high/medium finding requires revision.

Every phase appends command-level durations to `review/timings.json`, which is what `--status` reads to report elapsed budget.

## Reviewer Dispatch

Full Validation review is performed by two bundled subagents, invoked with the Task tool. The authoring agent never writes its own review verdict; leaving dispatch implicit is exactly what produces self-authored review records.

- `build-html-slides-visual-reviewer` — primary and cross-review inspection of full-size captures.
- `build-html-slides-quality-editor` — one final pass: squint review, the single quality score, the weakest slides, and the pending `cross_review_batches`.

**Primary dispatch, after phase 1:**

1. Read `review/review.json`. Only slides listed in `review_batches` need AI inspection.
2. Split those batches into contiguous slide ranges: two reviewers at standard risk, three at high risk — the same count passed to `--review-risk`.
3. **Issue every reviewer in a single message so they run concurrently.** Their ranges are disjoint and share no state; sequential dispatch roughly doubles primary-review wall-clock and is a defect.
4. Each invocation must carry, as absolute paths and literal values:
   - the `review.json` path and the sibling `sources.json` path;
   - the batch's slide numbers — at most four per vision call, the contract's `review_batch_size`;
   - for each slide, every PNG path in its `required_ai_profiles` (normally `normal`, plus `short` or `zoom150` only where the manifest routes them);
   - for each slide with a `debug_captures` entry, that overlay PNG too, labeled as the overlay. The renderer writes `<profile>/slide-NN-debug.png` for every slide with a measured issue or warning, drawing slide bounds, container boxes, image boxes, text-line ink boxes, and the nav exclusion zone over the real capture, so the reviewer sees which card owns an image instead of guessing;
   - the slide's `review_scope`, the exact check tuple it requires, and the path to `references/reviewer-gates.md`;
   - the verbatim warning text for any slide that carries one, which puts that slide into the **refute-or-confirm** pass defined in `reviewer-gates.md`: the observation must open with `CONFIRM: ` or `REFUTE: ` and name an element and location. Generic approval does not close a warning;
   - for `identity_required` slides, every `identity_targets[].reference_path`.
5. Each reviewer returns JSON with `reviewer_ref` and `slides[]`, each entry containing `slide`, `inspected_profiles`, `observation`, `checks`, `identity_review`, `status`, and `notes`.
6. Transcribe each returned record exactly as returned. Do not fill a slide the reviewer did not return and do not author an observation yourself.

**Final dispatch, after phase 4:** one `build-html-slides-quality-editor` invocation receiving `review.json`, the `squint_review.artifact_path`, the full-size capture paths it is allowed to open, the presenter-notes path, the audience brief, and the absolute path to `references/quality-bar.md`. It returns `reviewer_ref`, `squint_review`, `dimensions`, `total`, `weakest_slides`, `notes`, and `cross_reviews`.

**Independence:** every cross-reviewer's `reviewer_ref` must be outside the complete primary-reviewer set, not merely different from the primary reviewer of that slide. Do not claim independent review for a record you authored.

### Check Tuples

`record_review.py` requires each expected check exactly once, in the contract order from `checks_by_change` in `scripts/validation_contract.json`, and rejects any other set:

- `all`: `crop`, `aspect_ratio`, `resolution`, `content_match`, `completion`, `overflow`, `occlusion`, `text`, `text_bounds`, `contrast`, `density`, `controls`
- `text`: `text`, `text_bounds`, `contrast`, `density`
- `image`: `crop`, `aspect_ratio`, `resolution`, `content_match`, `completion`
- `navigation`: `controls`

### Recording Syntax

Four subcommands: `slide`, `cross-slide`, `quality`, `squint`. Each `--check` is `name=pass|fail`; `--inspected` is a comma-separated profile list that must exactly equal that slide's current required profiles; an observation under 24 characters is rejected.

```bash
REVIEW="$(node "$SKILL_DIR/scripts/render_slides.js" --workspace-dir OUTPUT.html)/review/review.json"

python3 "$SKILL_DIR/scripts/record_review.py" "$REVIEW" slide \
  --slide 7 --reviewer build-html-slides-visual-reviewer --reviewer-ref vr-a-01 \
  --status pass --inspected normal \
  --check crop=pass --check aspect_ratio=pass --check resolution=pass \
  --check content_match=pass --check completion=pass --check overflow=pass \
  --check occlusion=pass --check text=pass --check text_bounds=pass \
  --check contrast=pass --check density=pass --check controls=pass \
  --observation "Product photo fills the left column to its card edge; caption clears the nav zone by ~40px."
```

`cross-slide` takes the same arguments. `quality` takes `--dimension name=0..3` exactly once for each of `story`, `art_direction`, `layout_rhythm`, `typography`, `imagery`, `composition`, `evidence`, `presentation_utility`, plus `--weakest 4,11,18`; it rejects `--status pass` under 20/24 or with any dimension below 2. `squint` takes `--check` for `focal_hierarchy`, `emphasis_range`, `deck_rhythm`, and `color_density_balance`.

## Deterministic Gates And Their Thresholds

`references/reviewer-gates.md` is the authority for every threshold, message string, and escape hatch; `scripts/validation_contract.json` is the machine authority. Do not restate a number from either here or in a review observation. These gates run inside `--phase prepare`, before any capture reaches a reviewer. Each one replaces a reviewer paragraph with a measurement, and no reviewer may argue a measured issue away.

Design to them up front — passing is far cheaper than failing:

| Gate | Blocks when |
| --- | --- |
| Container containment | an image escapes its `.card`/`.panel`/`.tile`/`.box` padding box by more than **2px** |
| Hero prominence | a hero or cover subject renders under **15%** of the 1280×720 stage |
| Subject prominence | an ordinary subject renders under **2%** of the stage, or its short edge is under **96** stage px (warnings at **5%** and at under **0.25×** intrinsic size) |
| Text collision | adjacent lines overlap by more than **1px** of glyph ink, or an opaque layer bites **1.5px** into it |
| Nav exclusion zone | anything intrudes more than **1px** into the reserved lower-right **280×84** stage rectangle |
| Container density | a region at least **7%** of the slide and **200×110** px carries too little ink — warning |
| Contrast | the provable best-case ratio is still under **4.5:1** body or **3:1** large text |
| Slide variety | two substantive slides share a skeleton at **≥ 0.90** similarity |

Three authoring consequences:

- `data-media-purpose` is authoritative; `.slide-media` membership means nothing to the classifier. Use `atmosphere`, `concept`, `scenario`, or `decorative` for support imagery and `subject`, `evidence`, or `identity` for anything the audience must read. An undeclared image counts as meaningful and is measured for prominence.
- Keep footer notes, sources, logos, and captions out of the navigation zone at authoring time. The shell's `.nav-safe-note` helper clears it by construction; `data-nav-exclusion-ok` is a deliberate exception, never a silencer. Quick Draft must honor this even though it never renders.
- Every escape hatch is an author declaration, not a reviewer opinion, and the slide still needs a visual verdict that says why the exception is legitimate.

## Time Budget

**Full Validation: 70 minutes for a 20-25 slide deck. Quick Draft: 15 minutes.** These are ceilings, not aspirations. `scripts/validation_contract.json` holds the same figures under `time_budgets`, and `validate_all.py --status` reports elapsed time against them from `review/timings.json`.

| Stage | Allowance | Cumulative |
| --- | --- | --- |
| Brief, audience and mode intake, preflight | 5 min | 5 |
| Research and factual/media discovery | 12 min | 17 |
| Theme contract, storyboard, cover brief | 5 min | 22 |
| Authoring: HTML, notes, assets | 18 min | 40 |
| `--phase prepare` | 5 min | 45 |
| Primary review, all reviewers concurrent | 10 min | 55 |
| One batched fix round, re-prepare, `--phase verify` | 8 min | 63 |
| `--phase finalize-prepare` | 2 min | 65 |
| Final review | 3 min | 68 |
| `--phase finalize-verify` | 2 min | 70 |

The per-phase ceilings enforced by the contract are higher than this plan on purpose — prepare 15, primary-review 25, verify 3, finalize-prepare 5, final-review 18, finalize-verify 4. The table is the plan that keeps you under them.

Checkpoints act autonomously. Do not ask the user at a checkpoint: asking costs time it cannot recover and is skipped entirely in a non-interactive run. Cut, then report what was cut.

- **At 25 minutes elapsed, or 40 media candidates, whichever comes first — freeze the media set.** No further image searching. Every remaining slide is composed from assets already acquired, or from type, data, and slide-native visuals.
- **At 45 minutes elapsed, if `--phase prepare` has not yet passed — cut scope, in this fixed order:** drop remaining optional atmosphere imagery and ship those slides type-led; stop all design-candidate comparison and commit to the current theme contract; restrict sourcing to the existing cache (`source_cache.py --update` only, no new research); reduce the deck to the slides that carry the argument. Never cut presenter notes, a deterministic gate, or the reviewer dispatch.
- **At 60 minutes elapsed — no new review rounds.** Finish the phase in flight, run `--phase finalize-verify`, and deliver with every unresolved item listed as an explicit limitation.
- **Quick Draft at 8 minutes — freeze media and stop discovery.** Complete the deck from what exists.

Full Validation controls assurance depth, not research breadth, art direction, or visual-media variety. It must not turn an image-worthy presentation into a chart-and-SVG report. When a request asks for many, as many as possible, or a large collection of fan artworks, read `references/fan-art-budget.md` before searching and apply the first checkpoint above to its targets.

## Fix In Batches, Render Once

- Collect every finding from a complete review round — all reviewers, all batches, and every deterministic warning — before editing anything.
- Apply them in one editing pass, then run `--phase prepare` once. One re-render per round, never one per finding. A re-render is the single most expensive step in the budget.
- **A shared-CSS or runtime edit after `--phase finalize-prepare` changes every capture hash and discards the entire independent primary review**, which must then be re-dispatched from phase 2. Before making one, acknowledge the cost explicitly: name the slides that lose their review records and the roughly 15 minutes the re-dispatch adds. If a `<style data-slide-scope="N">` rule can fix the defect locally, use that instead. The foundation freeze in build step 6 exists to make this rare.
- Within one reviewer's range, batches may be issued together; across reviewers, dispatch is always concurrent.

## Companion Skill Routing

- Inspect the skills already available in the session before drafting. Never install or configure a missing companion during deck work without explicit consent.
- Availability is sufficient consent to use a companion whose routing rule matches. Do not ask whether to use an available `humanize-korean` or `archify`; invoke it automatically at the right stage.
- If `humanize-korean` is available and the deliverable contains Korean, invoke it once after facts, numbers, proper nouns, citations, and slide order have settled — and before the deck is captured, so its edits do not invalidate a review. Apply it to slide copy and presenter notes, then review the diff and reject any change to meaning, factual claims, figures, names, source scope, or technical terminology.
- Bundled distributions include `archify` as an independent sibling skill. Do not load its full instructions during ordinary deck planning. First decide semantically whether a complex diagram materially improves understanding of topology, order, boundaries, ownership, or relationships compared with a photograph, real interface, chart, table, or simple native visual. Technical vocabulary alone is never sufficient. Only after that gate passes, read `references/architecture-diagrams.md`, load Archify, and invoke it without waiting for a separate request. Otherwise skip Archify entirely and keep simple grids, two- or three-node flows, and staged-animation diagrams in semantic HTML/CSS or inline SVG.
- Preserve Archify's self-contained HTML as the reproducible diagram source. Use `scripts/export_archify_asset.js` for a clean theme-bound SVG and exact-size WebP without viewer controls, insert the chosen asset into the real slide, and run the same gates as every other slide. If `archify` is unavailable because only the slide skill was copied, continue with the native diagram path and disclose it; never install software during deck work without explicit consent.

## Story And Copy

- Give every slide one main claim and one communication job.
- Separate private authoring constraints from audience-facing copy. Never echo validation mode, slide count, file format, requested workflow, image quantity, design instructions, or prompt phrases such as `개념 강의 + 팀 활동` into titles, eyebrows, badges, chips, or cover metadata unless the audience genuinely needs them as logistics.
- Build a slide-role table internally — audience, question, decision job, detail level, main visual, transition. It need not become a user-facing artifact.
- Mixed executive, business, and engineering audiences often need decision context and impact before architecture, but derive the sequence from the request rather than applying that example mechanically.
- Match terminology support to audience familiarity. A domain-team status update omits explanations for shared internal vocabulary; a company-wide concept-sharing deck explains only the few terms needed to follow the argument; executive notes state business meaning rather than dictionary expansions. With `청중은 알아서 해줘`, use the company-wide mixed-familiarity default.
- Keep visible term notes sparse: mark them `data-term-note`, one short plain-language line at the first meaningful occurrence, normally no more than one or two per slide. Render each as a quiet inline annotation or compact micro-note rail, never as a large card, tall footer panel, or empty framed box. Keep it smaller than body copy and physically separate from `data-source-citation`. If more terms need explanation, simplify the copy, spread them across slides, or move secondary definitions into presenter notes.
- Never place a term note, source, logo, or caption in the persistent lower-right navigation exclusion zone.
- For Korean decks, read `references/korean-copy.md`. Prefer established Korean names and natural spoken Korean; keep English for official names, standards, acronyms, or a small secondary label.
- Validate unstable or consequential facts against authoritative sources. For market-specific prices, availability, schedules, regulation, or launch information, read `references/source-locality.md` and use the target region.

## Art Direction

- Translate the theme into type, surfaces, shapes, imagery, density, and motion, not color alone.
- Every large-area non-neutral color needs a palette provenance: subject or media-derived, authentic brand identity, semantic status, or deliberate editorial pacing. Unsupported high-chroma colors may appear only as small accents, rules, labels, marks, or controls. Never use a saturated full-slide reset to manufacture variety.
- Slide 1 is the highest-priority art-direction decision: it must establish the literal subject, opening promise, and visual tone within roughly three seconds. After its first settled render, give it a dedicated full-size refinement pass covering subject authenticity, focal crop, title wrapping, type contrast, color integration, depth, logo and metadata placement, edge details, and navigation clearance. A cover for an existing named subject needs an authentic identity anchor; generated scenery may support it but never replace it.
- Declare `--font-display`, `--font-body`, and `--font-mono` from the language, subject, audience, and room, with visible role contrast through family, width, weight, scale, or serif/sans tension. One family is acceptable only when the theme contract says why and the layout still creates distinct roles. Never ship the shell's neutral stack unchanged or fall back to bare `system-ui`.
- Use only weights present in the local font files and keep `font-synthesis: none`. Bundle a real bold or variable face instead of synthetic Korean bold. Every `<strong>` or `<b>` stays visibly distinct through a supported weight or another deliberate cue.
- Full Validation requires every used display, body, and mono family to resolve to a redistribution-compatible local WOFF2 inside the deck folder. A system fallback, remote font, missing face, or declared-but-unused bundle blocks portability assurance.
- Technology is a subject domain, not a visual theme. Dark-led directions remain valid when the audience, tone, pacing, evidence contrast, venue, or subject identity supports them, and so are paper-led, mixed-surface, editorial, geometric, authentic-media, and interface-led ones; reject only automatic routing from a topic noun. Classify the communication job before mapping a subject to a theme — for travel, ordinary leisure guides default to Destination Magazine rather than Field Notes.
- Test the longest title and densest body copy in the real writing system before committing to typography. Fix stranded final-line characters and colliding glyph rows by editing copy, width, size, or line-height, not by approving a box that technically contains broken text.
- Give every meaningful `<img>` useful alt text; missing alt text blocks Full Validation.
- Never ship generic demo styling, repeated three-card layouts, decorative gradient blobs, or a recognizable reference deck copied pixel for pixel.
- Promotional, entertainment, product, travel, event, and narrative decks normally need meaningful raster imagery across the story; technical, market, industrial, and research decks need the right mix of sourced real-world or scientific imagery, data, diagrams, states, and flows. Rigor is never a reason to hide an observable subject behind charts and SVGs.
- Plan each meaningful visual as evidence, identity, mechanism, concept, or atmosphere, and require a contribution beyond repeating the headline. Apply the stock substitution test from `media-strategy.md`: if an unrelated image from the same broad stock category could replace it without weakening the claim, it is generic atmosphere and must not hold the main explanatory role.
- Use whitespace for hierarchy. Outside intentional hero or chapter slides, avoid compositions trapped in one large panel. Generic framed cards should not dominate more than roughly one third of body slides in an ordinary explanatory deck; catalogs, dashboards, and deliberate fixed-format comparisons are exceptions. Replace dominant card grids with information-native forms: an editorial spread, annotated object, continuous process rail, layered diagram, timeline, evidence strip, full-width comparison, or type-led statement.
- Match every container to its information load. A large bordered or filled box holding one heading, one sentence, or a few short bullets is underfilled: shrink it to its content, drop the surface for open alignment, or earn the area with real imagery, data, comparison, process, or annotation. Never stretch sparse facts into equal-height cards.

## Asset Contract

1. Inspect user-supplied assets first and copy selected files into a descriptive local assets folder.
2. Read `references/asset-discovery.md` before searching a named person, group, brand, product, released game, event, institution, place, or project. Search official factual imagery first, then widen; never stop after one official page or one generic query. A generated lookalike is never a fallback for unsuccessful discovery. Preserve aspect ratio, clear space, signatures, and marks.
3. When many distinct sourced images would make serial inspection dominate the schedule, follow `references/high-volume-media-workflow.md` and review up to twelve labeled candidates at once with `scripts/build_media_contact_sheet.js`. Deep-research and regenerate only flagged candidates. Never search, download, inspect, crop, convert, and render each image in isolation.
4. For games, animation, characters, and fan-art-heavy decks, follow `references/fan-art-budget.md`. Internal or private decks may record the discovery URL and visible creator handle without reverse-origin tracing. Public or commercial decks require verified reuse rights or a safer official, licensed, supplied, or original replacement; reduce the number of works rather than extending research past the budget.
5. For slides claiming a named fictional character or real person, follow `references/identity-review.md`. Ground each subject with a separate official, licensed, or supplied local WebP reference and visible cues. Identity review is automatically activated by subject metadata and character/person/profile markup; `data-identity-review="required"` is documentation, not the only trigger. Filenames, folders, alt text, captions, and source tags are never identity evidence. When several images show one subject, reuse a single canonical reference and compare candidates as a batch.
6. Read `references/image-generation.md` only when original raster art is actually wanted. Use a generator only for non-factual atmosphere, concepts, scenarios, or decoration, and never install or configure one without consent; its absence never fails the preflight. Never generate a real idol, celebrity, historical person, released game, gameplay screen, product, place, artwork, logo, interface, event, or evidence image as a substitute for sourced material. `source_cache.py --check` rejects generated subject, evidence, and identity roles.
7. Every raster image in the deliverable must be WebP; keep SVG only for genuine vector logos, icons, and editable diagrams. Conversion does not repair a thumbnail, blur, ringing, block artifacts, or prior upscaling. Prefer source pixels at least 1.25× the maximum rendered device-pixel size, and replace visibly soft assets even when the intrinsic dimensions technically pass.
8. Use `<img>`, `<picture>`, or SVG `<image>` with local paths. Never hide raster ownership in global CSS backgrounds.
9. Declare every image's role with `data-media-purpose`. Decorative media may use `cover`; logos, title art, products, posters, screenshots, diagrams, character art, and edge-important key visuals use `contain`. Mixed media may use a covered backdrop plus a contained foreground copy.
10. Avoid stretching and careless reuse. A continuity asset may appear twice only when the two appearances have different narrative roles and one is clearly subordinate.
11. Maintain `sources.json` schema 2 with local path, hash, asset roles, source kind, URL where applicable, verification time, and credit. `data-identity-reference` files are cache entries even when not rendered and must use an authoritative source kind. Both actions take the deck and the cache as positional arguments — the bare flag is not a valid invocation:

    ```bash
    python3 "$SKILL_DIR/scripts/source_cache.py" OUTPUT.html sources.json --update
    python3 "$SKILL_DIR/scripts/source_cache.py" OUTPUT.html sources.json --check
    ```

    Run `--update` before researching a revision and revisit only `needs-review` records. `--check` is what `--phase prepare` runs.
12. Placeholders may exist only in the private authoring workspace. Never deliver visible labels such as `PLACE NOTE`, image-here instructions, dummy assets, empty image frames, or generic substitutes standing in for an expected place, product, person, character, venue, or event image. Full Validation blocks them automatically; Quick Draft relies on authoring discipline and provides no assurance. Acquire the asset, redesign the slide without that visual promise, or disclose the limitation before delivery.

## Runtime And Interaction

- The canonical stage is always 1280×720. Scale it uniformly from `window.visualViewport.width/height`, falling back to `document.documentElement.clientWidth/clientHeight`. Include `visualViewport.offsetLeft/offsetTop` when centering, and anchor navigation, progress, and edge-click regions to that same visible area so 150% browser zoom cannot move controls off-screen. Never reshape the composition to match arbitrary browser aspect ratios.
- Do not calculate fit from `window.innerWidth` or `window.innerHeight` alone. Do not place meaningful content outside the 1280×720 safe canvas.
- Preserve keyboard navigation, edge clicks, hashes, Home/End, Page Up/Down, direct numeric page input, fullscreen, and print behavior.
- Keep the navigation order: previous icon, integrated current/total counter, next icon, fullscreen icon. Do not add the slide title to the panel. Theme only the navigation tokens unless the user requests a different interaction model.
- Keep page numerals, separator, icons, and CTA contents geometrically centered with grid/flex and tabular numerals.
- Make anything that looks interactive work with semantic buttons or links, focus states, and accessible names. Avoid redundant in-slide utility navigation when persistent controls already provide it.
- Keep final animation around 300–600ms and respect reduced motion. Validation disables motion only inside Chromium capture.

## Content Fit

- Fit content by editing, splitting, simplifying, or changing layout before shrinking type.
- Keep body copy at least 16px and code at least 13px on the logical 1280×720 canvas unless the user explicitly requires denser material.
- Keep UTF-8 throughout. Replacement characters and repairable mojibake are blocking defects.
- No text, logo, key visual, diagram, screenshot, badge, or control may cross the safe canvas or be hidden behind another layer.
- No visible placeholder, temporary asset label, empty media promise, or generic fallback graphic may remain. `completion` is a blocking visual verdict, not a quality-score deduction.
- Check rendered geometry rather than trusting CSS intent. Read `references/visual-qa.md` for the visual inspection checklist and `references/slide-by-slide-review.md` for how to fill the records.
- Inspect relationships, not only bounds. Media that stays inside the slide still fails when it crosses a divider, label, caption, text region, control, or the intended edge of its card. Subject imagery that is technically contained but too small to read fails on prominence, and near-duplicate compositions fail on variety — both are measured, so do not argue them away as intentional.

## Deliverable

Report:

- exact HTML, notes, and `sources.json` paths;
- slide count and selected validation mode;
- audience/story choice and selected theme;
- controls and typography;
- official, supplied, sourced, and generated asset provenance;
- checks actually performed, anything cut at a budget checkpoint, and any remaining limitation.

For Edit Only, explicitly state that no new render or validation was run. Never present old evidence as current. For Quick Draft, state that the deck was created without browser rendering, automated validation, AI visual review, or a quality score. For Full Validation, report reviewer count, review risk, quality score, and unresolved limitations. Do not claim independent review when reviewer records were authored by the same agent without a real separate inspection of the current capture hashes.
