# Visual QA Checklist

Use this checklist while inspecting the rendered slides selected by `validation-contract.md`. Mode, profile, reviewer-count, and finalization rules do not live here.

## Hierarchy And Story

- The opening establishes a clear promise or stake.
- Each slide has one primary claim and an obvious reading order.
- Evidence appears close to the claim it supports.
- Specialist depth arrives when the audience has a reason to care.
- The closing resolves the opening and leaves a decision, takeaway, or next action.

## Composition

- Layout families vary without breaking the theme system.
- The composition does not look trapped inside one large panel.
- Repeated cards, decorative chips, and labels have a real information job.
- Intentional whitespace reads as hierarchy, not missing work.
- Large cards and panels contain enough information or visual evidence to justify their area; short copy is not stranded inside tall empty boxes.
- Empty outlines, low-contrast placeholder-like shapes, and equal-height sparse cards do not make the slide look unfinished.
- Dense slides have enough separation for scanning and comparison.
- In the all-slide overview, technology content does not collapse into one repeated dark-console fingerprint. A deliberately chosen dark-led system is valid; near-black fields, neon status accents, mono micro-labels, glowing nodes, diagonals, and topology maps must follow the whole communication brief rather than technical vocabulary alone.

## Typography

- Titles fit without awkward single-character wraps or stranded punctuation.
- Display titles and quotes do not leave one or two Korean characters, sentence endings such as `다.`, or closing punctuation alone on the final line.
- Multiline display glyphs have visible separation; no row intersects the glyphs above or below it even when the element itself remains in bounds.
- Body text remains readable on the logical 1280×720 canvas.
- Korean and Latin glyphs look compatible.
- Numerals, punctuation, units, and table alignment are consistent.
- Long text stays inside its intended box, column, cell, badge, button, or safe region.
- Footer text, captions, and sources remain clear of the persistent navigation panel.
- Prompt fragments and production settings do not leak into visible titles, eyebrows, badges, chips, or footer metadata unless the audience needs them as logistics.

## Imagery

- Every main visual has a legible job: evidence, identity, mechanism, concept, or deliberate atmosphere.
- Apply the stock substitution test: when a same-category stock image could replace the visual without changing the claim, fail it as the main explanatory visual. It may remain only where atmosphere is the explicit job.
- The deck's medium matches the subject. Physical industries, products, facilities, equipment, people, experiments, organisms, tissue, and clinical or laboratory phenomena receive enough sourced real-world or scientific imagery to establish the subject; charts and SVGs do not replace seeing the thing itself.
- Unless the brief explicitly required pure HTML or no photography, an image-free chapter reflects a documented semantic choice after relevant visual discovery rather than convenience or an unattempted search.
- The cover or opening sequence visually establishes a materially observable subject unless confidentiality, availability, or a deliberate abstract communication job justifies another approach.
- Data-heavy slides may remain chart-first, but the overall sequence still has image-led context and chapter rhythm when the subject benefits from it.
- Official marks retain aspect ratio and clear space.
- Key visuals use `contain` when faces, products, title art, UI, diagrams, or edges matter.
- Decorative `cover` crops do not remove meaningful content.
- Raster assets are sharp enough at the actual full-size presentation capture and stored as WebP. Converting a small or damaged JPEG to WebP does not improve it.
- Product packaging, faces, screenshots, diagrams, and embedded labels retain crisp edges and readable detail. Reject obvious thumbnails, prior upscales, blur, ringing, mosquito noise, block artifacts, banding, and over-compression.
- Prefer at least 1.25 source pixels per maximum rendered device pixel. Treat less than 1.0 as blocking unless an irreplaceable user-supplied historical asset is explicitly marked, disclosed, and presented small enough to look intentional.
- Reused imagery serves a different narrative role and does not look like filler.
- Sources, credits, signatures, and watermarks remain accurate.
- Each meaningful image visibly matches the subject and narrative claim of its slide; filenames, alt text, captions, folders, and search tags are not proof.
- Named characters and people match a separate official/authoritative reference, including the intended costume, age, form, and distinguishing traits. Uncertain identity is a failure.
- Every apparent media slot is finished. Labels such as `PLACE NOTE`, dummy/temporary art, empty image frames, and repeated generic substitute graphics fail when the slide promises a real place, product, person, character, venue, or event image.
- Judge the visible subject separately from the raster canvas. Large intrinsic white or transparent margins that make the subject look tiny are a composition failure even when `object-fit: contain` passes.
- Compare repeated image frames as a family. One unusually tall, wide, or whitespace-heavy asset must not push a shared grid track, divider, caption, or label out of alignment.

For games and animation, inspect official key art, wallpapers, title art, screenshots, and creator-hosted fan work against spoiler boundaries and distribution rights. Public or commercial decks require verified reuse rights or safer replacements.

