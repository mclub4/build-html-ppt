# Visual QA

Use this checklist on rendered slides, not source code alone.

## Render integrity

- Generate evidence with `scripts/render_slides.js`; it loads local fonts/images, disables motion only in Playwright, waits two animation frames, navigates by hash, verifies the active slide, measures text/control/image geometry, and hashes each PNG. The delivered HTML keeps its animations. Do not begin AI review unless `automation_gate.status` is `pass`.
- Quick Draft and Full Validation both default to `normal`, `short`, and `zoom150`. Add `tablet` and `mobile` only with `--responsive` when the user requested those targets.
- For Full Validation, `node scripts/render_slides.js --check` must pass before substantive work. If tooling is missing, ask before installing it and rerun the check after approval.

## Quality score

After all render/fix iterations pass, run `--finalize` and score settled renders once with `quality-bar.md`. Record the eight dimensions, calculated total, weakest slides, concrete notes, and stable editor `reviewer_ref`. Quick Draft requires at least 16/24 with no zero. Full Validation requires at least 20/24 with no dimension below 2.

- Name the three weakest slides and explain why they trail the rest.
- Check that the deck uses several composition families and no three consecutive slides repeat the same dominant grid.
- Check that the cover establishes the named subject immediately and the closing resolves the opening promise.
- Treat “still looks like the starter template,” sparse imagery, repeated cards, and weak narrative payoff as blocking quality defects.

## Alignment and controls

- Verify optical and geometric centering for large numerals, icons, badges, and device mockups.
- Inspect every CTA at rendered size. The combined label+icon group must be centered horizontally and vertically inside the button; compare its bounding-box center with the button center and keep the geometric difference within 2px before any optical correction. Confirm card-button top alignment or `space-between` rules do not affect compact CTAs.
- Test navigation with page `1`, a two-digit page, and the last page. The input, slash, and total must share a stable baseline and center vertically inside the control bar.
- Confirm the default control cluster contains no visible slide title, subtitle, section label, or truncated text. Permit one only when explicitly requested and marked `data-nav-title-ok`.
- Compare the bounding-box centers of the current-page input, separator, and total with the counter center. Keep each vertical delta within 1.5px and use equal-height cells rather than padding or translate hacks.
- Confirm the default control cluster sits at the bottom-right, stays compact, does not cover source text or content, and remains usable in a smaller window. A centered oversized control bar requires an explicit reason.
- Preserve the canonical order `previous | current input / total | next | fullscreen`. Theme the panel through `--nav-*` tokens; keep the input integrated with the counter and use inline SVG icons rather than text glyphs.
- Use grid/flex centering. Remove padding or fixed line-height hacks that shift with different glyphs.
- Check repeated cards for identical outer size, padding, title baseline, and number position.

## Logos and brands

- For every named brand/product, confirm whether an official logo or wordmark exists before creating a text substitute.
- Prefer official SVG/transparent PNG; preserve original aspect ratio, colors, and clear space.
- Do not pair an approximate icon with a typed brand name in a way that appears official.
- If unavailable, use neutral typography and note the limitation in presenter notes.

## Typography

- Confirm the font has native, high-quality glyphs for every language used.
- Inspect the longest title, smallest copy, numerals, punctuation, and mixed Korean/Latin lines.
- Avoid over-tight Korean titles, excessive all-caps tracking, crowded breaks, widows, and isolated punctuation.
- Maintain stable kicker, title, subtitle, body, annotation, source, and UI roles.

## Rendered text-box audit

- Follow generated `review_batches`: open at most four slides' listed full-size capture sets in one vision call. Write one observation and one verdict per slide, not one per profile or batch. Ordinary slides require `normal`; cover, closing, explicit `data-visual-critical="true"`, responsive, and warning-routed slides include their listed stress profiles. Do not approve text fit from HTML/CSS, DOM measurements, OCR, or a contact sheet.
- Trace every rendered title, paragraph, list, table cell, diagram label, button, badge, code block, caption, footnote, and source line against its intended box, column, color field, or safe-area edge.
- Fail `text_bounds` when any glyph, underline, focus ring, line box, or emphasis mark crosses a boundary, is clipped by `overflow`, disappears under an adjacent element, or truncates without a deliberate visible ellipsis/fade treatment.
- Inspect right and bottom edges first, then wrapped Korean/Latin lines, long unbroken URLs, numerals, punctuation, and font-fallback cases. Reopen or zoom the original capture when an edge is ambiguous.
- Geometry scripts may identify suspects but cannot provide the visual verdict. Fix the layout, use `--slides N --change-type text`, and inspect the changed slide plus automatically included neighbors before changing their records to `pass`.

## Contrast

