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

The default is `~/.codex/build-html-slides/workspaces/<deck-id>/`, with `review/`, `drafts/`, and `tmp/` beneath it. The renderer creates and reuses only the latest review evidence for that deck. Put outlines and copy drafts in `drafts/`; put contact sheets and disposable transforms in `tmp/`. `CODEX_HOME` relocates the Codex root, and `BUILD_HTML_SLIDES_WORKSPACE_ROOT` overrides this workspace root explicitly.

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

The preflight never installs software. If it fails, report the exact missing or incompatible components and ask whether the user wants them installed. Stop until the user answers unless the original request already gave explicit installation consent. Never run `npm install`, `npx playwright install`, an OS package manager, or elevated installation commands without that consent. Install only the approved missing components, rerun the preflight, and start deck work only after it passes.

## Build Workflow

1. Inspect supplied files and successful prior decks. Extract useful rhythm, density, composition range, and interaction behavior without copying identity or defects.
2. Read `references/audience-story-routing.md`. Identify audience groups, decision owner, desired room outcome, baseline knowledge, likely objections, locale, and distribution scope. Order information for the actual room. Put shared stakes and decisions before specialist depth when that improves attention; do not apply a generic outline.
3. Read `references/quality-bar.md`, `references/theme-playbook.md`, and `references/theme-gallery.md`. Write a one-line theme contract covering mood, typography, palette roles, shape language, imagery, density, and motion. Choose several composition families rather than repeating one card grid.
4. Read `references/style-presets.md`. Copy `assets/runtime-shell.html` to the output path. Replace all placeholder sections while preserving the stage fitter and navigation runtime. The shell has no art direction; the subject and audience must determine the design.
5. Plan official/supplied/sourced/generated assets and diagrams. Read `references/architecture-diagrams.md` when systems, flows, deployment, integrations, or trust boundaries matter.
6. Implement semantic `<section class="slide" data-title="…">` elements. Give every slide exactly one direct `.slide-media` and `.slide-content` child. Keep meaningful copy and non-croppable visuals in the content-safe layer.
7. Create `OUTPUT-notes.md` from `assets/speaker-notes-template.md`. Use the exact slide number and title. Include purpose/audience, natural 30–90 second talk track, emphasis, transition, and source/caveat guidance without repeating slide text.
8. Run only the checks required by the selected mode in `references/validation-contract.md`. Fix deterministic geometry failures before opening captures. After scoped edits, rerender only the changed slides and immediate neighbors unless global runtime or styles changed.
9. Deliver the HTML, notes, sources cache, asset provenance, selected mode, and only the checks actually performed. Report the validation workspace separately; never present it as a deliverable.

Full Validation controls assurance depth, not research breadth. When a request asks for many, as many as possible, or a large collection of fan artworks, read `references/fan-art-budget.md` before searching. Use its bounded policy by default; do not let open-ended asset discovery consume the time reserved for implementation and validation. Exceed the two-hour delivery envelope only after warning the user and receiving explicit consent for exhaustive research.

## Story And Copy

- Give every slide one main claim and one communication job.
- Build a slide-role table internally with audience, question, decision job, detail level, main visual, and transition. It does not need to become a user-facing artifact.
- Mixed executive, business, and engineering audiences often need decision context and impact before architecture, but derive the sequence from the request rather than applying that example mechanically.
- For Korean decks, read `references/korean-copy.md`. Prefer established Korean names and natural spoken Korean. Keep English for official names, standards, acronyms, or a small secondary label.
- Validate unstable or consequential facts against authoritative sources. For market-specific prices, availability, schedules, regulation, or launch information, read `references/source-locality.md` and use the target region.

## Art Direction

- Translate the theme into type, surfaces, shapes, imagery, information density, and motion, not color alone.
- Use the theme gallery as a vocabulary, not a template library. Combine composition families coherently within one visual system.
- Test the longest title and densest body copy in the actual writing system before committing to typography.
- Do not ship generic demo styling, repeated three-card layouts, decorative gradient blobs, or a recognizable reference deck copied pixel for pixel.
- Promotional, entertainment, product, travel, event, and narrative decks normally need meaningful raster imagery across the story. Technical decks need visual evidence, diagrams, states, or flows rather than walls of prose.
- Use whitespace for hierarchy. Except for intentional hero or chapter slides, avoid compositions that look unfinished or trapped inside one large panel.
- Match every container to its information load. A large bordered or filled box with only a heading, one sentence, or a few short bullets is an underfilled container and a quality defect. Shrink it to its content, remove the surface and use open alignment, or earn the area with meaningful imagery, data, comparison, process, or annotation. Do not stretch sparse facts into equal-height cards merely to fill a grid.

