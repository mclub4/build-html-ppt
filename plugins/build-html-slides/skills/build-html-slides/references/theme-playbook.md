# Theme Playbook

## Theme inference

Read `theme-gallery.md`, then define six decisions before styling: three mood adjectives; display and body typography; palette roles; shape language; media treatment; and motion character. Write them as a one-line theme contract before coding.

| Direction | Best for | Visual grammar |
|---|---|---|
| Editorial field guide | security, policy, strategy, architecture | paper + forest/dark surfaces, serif display with sans utility, thin rules, mint/orange accents, generous margins, diagrams and matrices |
| Technical night | infrastructure, developer tools, systems | near-black/navy, cyan or green accent, monospace details, glowing nodes, code and topology diagrams |
| Minimal corporate | proposals, reports, roadmaps | warm white or navy, restrained blue/green, clean grid, quiet transitions, data-first layouts |
| Cinematic game | game introductions, lore, entertainment | dark vignette, expressive display type, bold accent, large art crops, chapter cards, spoiler-aware copy |
| Bright learning | education, onboarding, explainers | light surfaces, friendly saturated accents, simple diagrams, numbered steps, generous whitespace |
| Product launch | product/feature storytelling | strong hero, benefit cards, product imagery, high contrast, short copy, deliberate negative space |
| Raw culture | music, community, experimental brands | hard grids or print collage, condensed display type, halftone imagery, limited ink colors, abrupt scale shifts |
| Scientific atlas | research, medicine, climate, space | specimen plates, labeled scales, sectional diagrams, magnified evidence, uncertainty and source captions |
| Blueprint build | architecture, robotics, hardware, protocols | measured grids, exploded views, dimensions, revision marks, phased assembly or implementation flows |
| Documentary essay | field reporting, social impact, case studies | full-frame photography, location/date slugs, testimony, map interludes, quiet evidence captions |
| Spatial product | AI products, mobility, digital twins, XR | layered depth, isolated objects, anchored labels, restrained translucency, state transitions |
| Financial trust | banking, fintech, stablecoins, payments | tabular numerals, reserve composition, money movement, fiat/chain boundaries, audit trails, semantic risk color |

These are routing hints, not fixed presets. Use the larger gallery for distinctive directions including Neo Brutalist, Riso Zine, Scientific Atlas, Blueprint Workshop, Documentary Photo Essay, Spatial Interface, and Ledger Trust alongside the original gallery. Mix only compatible attributes.

## Theme contract

Record this compact internal spec before implementation:

```text
Mood: precise / urgent / humane
Type: heavy Korean sans display + readable sans body + mono metadata
Palette roles: dark field / paper reset / safety orange / mint status
Shape: thin boundaries, square cards, rounded image masks only
Media: documentary WebP photography + editable SVG systems diagrams
Motion: short directional fades; chapter images settle more slowly
```

Do not select a theme by swapping color tokens on the starter template. Change typography, spacing, image treatment, composition families, source treatment, and motion together.

## Visual rhythm

Plan the sequence as a set of spreads, not isolated pages.

- Open with identity and a promise.
- Follow with a thesis or tension slide that makes the audience care.
- Alternate evidence-heavy and image-led slides so the deck can breathe.
- Insert a chapter break, quote, or surface reset before attention drops.
- Place the densest diagram or table after its context has been established.
- End by resolving the opening promise, not by repeating a generic thank-you page.
- Avoid three consecutive slides with the same dominant grid. A color change alone does not create rhythm.

For a typical 8-15 slide deck, use at least five composition families from `quality-bar.md`. Promotional and narrative decks should normally include a cover, editorial split, full-bleed or contained key visual, lineup/gallery, decision slide, and designed closing. Technical decks should normally include a stakes image, system context, process or loop, failure/timeline, authority or comparison, and roadmap/closing.

## Financial and stablecoin visuals

For banking, payments, stablecoins, treasury, reserve, or settlement topics:

- Separate user funds, issuer reserves, operating funds, custodians, banks, blockchains, and merchants as labeled boundaries rather than merging them into a generic network.
- Show money movement with directional verbs and name the asset, unit, network, timing, and settlement destination when known.
- Distinguish issuer disclosure, third-party attestation, audit, regulatory status, and onchain evidence. Do not use these terms interchangeably.
- Date every balance, reserve, market, yield, transaction, adoption, and availability figure. Never fabricate a live ticker or imply live data from a static source.
- Use tabular numerals and semantic color: green for verified/backed/complete, blue for transfer/settlement, amber for dependency or pending state, red only for loss, breach, depeg, or blocking risk.
- Use official token and institution marks only when sourced. A generic coin or chain glyph must not masquerade as a real asset.
- Present depeg, liquidity, custody, smart-contract, counterparty, operational, and regulatory risks in the same visual system as benefits. Never imply guaranteed value, redemption, yield, or returns beyond the cited terms.

## Matching a reference

Extract the stage and margin proportions, typography contrast, color roles, layout families, line weights, radii, texture, image treatment, transition behavior, and control placement. Rebuild cleanly in UTF-8. Do not inherit malformed HTML, mojibake, inaccessible controls, overflowing absolute layouts, or brittle paths.

## Editorial mixed-surface pattern

For a theme like the trust-boundary reference:

- Use a 1920×1080 logical stage only when poster-like typography benefits from the scale, and always fit it with the visualViewport-based scaling rules in `style-presets.md`.
- Alternate paper, dark, forest, and tinted wash surfaces.
- Pair an elegant serif display face with strong sans-serif utility text.
- Use mint for safe/approved states and orange/coral for gates or warnings.
- Favor thin borders, large statements, matrices, numbered annotations, and full-width flow diagrams.
- Add subtle CSS grain only when it remains legible and cheap to render.
- Include print CSS that reveals slides sequentially and hides navigation.

## Image composition

- Hero image: reserve 35–55% negative space for HTML title copy.
- Split slide: use 40/60 or 50/50; direct the subject’s gaze or motion toward the text.
- Full bleed: add a controlled overlay or gradient scrim and verify contrast at the busiest crop.
- Card thumbnails: keep aspect ratios and focal positions consistent.
- Convert every raster asset to WebP before placing it in the deck. Keep SVG for true vector logos, icons, and diagrams.
- Never stretch images. Use `object-fit: cover` only for decorative or safely croppable fields, explicit aspect ratios, and per-image `object-position`.
- Keep decorative art out of the reading order with empty `alt`; give informative images concise meaningful alternatives.

## Default-template escape check

Before the first render, confirm that `assets/runtime-shell.html` supplied only the runtime and did not become the deck's art direction.

- No demo copy remains.
- The demo dark-blue/purple palette is gone unless the topic independently calls for it.
- The three-card sample is not the dominant layout.
- At least five composition families are visible in the storyboard.
- The cover and closing are designed for this subject.
- The deck's visual identity is recognizable with the text blurred.
