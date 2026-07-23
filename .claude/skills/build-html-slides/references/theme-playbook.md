# Theme Playbook

## Theme inference

Read `theme-gallery.md`, then define six decisions before styling: three mood adjectives; display and body typography; palette roles; shape language; media treatment; and motion character. Write them as a one-line theme contract before coding.

| Direction | Best for | Visual grammar |
|---|---|---|
| Destination magazine | consumer travel guides, itineraries, city and food recommendations | destination-derived color, bold cover hierarchy, editorial photo pacing, route maps, neighborhood spreads, compact practical metadata |
| Paper systems | architecture decisions, standards, platform strategy, technical research | cool paper, deep ink, humanist type, annotated schematics, decision matrices, open comparisons |
| Interface lab | developer tools, testing, APIs, coding workflows | bright neutral or brand-led surfaces, authentic interface crops, code diffs, traces, numbered experiments |
| Human infrastructure | migrations, incidents, developer experience, hardware ecosystems | documentary photography, paper or steel neutrals, handoff maps, timelines, operational evidence |
| Technical night | live operations, security response, runtime monitoring | near-black/navy, restrained status color, monospace evidence, control states and topology; never the generic technology default |
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
| Idol editorial index | multi-act or multi-member orientation, chronology, comparison, and curation | authentic photo index, bold grotesk hierarchy, serif contrast, mono metadata, act-specific accents, timeline and listening map |

These are routing hints, not fixed presets. A topic may support several valid directions depending on audience and communication job, and the best answer may be a bespoke contract not named here. Use the larger gallery for additional vocabulary including Neo Brutalist, Riso Zine, Scientific Atlas, Blueprint Workshop, Documentary Photo Essay, Spatial Interface, Ledger Trust, and Idol Editorial Index. Mix only compatible attributes, and do not turn signature-slide lists into mandatory checklists.

### Idol routing

Treat idol presentations as different editorial jobs rather than one visual genre:

| Communication job | Possible direction | Typical treatment |
|---|---|---|
| Multi-group generation guide, lineup overview, or listening map | Idol Editorial Index | authentic photo index, chronology, profile spreads, source labels, act-specific accent shifts |
| Single-act personality, fandom, relationship, or meme guide | Bespoke fan-zine, Editorial Culture, Riso Zine, or Playful Modular traits | closer photography, quotes, artifacts, fan-language rhythm, scrapbook cues only when they serve the story |
| Premium comeback, concept launch, or sales promotion | Editorial Culture, Product Keynote, Cinematic Noir, or a bespoke brand direction | official key art, campaign hierarchy, dramatic reveal, concise benefit or concept claims |
| History, legacy, archive, or industry analysis | Museum Catalog, Documentary Photo Essay, Data Newsroom, or a bespoke research direction | chronology, archival evidence, dated captions, comparisons, restrained interpretation |

Do not select Idol Editorial Index merely because an idol appears. Preserve the act's own visual identity and let the audience, purpose, evidence, and available photography determine the final system.

### Travel routing

Treat travel as a set of editorial jobs, not one visual theme:

| Communication job | Primary direction | Typical treatment |
|---|---|---|
| Leisure guide, itinerary, city or food recommendations | Destination Magazine | travel-magazine cover hierarchy, destination photography, editorial spreads, route and practical-info modules |
| Premium hotel, resort, ryokan, wellness stay | Soft Kinetic or Museum Catalog | quiet image-led pacing, material and service details, elegant but readable typography |
| Expedition, ecology, research trip, first-person observations | Field Notes | field evidence, annotated maps, observation-to-insight sequence, restrained notebook cues |
| Reportage, oral history, heritage, community story | Documentary Photo Essay | full-frame documentary photography, place/date slugs, testimony, map interludes |
| Tourism campaign or destination launch | Destination Magazine with Product Keynote accents | aspirational hero imagery, memorable claims, seasonal reasons to visit, decisive closing |

For an ordinary Tokyo, Kyoto, Osaka, or regional Japan guide, start from Destination Magazine unless the brief clearly asks for luxury hospitality, documentary reporting, or field research. Infer the palette from the actual season and photographs. A contemporary city guide may use bold grotesk display type, while a heritage-focused guide may use a serif/sans contrast; Japanese travel does not automatically mean dark green, off-white, or a serif headline.

## Theme contract

Record this compact internal spec before implementation:

```text
Mood: precise / open / humane
Type: confident Korean humanist sans display + readable sans body + mono only for code and identifiers
Palette roles: cool paper / deep ink / cobalt decision / coral risk
Shape: open alignment, thin rules, framed evidence only where boundaries carry meaning
Media: authentic interface or facility WebP + editable SVG systems diagrams
Motion: short directional fades; evidence appears in explanatory order
```

Do not select a theme by swapping color tokens on the starter template. Change typography, spacing, image treatment, composition families, source treatment, and motion together.

### Technology routing

Technology is a subject domain, not a visual theme. Before styling a technology deck, compare three materially different directions:

1. a light or paper-led editorial system;
2. an authentic-media system built around real interfaces, equipment, facilities, products, or people when relevant;
3. a schematic or operational system, using a dark command-room surface only when the communication job benefits from it.

| Communication job | Strong starting directions |
|---|---|
| Executive decision, ADR, platform strategy | Paper Systems, Swiss Signal, Minimal Corporate, Data Newsroom |
| Developer education, testing, API, coding workflow | Interface Lab, Bright Learning, Playful Modular, Product Keynote |
| Migration, developer experience, incident learning, operating model | Human Infrastructure, Documentary Photo Essay, Data Newsroom |
| Hardware, semiconductor, robotics, manufacturing | Human Infrastructure, Blueprint Workshop, Scientific Atlas |
| Benchmark, research, performance evidence | Data Newsroom, Scientific Atlas, Paper Systems |
| Live operations, security response, runtime monitoring | Mission Control or Technical Night |
| Developer-tool launch or product promotion | Product Keynote, Interface Lab, Spatial Interface |

Do not infer the recurring fingerprint `near-black or navy + cyan or acid green + mono micro-labels + glowing nodes + diagonal panel` merely because the title contains AI, cloud, CNI, MSA, testing, agent, RAG, architecture, or code. Mission Control and Technical Night require an operational, monitoring, incident, security, or command context. Otherwise prefer a paper-led or mixed-surface direction unless the subject's real brand identity supports darkness.

For technology decks, extend the theme contract with:

```text
Luminosity: paper-led / mixed / dark-led - reason
Distinctive evidence: the real media or information shape that prevents a generic tech-console look
```

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
- No large sparse card or placeholder-like empty shape remains; every large surface carries proportionate information or a deliberate visual role.
- No `PLACE NOTE`, image-here label, temporary/dummy media, empty frame, or generic replacement graphic remains. If a promised factual image is unavailable, redesign the composition instead of styling the missing slot.
- Display and body fonts were deliberately selected for this subject and writing system; the neutral runtime-shell font stack is no longer the art direction.
- At least five composition families are visible in the storyboard.
- The cover and closing are designed for this subject.
- The deck's visual identity is recognizable with the text blurred.
