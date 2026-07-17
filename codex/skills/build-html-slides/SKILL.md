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

## Keep Working Files Out Of The Deliverable

Do not create `review/`, `copy-draft.md`, contact sheets, render logs, or temporary screenshots beside the final deck. Resolve the deck workspace with:

```bash
node scripts/render_slides.js --workspace-dir OUTPUT.html
```

The default is `<agent-home>/build-html-slides/workspaces/<deck-id>/`, with `review/`, `drafts/`, and `tmp/` beneath it. Codex uses `~/.codex`; Claude Code uses `~/.claude`; Gemini CLI uses `~/.gemini`. The renderer creates and reuses only the latest review evidence for that deck. Put outlines and copy drafts in `drafts/`; put contact sheets and disposable transforms in `tmp/`. `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `CLAUDE_HOME`, or `GEMINI_HOME` relocates the matching agent home. `BUILD_HTML_SLIDES_AGENT_HOME` overrides any agent home, and `BUILD_HTML_SLIDES_WORKSPACE_ROOT` overrides the workspace root directly.

The deliverable directory should contain only the HTML deck, presenter notes, `sources.json` when used, and assets referenced by the deck. Keep the workspace for incremental revisions. Remove it only when the user asks or the evidence is no longer needed:

```bash
node scripts/render_slides.js --clean-workspace OUTPUT.html
```

An explicit legacy `REVIEW_DIR` remains supported when integration with another system requires it.

## Decide The Work Mode

Read `references/validation-contract.md` before substantial work.

For every new deck, require an explicit mode choice before researching, drafting, creating files, or generating assets. If the user already chose Quick Draft or Full Validation, proceed with that mode. Otherwise, stop and present both options with their validation scope and relative turnaround, then ask the user to choose. Do not silently infer a mode, even when one appears likely from context. Interpret an explicit choice semantically rather than with a keyword table or substring parser.

- **Edit Only**: ordinary revisions where the user primarily wants a change, not new assurance. Make the requested edit and do not create a new render or validation pass. Update notes when the story, claim, order, or talk track changed. Disclose that the revision was not re-rendered.
- **Quick Draft**: the user prioritizes iteration, exploration, a first usable version, or short turnaround. Keep design ambition high, but use deterministic checks as the main safety net. Render every slide at the three canonical profiles; AI inspects only cover, closing, explicitly critical, and warning-triggered slides. Do not run a quality score or multi-agent final review.
- **Full Validation**: the output is intended for real delivery, publication, a consequential decision, or the user asks for strong assurance. Render all slides, inspect every slide with AI, score the settled deck once, and use independent reviewers.

After the user chooses Full Validation, infer standard or high review risk from consequences, factual uncertainty, technical or visual complexity, audience sensitivity, and distribution scope. Standard Full Validation uses two primary reviewers; high risk uses three. Ask only if that risk level itself remains materially ambiguous.

After the user chooses Quick Draft or Full Validation, run this preflight before substantive work:

```bash
python3 scripts/check_environment.py
```

The preflight never installs software. If it fails, report the exact missing or incompatible components and ask whether the user wants them installed. Stop until the user answers unless the original request already gave explicit installation consent. Never run `npm install`, `npx playwright install`, an OS package manager, or elevated installation commands without that consent. After approval, prefer `python3 scripts/install_browser_dependencies.py --consent` for a user-scoped Playwright/Chromium runtime; use `--with-deps` only when the user also approved system-library installation. Rerun the preflight and start deck work only after it passes.

## Build Workflow

1. Inspect supplied files and successful prior decks. Extract useful rhythm, density, composition range, and interaction behavior without copying identity or defects.
2. Read `references/audience-story-routing.md`. Identify audience groups, decision owner, desired room outcome, baseline knowledge, likely objections, locale, and distribution scope. Order information for the actual room. Put shared stakes and decisions before specialist depth when that improves attention; do not apply a generic outline.
3. Read `references/quality-bar.md`, `references/theme-playbook.md`, `references/theme-gallery.md`, and `references/cover-design.md`. Write a one-line theme contract covering mood, named display/body font stacks, palette roles, shape language, imagery, density, and motion. Write a separate cover brief, compare at least two materially different slide-1 directions in planning, and implement the stronger one. Choose several body composition families rather than repeating one card grid. Unless the user supplied a brand type system, infer an attractive language- and topic-appropriate pairing without asking a separate font question.
4. Read `references/style-presets.md`. Copy `assets/runtime-shell.html` to the output path. Replace all placeholder sections while preserving the stage fitter and navigation runtime. The shell has no art direction; replace its neutral font variables and styling with the chosen theme system.
5. Read `references/media-strategy.md`, then plan official/supplied/sourced/generated assets and diagrams. Classify each meaningful visual role as factual subject/evidence or illustrative support. When the deck introduces an existing named or released person, group, game, product, place, event, interface, or work, complete the factual asset search before considering ImageGen; generated art must never stand in for the real subject. Decide semantically whether the audience needs to see real products, facilities, equipment, people, organisms, tissue, experiments, interfaces, or places. Read `references/architecture-diagrams.md` when systems, flows, deployment, integrations, or trust boundaries matter.
6. Implement semantic `<section class="slide" data-title="…">` elements. Give every slide exactly one direct `.slide-media` and `.slide-content` child. Keep meaningful copy and non-croppable visuals in the content-safe layer.
7. Create `OUTPUT-notes.md` from `assets/speaker-notes-template.md`. Use the exact slide number and title. Include purpose/audience, natural 30–90 second talk track, emphasis, transition, and source/caveat guidance without repeating slide text.
8. Run the selected mode through `python3 scripts/validate_all.py OUTPUT.html --mode quick|full --phase prepare`. Each new or edited source goes through the deterministic completion gate before captures open; later phases validate evidence instead of rerunning the same deterministic suite. Fill only the generated review batches and run `--phase verify`. Full Validation then uses `--phase finalize-prepare`, fills the generated score and independent cross-review batches, and ends with `--phase finalize-verify`; Quick Draft ends after `verify`. After scoped edits, pass `--slides` plus the best change-type hint. The typed classifier decides impact: pure copy, image, or slide-local CSS refreshes only affected slides; structure, order, transition, or adjacency-sensitive changes add immediate neighbors; shared CSS, runtime, profile, or deck-wide dependency changes refresh the full deck. It also skips notes, source, image, and browser-E2E gates that the detected edit cannot affect. Treat rendered pixels as the source of truth: never bulk-fill review records, synthesize PASS observations, or override a reviewer FAIL. After a failure, fix and reinspect the implicated slides and checks; do not restart unaffected machine checks or discard valid independent cross-reviews whose capture hashes remain current.
9. Deliver the HTML, notes, sources cache, asset provenance, selected mode, and only the checks actually performed. Report the validation workspace separately; never present it as a deliverable.

Full Validation controls assurance depth, not research breadth, art direction, or visual-media variety. It must not turn an image-worthy presentation into a chart-and-SVG report. For 20-25 slides, target 40-90 minutes. When a request asks for many, as many as possible, or a large collection of fan artworks, read `references/fan-art-budget.md` before searching. Use its planning targets to protect implementation and validation time, but treat them as checkpoints rather than hard caps. If the task is likely to exceed 90 minutes, explain why and ask whether to continue discovery or freeze the current set; do not abruptly stop the work.

## Optional Companion Routing

- Inspect the skills already available in the current agent session before drafting. Never install or configure a missing companion during deck work without explicit consent.
- If `humanize-korean` is available and the deliverable contains Korean, invoke it once after facts, numbers, proper nouns, citations, and slide order have settled. Apply it to slide copy and presenter notes without waiting for a separate request. Review the diff and reject any change to meaning, factual claims, figures, names, source scope, or technical terminology.
- If `archify` is available and the deck needs an architecture, network or cloud topology, deployment view, ERD, UML, sequence, lifecycle, codebase structure, or a complex multi-component flow, invoke it proactively without waiting for a separate request. Read `references/architecture-diagrams.md` for the handoff contract.
- Keep simple slide-native grids, two- or three-node flows, and diagrams whose main purpose is staged animation in semantic HTML/CSS or inline SVG. Do not pay the companion export and review cost when it adds no clarity.
- Preserve Archify's self-contained HTML as the reproducible diagram source and use its inline SVG or a WebP export in the deck. Remove export controls from the embedded slide asset, match the deck theme, and rerun the same geometry and visual checks as for every other slide. If Archify is missing, ask before installing it; if the user declines, use the native diagram path.

## Story And Copy

- Give every slide one main claim and one communication job.
- Build a slide-role table internally with audience, question, decision job, detail level, main visual, and transition. It does not need to become a user-facing artifact.
- Mixed executive, business, and engineering audiences often need decision context and impact before architecture, but derive the sequence from the request rather than applying that example mechanically.
- For Korean decks, read `references/korean-copy.md`. Prefer established Korean names and natural spoken Korean. Keep English for official names, standards, acronyms, or a small secondary label.
- Validate unstable or consequential facts against authoritative sources. For market-specific prices, availability, schedules, regulation, or launch information, read `references/source-locality.md` and use the target region.

## Art Direction

- Translate the theme into type, surfaces, shapes, imagery, information density, and motion, not color alone.
- Treat slide 1 as the deck's highest-priority art-direction decision. It must establish the literal subject, opening promise, and visual tone within roughly three seconds; do not spend the visual ambition only on body slides.
- Give slide 1 a dedicated full-size refinement pass after its first settled render. Inspect subject authenticity, focal crop, title wrapping, type contrast, color integration, depth, logo and metadata placement, edge details, and navigation clearance. A cover for an existing named subject needs an authentic identity anchor; generated scenery may support it but cannot replace it.
- Choose typography proactively from the language, subject, audience, and room. Declare `--font-display`, `--font-body`, and `--font-mono`; use a deliberate display/body contrast when the theme benefits from it. Do not ship the shell's neutral font stack unchanged or fall back to bare `system-ui` as the final art direction.
- Use only weights present in the selected local font files and keep `font-synthesis: none`. Bundle a real bold/variable face instead of synthetic Korean bold. Every `<strong>` or `<b>` must remain visibly distinct through a supported weight or another deliberate cue; do not reset it to the parent's weight and color.
- Use the theme gallery as optional vocabulary, not a template library or closed taxonomy. Never select a named direction from the topic noun alone. Start from the audience, communication job, emotional tone, available authentic media, and desired pacing; combine compatible grammar or write a bespoke theme contract when that produces a better deck.
- Classify the communication job before mapping a subject to a theme. For travel, distinguish consumer magazine, premium hospitality, documentary reportage, and expedition records; ordinary leisure guides default to Destination Magazine rather than Field Notes.
- Test the longest title and densest body copy in the actual writing system before committing to typography.
- Treat rendered line quality as geometry, not taste alone. Display copy must not leave one or two Korean characters or punctuation stranded on a final line, adjacent glyph rows must not collide, and persistent navigation must not cover captions or footer text. Fix copy, width, font size, or line-height before AI review rather than approving a box that technically contains broken text.
- Do not ship generic demo styling, repeated three-card layouts, decorative gradient blobs, or a recognizable reference deck copied pixel for pixel.
- Promotional, entertainment, product, travel, event, and narrative decks normally need meaningful raster imagery across the story. Technical, market, industrial, and research decks need the right mix of sourced real-world or scientific imagery, data, diagrams, states, and flows. Do not treat rigor as a reason to hide a physical or observable subject behind charts and SVGs.
- Use whitespace for hierarchy. Except for intentional hero or chapter slides, avoid compositions that look unfinished or trapped inside one large panel.
- Match every container to its information load. A large bordered or filled box with only a heading, one sentence, or a few short bullets is an underfilled container and a quality defect. Shrink it to its content, remove the surface and use open alignment, or earn the area with meaningful imagery, data, comparison, process, or annotation. Do not stretch sparse facts into equal-height cards merely to fill a grid.

## Asset Contract

1. Inspect user-supplied assets first and copy selected files into a descriptive local assets folder.
2. Read `references/asset-discovery.md`. For named people, groups, brands, products, released games, events, institutions, places, or projects, search official photos, screenshots, title art, packaging, logos, and other factual imagery first, then widen discovery through topic-specific archives, creator accounts, visual-search platforms, social posts, photo communities, and fan communities. A generated lookalike is not a fallback for unsuccessful discovery. Do not stop after one official page or one generic image query. For fan-art-heavy work, use the search targets as checkpoints and avoid indefinite research. Preserve aspect ratio, clear space, signatures, and marks.
3. For games, animation, characters, and fan-art-heavy decks, read `references/fan-art-budget.md`. Internal/private decks may record the discovery URL and visible creator handle without reverse-origin tracing. Public or commercial decks require verified reuse rights or a safer official, licensed, supplied, or original replacement; reduce the number of works instead of extending research beyond the agreed turnaround.
4. For slides claiming a named fictional character or real person, read `references/identity-review.md`. Ground each subject with a separate official, licensed, or supplied local WebP reference and visible cues, then annotate every meaningful subject image. Identity review is automatically activated by subject metadata and character/person/profile markup; `data-identity-review="required"` is explicit documentation, not the only trigger. Filenames, folders, alt text, captions, and source tags are not identity evidence.
5. Read `references/image-generation.md` when original raster imagery would improve the story. Use a configured image-generation tool only for non-factual atmosphere, concepts, scenarios, or decoration. Its absence does not fail the browser preflight or block ordinary deck work. Never install or configure a generator without consent, and do not generate a real idol, celebrity, historical person, released game, gameplay screen, product, place, artwork, logo, interface, event, or evidence image as a substitute for sourced material. Set every generated raster use's `data-media-purpose` to one of `atmosphere`, `concept`, `scenario`, or `decorative`; `source_cache.py --check` rejects generated subject, evidence, and identity roles.
6. Every raster image referenced by the deliverable must be WebP. Keep SVG only for genuine vector logos, icons, and editable diagrams. WebP conversion does not repair a thumbnail, blur, ringing, block artifacts, or prior upscaling. Prefer source pixels at least 1.25× the maximum rendered device-pixel size and replace visibly soft assets even when the intrinsic dimensions technically pass.
7. Use `<img>`, `<picture>`, or SVG `<image>` with local paths. Do not hide raster ownership in global CSS backgrounds.
8. Classify media as decorative, meaningful, or mixed. Decorative media may use `cover`; logos, title art, products, posters, screenshots, diagrams, character art, and edge-important key visuals use `contain`. Mixed media may use a covered backdrop plus a contained foreground copy.
9. Avoid stretching and careless reuse. A continuity asset may appear twice only when the two appearances have different narrative roles and one is clearly subordinate.
10. Maintain `sources.json` schema 2 with local path, hash, asset roles, source kind, URL where applicable, verification time, and credit. `data-identity-reference` files are cache entries even when not rendered and must use an authoritative source kind. Run `source_cache.py --update` before researching a revision and revisit only `needs-review` records.
11. Placeholders may exist only in the private authoring workspace. Neither Quick Draft nor Full Validation may deliver visible labels such as `PLACE NOTE`, image-here instructions, dummy assets, empty image frames, or generic substitute graphics standing in for an expected place, product, person, character, venue, or event image. Acquire or generate an appropriate asset, redesign the slide without that visual promise, or disclose the limitation before delivery; never disguise missing work as a finished card.

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
- Keep UTF-8 throughout. Replacement characters and mojibake are blocking defects.
- No text, logo, key visual, diagram, screenshot, badge, or control may cross the safe canvas or be hidden behind another layer.
- No visible placeholder, temporary asset label, empty media promise, or generic fallback graphic may remain. `completion` is a blocking visual verdict, not a minor quality-score deduction.
- Check rendered geometry rather than trusting CSS intent. Read `references/visual-qa.md` for the visual inspection checklist.
- Inspect relationships, not only bounds. Media that remains inside the slide still fails when it crosses a divider, label, caption, text region, control, or the intended edge of its card. Also fail subject imagery that is technically contained but visually unusable because intrinsic whitespace makes it tiny or an oversized inset dominates the composition.

## Deliverable

Report:

- exact HTML, notes, and `sources.json` paths;
- slide count and selected validation mode;
- audience/story choice and selected theme;
- controls and typography;
- official, supplied, sourced, and generated asset provenance;
- checks actually performed and any limitation.

For Edit Only, explicitly state that no new render or validation was run. Never present old evidence as current. For Quick Draft, distinguish automated geometry coverage from the smaller AI-inspected subset. For Full Validation, report reviewer count, review risk, quality score, and unresolved limitations. Do not claim independent review when reviewer records were authored by the same agent without a real separate inspection of the current capture hashes.

## References And Tools

- `references/validation-contract.md`: semantic contract for mode, render, AI review, reviewer count, incremental validation, and finalization. Exact profiles, checks, batch size, and sampling values live in `scripts/validation_contract.json`.
- `references/audience-story-routing.md`: audience-aware story order.
- `references/theme-playbook.md` and `references/theme-gallery.md`: theme and composition selection.
- `references/cover-design.md`: first-slide planning, art direction, media, typography, and blocking review criteria.
- `references/style-presets.md`: canonical stage, media safety, navigation, and responsive fit.
- `references/quality-bar.md`: full-validation scoring rubric.
- `references/slide-by-slide-review.md`: how to inspect rendered evidence and fill review records.
- `references/visual-qa.md`: visual defect checklist.
- `references/identity-review.md`: canonical-reference contract for named character and person imagery.
- `references/architecture-diagrams.md`: editable technical diagrams.
- `references/media-strategy.md`: semantic decision rules for real-world, scientific, screenshot, chart, and diagram coverage.
- `references/source-locality.md`: region-specific factual sourcing.
- `references/asset-discovery.md`: broad, topic-aware image discovery and original-source tracing.
- `references/fan-art-budget.md`: bounded fan-art search, provenance, processing, and validation limits.
- `scripts/validate_all.py`: canonical prepare, verify, finalize-prepare, and finalize-verify entrypoint.
- `scripts/validate_deck.py`, `validate_placeholders.py`, `validate_speaker_notes.py`, `validate_image_reuse.py`, `validate_interactions.py`, and `validate_browser_e2e.js`: deterministic deliverable, completion, and real-browser behavior checks.
- `scripts/render_slides.js` and `validate_visual_review.py`: Chromium evidence, true page-scale zoom, and adaptive review validation.
- `scripts/check_environment.py`: non-mutating Python, Node.js, Playwright, and Chromium preflight.
- `scripts/install_browser_dependencies.py`: explicit-consent, user-scoped Playwright/Chromium installer.
- `scripts/measure_container_density.js`: rendered warning detector for oversized low-information surfaces.
- `scripts/source_cache.py`: hash-bound raster provenance cache.
