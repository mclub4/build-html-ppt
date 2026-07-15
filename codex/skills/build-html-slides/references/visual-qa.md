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

## Typography

- Titles fit without awkward single-character wraps or stranded punctuation.
- Body text remains readable on the logical 1280×720 canvas.
- Korean and Latin glyphs look compatible.
- Numerals, punctuation, units, and table alignment are consistent.
- Long text stays inside its intended box, column, cell, badge, button, or safe region.

## Imagery

- Official marks retain aspect ratio and clear space.
- Key visuals use `contain` when faces, products, title art, UI, diagrams, or edges matter.
- Decorative `cover` crops do not remove meaningful content.
- Raster assets are sharp enough and stored as WebP.
- Reused imagery serves a different narrative role and does not look like filler.
- Sources, credits, signatures, and watermarks remain accurate.
- Each meaningful image visibly matches the subject and narrative claim of its slide; filenames, alt text, captions, folders, and search tags are not proof.
- Named characters and people match a separate official/authoritative reference, including the intended costume, age, form, and distinguishing traits. Uncertain identity is a failure.
- Every apparent media slot is finished. Labels such as `PLACE NOTE`, dummy/temporary art, empty image frames, and repeated generic substitute graphics fail when the slide promises a real place, product, person, character, venue, or event image.

For games and animation, inspect official key art, wallpapers, title art, screenshots, and creator-hosted fan work against spoiler boundaries and distribution rights. Public or commercial decks require verified reuse rights or safer replacements.

## Layers And Contrast

- Media remains behind titles, labels, sources, and controls.
- Text does not straddle incompatible light/dark regions without a stable scrim or backing.
- Body text and controls target at least 4.5:1 contrast; large display text targets at least 3:1.
- Decorative shapes do not create accidental tangencies or obscure hierarchy.

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
- Caveats and assumptions are not hidden by the visual treatment.
- Presenter notes add delivery guidance rather than repeating slide copy.

## Blocking Defects

- cropped or stretched meaningful imagery;
- text outside a box or safe area;
- unreadable contrast or foreground media over copy;
- broken/missing local assets;
- generic starter styling or repeated default composition;
- wrong region, unsupported factual claims, or misleading provenance;
- wrong character/person, wrong variant, unverifiable identity, or thematically inappropriate imagery;
- any visible placeholder or generic replacement graphic standing in for missing factual or subject-specific media;
- an unconsidered generic font stack or typography that conflicts with the subject, language, or audience;
- stale captures presented as current evidence.