- Check rendered contrast, not only declared text and background colors. Body text and controls require at least 4.5:1; large text requires at least 3:1.
- Inspect the full glyph bounds on photographs, gradients, diagonal splits, and layered shapes. If any part crosses into a low-contrast region, move it or add an opaque backing surface, outline, or scrim.
- Treat white-on-white, red-on-red, dark-on-dark, and near-equal colors as blocking even when another part of the word remains visible.
- Inspect normal, hover, focus, disabled, and active states for controls.

## Imagery

- Promotional and narrative decks should normally include meaningful raster imagery throughout the story, not only on the cover.
- Use official/sourced visuals for factual products, people, places, screenshots, logos, and events.
- For games and animation, search the title's official site, media/press page, publisher or studio channels, and official wallpaper/key-art downloads before using generic imagery. Preserve title marks, character faces, composition edges, and spoiler boundaries; record the official source URL.
- For private/internal decks, suitable fan art may be used without formal permission evidence as a hard validation field. Prefer creator-hosted originals, keep creator/source details when discoverable, preserve signatures/watermarks, credit the artist, and never imply official endorsement. Avoid unattributed feeds and repost aggregators.
- For public, commercial, client-facing, or broadly distributed decks, verify intended reuse rights and applicable attribution/adaptation terms or use official, licensed, supplied, or original work instead. Image-search rights filters are discovery hints, not proof.
- Use ImageGen for original atmosphere, conceptual metaphors, lifestyle scenes, and bespoke backgrounds when requested or justified.
- Inspect every crop for focal-point loss, stretching, low resolution, contrast, and text-safe space.
- Treat non-16:9 key visuals, official title art, transparent logos, product shots, and game/anime art as meaningful media. They must not be cropped by `object-fit: cover` unless every cropped edge is decorative. Prefer a blurred decorative backdrop plus a contained foreground key visual.
- Avoid repeating a hero image without a new narrative purpose.
- Confirm every raster asset in the final bundle is WebP. SVG is allowed for true vector logos, icons, and diagrams; PNG, JPEG, GIF, TIFF, BMP, and AVIF references fail validation.
- Compare asset paths and rendered content across slides. Contextual reuse is allowed: one cover/detail hero plus one visibly smaller lineup thumbnail may share a factual title/product image. Both uses must share a documented continuity id, serve different narrative jobs, and total no more than two slides. Repeated large backgrounds, hero+hero reuse, and filler repetition are not allowed.

## Layering and occlusion

- Inspect every image, SVG, pseudo-element, diagram, and decorative shape against every text block at the final viewport.
- Confirm media is in a lower stacking layer and all titles, body text, labels, sources, and controls remain fully readable above it.
- Flag even partial collisions through glyphs, clipped text-safe margins, or low-contrast busy art behind copy.
- Fix collisions by cropping, repositioning, masking, changing the grid, or adding a controlled scrim behind text. Never place artwork in front of copy or hide the problem by fading the text.
- Verify transitions do not temporarily move media over text.

## Density and whitespace

- Standard content slides should usually occupy about 65–85% of the safe canvas.
- Hero/chapter slides may use more negative space, but the composition must remain anchored.
- Flag content confined to the upper half or one corner without an intentional counterweight.
- Fix empty areas through composition, useful content, imagery, or story restructuring—not decorative filler.

## Per-slide pass

Follow `slide-by-slide-review.md`. Inspect each slide once across `required_ai_profiles` and record one observation plus only the checks required by its change type. Initial/mixed work uses all checks; text, image, and navigation-only edits use their scoped checks. A contact sheet is useful for duplication, density, rhythm, and style drift, but it cannot provide a per-slide pass. For region-dependent slides, confirm that visible currency, dates, product names, and sources match the target market.

Also test short browser viewports and zoom/display-scaling conditions that reduce available height. For fixed logical stages, confirm the stage is centered and scaled from `window.visualViewport` dimensions rather than `window.innerWidth` / `window.innerHeight` alone.

## Independent reviewer protocol

Run this protocol for Full Validation.

1. Divide contiguous ranges of at most six slides among visual reviewers, then execute generated batches of at most four slides per vision call. Give each reviewer only each slide's `required_ai_profiles` and relevant source assets; require a stable `reviewer_ref`, one observation, and one scoped verdict per slide. Do not provide the creator's suspected defects.
2. After `--finalize`, give the presentation editor the original request, notes, and settled renders. Calculate the manifest quality score once and record findings on opening promise, audience fit, claim sequence, evidence, transitions, and closing payoff.
3. Give a domain reviewer the same raw artifacts for technical correctness or brand/source provenance when applicable.
4. Require severity, slide number, visible evidence, score impact, and a concrete fix. Reject vague reactions such as “make it pop” or approvals based only on source code.
5. Resolve generic theme, weak imagery, repetitive composition, and story gaps before micro-spacing comments.
6. In final phase, independently cross-review the cover, closing, and critical visual/diagram/data slides with a different `reviewer_ref` bound to the same capture hashes. During fixes, rerender only changed slides and neighbors with the matching change type. Do not close a finding based on an HTML diff alone.