## Asset Contract

1. Inspect user-supplied assets first and copy selected files into a descriptive local assets folder.
2. Read `references/asset-discovery.md`. For named brands, products, games, events, institutions, or projects, search official logos and factual imagery first, then widen discovery through topic-specific archives, creator accounts, visual-search platforms, social posts, photo communities, and fan communities. Do not stop after one official page or one generic image query, but obey the fan-art search ceiling instead of searching indefinitely. Preserve aspect ratio, clear space, signatures, and marks.
3. For games, animation, characters, and fan-art-heavy decks, read `references/fan-art-budget.md`. Internal/private decks may record the discovery URL and visible creator handle without reverse-origin tracing. Public or commercial decks require verified reuse rights or a safer official, licensed, supplied, or original replacement; reduce the number of works instead of extending research beyond the agreed turnaround.
4. Use ImageGen for original atmosphere, editorial illustration, conceptual scenes, and bespoke backgrounds when it improves the story. Do not generate fake factual products, screenshots, logos, or events.
5. Every raster image referenced by the deliverable must be WebP. Keep SVG only for genuine vector logos, icons, and editable diagrams.
6. Use `<img>`, `<picture>`, or SVG `<image>` with local paths. Do not hide raster ownership in global CSS backgrounds.
7. Classify media as decorative, meaningful, or mixed. Decorative media may use `cover`; logos, title art, products, posters, screenshots, diagrams, character art, and edge-important key visuals use `contain`. Mixed media may use a covered backdrop plus a contained foreground copy.
8. Avoid stretching and careless reuse. A continuity asset may appear twice only when the two appearances have different narrative roles and one is clearly subordinate.
9. Maintain `sources.json` with local path, hash, source kind, URL where applicable, verification time, and credit. Run `source_cache.py --update` before researching a revision and revisit only `needs-review` records.

## Runtime And Interaction

- The canonical stage is always 1280×720. Scale it uniformly from `window.visualViewport.width/height`, falling back to `document.documentElement.clientWidth/clientHeight`. Center it in the available viewport. Never reshape the composition to match arbitrary browser aspect ratios.
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
- Check rendered geometry rather than trusting CSS intent. Read `references/visual-qa.md` for the visual inspection checklist.

## Deliverable

Report:

- exact HTML, notes, and `sources.json` paths;
- slide count and selected validation mode;
- audience/story choice and selected theme;
- controls and typography;
- official, supplied, sourced, and generated asset provenance;
- checks actually performed and any limitation.

For Edit Only, explicitly state that no new render or validation was run. Never present old evidence as current. For Quick Draft, distinguish automated geometry coverage from the smaller AI-inspected subset. For Full Validation, report reviewer count, review risk, quality score, and unresolved limitations.

## References And Tools

- `references/validation-contract.md`: single source of truth for mode, render, AI review, reviewer count, incremental validation, and finalization.
- `references/audience-story-routing.md`: audience-aware story order.
- `references/theme-playbook.md` and `references/theme-gallery.md`: theme and composition selection.
- `references/style-presets.md`: canonical stage, media safety, navigation, and responsive fit.
- `references/quality-bar.md`: full-validation scoring rubric.
- `references/slide-by-slide-review.md`: how to inspect rendered evidence and fill review records.
- `references/visual-qa.md`: visual defect checklist.
- `references/architecture-diagrams.md`: editable technical diagrams.
- `references/source-locality.md`: region-specific factual sourcing.
- `references/asset-discovery.md`: broad, topic-aware image discovery and original-source tracing.
- `references/fan-art-budget.md`: bounded fan-art search, provenance, processing, and validation limits.
- `scripts/validate_deck.py`, `validate_speaker_notes.py`, `validate_image_reuse.py`, and `validate_interactions.py`: deterministic deliverable checks.
- `scripts/render_slides.js` and `validate_visual_review.py`: Chromium evidence and adaptive review validation.
- `scripts/check_environment.py`: non-mutating Python, Node.js, Playwright, and Chromium preflight.
- `scripts/measure_container_density.js`: rendered warning detector for oversized low-information surfaces.
- `scripts/source_cache.py`: hash-bound raster provenance cache.