## Layers And Contrast

- Media remains behind titles, labels, sources, and controls.
- At 100% capture size, image edges terminate exactly at their intended frame, mask, divider, or bleed boundary; a one- or two-pixel-looking gap, overshoot, accidental tangent, or mismatched corner is a visible defect.
- Translucent overlays and `::before`/`::after` decoration leave no stale duplicate, detached shadow, doubled edge, or residual shape after layout changes.
- Inspect the first glyph and first line start of every text block. Foreground media, masks, gradients, and decorative layers must not cover or visually bite into that starting edge.
- Text does not straddle incompatible light/dark regions without a stable scrim or backing.
- Body text and controls target at least 4.5:1 contrast; large display text targets at least 3:1.
- The automated gate calculates those ratios only when the text background resolves to a solid color. Image, gradient, translucent, blended, shadowed, or overlapping-media backgrounds are warnings routed to full-size AI contrast inspection, not sampled-color passes.
- Every meaningful `<img>` needs useful alt text. Missing alt text is a deterministic Full Validation failure, while deliberately decorative images use `alt=""`.
- Decorative shapes do not create accidental tangencies or obscure hierarchy.
- Dividers, card edges, captions, and labels remain visually separate from imagery. A product or screenshot crossing a divider or entering its caption region is blocking occlusion even when no DOM bounding box leaves the slide.
- Large high-chroma surfaces belong to the established palette and visual sequence. An isolated saturated reset with no subject, brand, media, semantic, or narrative rationale is a visual defect, even when contrast passes.

## Geometry And Runtime

- The full 16:9 stage is centered and visible at each retained profile, including Chromium page scale 1.5 with a measured 1280×720 `visualViewport`.
- No text, logo, image, badge, diagram, or control crosses the stage.
- Navigation order and page counter match the runtime contract.
- Current page, separator, total, and icons are geometrically centered.
- Hash navigation, direct page input, arrows, Page Up/Down, Home/End, fullscreen, edge clicks, and print behavior pass `validate_browser_e2e.js`, not only source-string checks.
- Final HTML retains authored motion and reduced-motion support.

## Evidence And Locale

- Dates, prices, availability, regulation, schedules, and product names match the target market.
- Sources are visible or recorded where the audience needs confidence.
- Decision-critical unfamiliar terms have a short first-use explanation when the audience needs one; familiar or incidental terms are not annotated.
- Term notes remain caption-sized, content-sized, distinct from citations, inside the safe area, and sparse enough that the slide does not become a glossary. A large annotation card or footer panel is a failure.
- Footer term notes terminate before the lower-right navigation exclusion zone; long definitions wrap or move upward rather than continuing behind controls.
- Treat the lower-right navigation exclusion zone as occupied space, not only the visible button rectangle. Captions, notes, sources, logos, images, and decoration must terminate with deliberate breathing room before it.
- Caveats and assumptions are not hidden by the visual treatment.
- Presenter notes add delivery guidance rather than repeating slide copy.

## Blocking Defects

- cropped or stretched meaningful imagery;
- image/frame edges that visibly gap, overshoot, mismatch masks, or create accidental tangencies;
- stale translucent or pseudo-element residue, doubled silhouettes, or detached decorative layers;
- text outside a box or safe area;
- foreground imagery or decoration covering the first glyph or text starting edge;
- orphaned final-line characters or punctuation, colliding text rows, overlapping text regions, or copy covered by navigation;
- unreadable contrast or foreground media over copy;
- broken/missing local assets;
- visibly blurry, thumbnail-sized, previously upscaled, or heavily compressed raster imagery, regardless of file extension or nominal dimensions;
- generic starter styling or repeated default composition;
- repeated top-headline-plus-panel layouts, safe-but-generic typography, or paper styling whose only idea is pale cards and muted rules;
- term notes rendered as large cards, glossary bands, or blocks that crowd source citations or navigation;
- a technology presentation dominated by the same dark-console grammar because of technical vocabulary alone, without a brief-specific rationale, candidate comparison, or meaningful compositional variation;
- a report-like, image-starved treatment of a materially observable subject despite suitable factual imagery being reasonably available;
- wrong region, unsupported factual claims, or misleading provenance;
- wrong character/person, wrong variant, unverifiable identity, or thematically inappropriate imagery;
- generic stock imagery used as explanatory evidence despite contributing no specific identity, mechanism, concept, or factual proof;
- any visible placeholder or generic replacement graphic standing in for missing factual or subject-specific media;
- an unconsidered generic font stack or typography that conflicts with the subject, language, or audience;
- stale captures presented as current evidence.
- a reviewer FAIL replaced with PASS without a new render and independent inspection of the new capture hashes;
- synthetic or bulk-generated visual observations and reviewer identities that do not correspond to actual inspection.
