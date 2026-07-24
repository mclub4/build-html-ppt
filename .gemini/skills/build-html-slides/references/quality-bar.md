# Presentation Quality Bar

Use this reference before storyboarding and again during visual review. It captures the reusable qualities of strong product, entertainment, and technical decks without copying any one deck.

## Aim for outstanding, not merely legal

The deterministic gates in `reviewer-gates.md` prevent defects. They do not produce a good deck, and passing them is not an achievement. Every rule below that narrows the design space exists because it prevents a specific failure; none of them is a reason to reach for the safest available composition. When a rule and an ambitious idea appear to conflict, build the ambitious idea and let the measurement decide — a dark deck, a saturated full-bleed reset, a poster-scale type moment, a framed-card catalog, and an editorial spread are all legitimate when they are chosen for this brief and carry their area. What is never legitimate is a deck that looks careful and says nothing.

## What strong decks do

- Lead with a point of view. Each slide states a claim, decision, tension, or transition instead of naming a topic.
- Build visual rhythm. Alternate image-led, statement, evidence, process, comparison, and decision slides instead of repeating one card grid or one top-headline-plus-panel skeleton.
- Make imagery carry meaning. Product shots prove the object, screenshots prove the experience, people create stakes, and generated scenes establish atmosphere or a chapter change.
- Use one art direction across many compositions. Typography, color roles, line weight, radii, image treatment, and source treatment stay coherent while layouts change.
- Design the ending. The last slide resolves the opening promise and leaves one useful action or memorable statement.
- Design the opening with equal intent. Slide 1 makes the named subject, promise, and visual world recognizable before the audience starts reading body copy.
- Integrate evidence. Sources, dates, caveats, and provenance belong to the composition rather than appearing as an afterthought.
- Route the story for the room. Common stakes and decision context arrive before specialist depth unless technical detail is itself the decision; every named audience sees why the next section matters.

## Storyboard contract

Before writing HTML, make a slide-role table with: slide number, claim, primary and secondary audience, audience question, decision job, detail level, why this information belongs now, composition family, dominant visual, and transition from the previous slide. Read `audience-story-routing.md` when the audience is named or inferable.

For an 8-15 slide deck, normally use at least five composition families from this list:

1. Brand or cinematic cover
2. Thesis or oversized statement
3. Editorial split with meaningful image
4. Full-bleed image with a text-safe field
5. Metric, price, or single-number proof
6. Comparison, matrix, or short table
7. Process, timeline, architecture, or causal diagram
8. Gallery, lineup, or annotated screenshot
9. Chapter break, quote, or tonal reset
10. Audience fit, decision, recommendation, or closing action

Do not use the same dominant composition on three consecutive slides. Change the information shape, not only the background color. Different panel counts still count as the same composition when the headline position, container treatment, and reading path remain unchanged.

A framed card is a legitimate, often excellent composition — the defect is repetition and underfill, never the frame itself. `measure_container_density.js` measures union ink coverage of every layout region, framed or not, so an editorial spread hides an empty region exactly as badly as a card does. Choose the container that serves the content and let the gate judge occupancy.

Every large-area saturated surface needs documented palette provenance and must belong to the subject, identity, semantic system, or sequence rather than acting as isolated novelty.

## Imagery expectations

- Promotional, entertainment, travel, lifestyle, portfolio, and product decks: use meaningful raster imagery across most of the story.
- Unless the user explicitly requests pure HTML or an image-free treatment, perform relevant photo/factual-image discovery before deciding that a deck or chapter should contain no photography. Use only images that earn their place; omit them when they add no information.
- Technical, strategy, market, industrial, and research decks: read `media-strategy.md`. When the subject is physical or observable, combine diagrams and data layouts with sourced product, facility, equipment, infrastructure, microscopy, pathology, medical, laboratory, field, or other subject-specific imagery that establishes what the audience is discussing.
- Full Validation must improve image relevance, provenance, crop, resolution, and captions; it must not remove useful subject imagery merely to make the deck easier to verify.
- A 12-20 slide physical-subject deck often needs four to eight distinct visual anchors across the cover, chapters, major entities, and key mechanisms. Treat this as a planning range, not a quota.
- Use distinct assets for distinct narrative jobs. A different crop of the same image is not a new visual idea.
- Convert every raster deliverable asset to WebP before referencing it in HTML. Keep SVG for logos, icons, and editable vector diagrams.
- Avoid low-resolution thumbnails, screenshots with unreadable embedded text, generic stock filler, and decorative images that do not support the slide claim.
- `media-strategy.md` is the single home for the visual-contribution test, the stock substitution test, and the authenticity rule that keeps generated media out of subject, evidence, and identity roles. Apply it there; this list does not restate it.
- Reject images that do not visibly match the named subject. Character/person decks require canonical-reference comparison as defined in `identity-review.md`; metadata and source tags alone are insufficient.
- Reject unfinished media slots. A label such as `PLACE NOTE`, an empty image frame, a repeated geometric fallback, or generic art standing in for an expected real place/product/person/event image is a blocking placeholder, not intentional visual variety.

## Composition checks

- The eye should find the claim first, evidence second, and source or caveat last.
- Use scale contrast: at least one dominant element per slide. Avoid five equally loud cards.
- Let image crops, diagonal fields, rules, and whitespace create direction. Do not solve every layout with centered content.
- Use deliberate asymmetry when it improves energy, but keep alignment lines obvious.
- Keep sources and controls quiet but readable. They must not compete with the headline or collide with the main composition.
- Use surface changes as chapter punctuation, not random decoration.
- Judge container occupancy, not only alignment: a region that reads as unfinished is unfinished whether it is a card, a column, a spread, or a bare grid track. `measure_container_density.js` reports it as `oversized low-information region` with the region's slide share, ink coverage, character count, largest type size, and content height. Fix it by changing the composition or adding evidence, never by enlarging the box.
- Judge typography as art direction, not only font loading. A single safe sans used with similar width and texture for display, body, metadata, and technical labels is generic unless the layout creates unmistakable role contrast.
- Audience term notes are micro-annotations, not cards. Fail large annotation surfaces, glossary bands, or notes that visually merge with source citations.
- For technology presentations, inspect the presentation-wide visual fingerprint. A dark-led system is valid when deliberately chosen from the audience, emotional tone, pacing, evidence contrast, venue, or subject identity. Repeating near-black or navy surfaces, cyan or acid-green accents, mono micro-labels, glowing nodes, diagonal control panels, and topology motifs merely because the subject is technical is generic template behavior. Vary the evidence form, luminosity, and composition rather than recoloring the same console structure.

## Anti-regression rubric

Score each dimension from 0 to 3 on rendered slides.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Story | disconnected topics | understandable list | coherent arc | memorable argument with payoff |
| Art direction | default template | colors changed only | cohesive but familiar system | distinctive, contemporary, topic-specific visual world |
| Layout rhythm | one repeated layout | changed panel counts on one skeleton | several useful families | deliberate pacing and chapter resets |
| Typography | cramped, generic, or one-role | readable but safe | strong hierarchy and role contrast | expressive, language-aware, and integral to the concept |
| Imagery | subject unseen, absent, or filler | sparse, repetitive, or wrong medium | subject-appropriate real/scientific/diagram coverage | narrative, sourced, well-cropped, varied, and evidentially clear |
| Composition | clipped/underfilled/overfull | mechanically aligned | balanced | confident focal hierarchy and movement |
| Evidence | unsupported or detached | present but weak | integrated sources | evidence strengthens the visual argument |
| Presentation utility | broken or awkward | functional | smooth controls and notes | rehearsal-ready and audience-aware |

This rubric is used only in Full Validation. After the render/fix loop is settled, run `--phase finalize-prepare`. The independent editor first inspects the generated squint contact sheet for deck-wide focal hierarchy, emphasis range, rhythm, and color/density balance, then scores exactly once. Require at least 20/24 with every dimension at least 2. Record the squint verdict, all eight dimensions, the calculated total, a stable independent editor `reviewer_ref`, concrete notes, and the three weakest slides (or every slide when fewer than three) in `review.json`. The squint verdict cannot excuse a full-size text, crop, distortion, overflow, identity, or completion defect. Complete only the generated cross-review batches, then run `--phase finalize-verify`. Quick Draft does not calculate this score. A passing structural validator does not compensate for a failing visual score.

### The score is not the only gate

The numeric total is a floor on overall craft. It cannot absorb a categorical defect, and a strong total must never be used to argue one away. The non-negotiable gates in `reviewer-gates.md` block delivery on a single occurrence at any score — a deck at 21/24 with a repeated slide does not ship. The most important of them for this rubric:

- **A near-duplicate slide pair.** `validate_slide_variety.py` flags a pair only when both slides are substantive (at least 8 structural elements), neither declares an exempt kind (`section`, `divider`, `chapter`, `interstitial`, `transition`, `quote`), the element skeletons are at least `0.90` similar, and the card counts, column counts, and referenced asset sets are all equal. `ERROR: slides A and B are near-duplicate compositions: skeleton similarity 1.00 …` is a blocking failure, not a note for the weakest-slides list. A deliberate twin — a before/after pair, a repeated scoreboard — carries the same non-empty `data-variety-ok` token on both slides, and the editor must say in its notes why that twin is intentional.
- **An unresolved deterministic warning.** A warning closes only with a `CONFIRM` or `REFUTE` observation naming an element and a location. An editor who reads a warning and writes an approval has not closed it.

## Blocking quality failures

- The output still looks like the starter template.
- A technology presentation defaults to a repeated dark-console fingerprint from technical vocabulary alone, without a brief-specific art-direction rationale or enough compositional variation. Darkness itself is not a failure.
- A one-off high-chroma full-slide reset has no subject, brand, media, semantic, or narrative rationale.
- Three or more consecutive slides share the same dominant layout.
- One composition dominates the body, even if each slide changes the number of panels or the accent color.
- A product, game, place, person, or event deck relies mainly on text and generic cards.
- A materially observable industry, product chain, facility, device, experiment, biological phenomenon, or research modality is shown almost entirely through text, tables, charts, and generic SVGs even though suitable subject imagery is reasonably available.
- Generic stock photography occupies main explanatory space while adding only a broad topic mood and no subject identity, evidence, mechanism, or concept.
- A visible audience term note is rendered as a large card or glossary strip, or competes with body copy.
- Prompt residue such as validation mode, slide count, requested workflow, or `개념 강의 + 팀 활동` appears as decorative visible metadata without an audience-facing reason.
- Two substantive slides are near-duplicate compositions, flagged by `validate_slide_variety.py` and not opted out with a matching `data-variety-ok` token on both.
- The cover lacks a clear first-glance identity signal for the named subject, looks like a generic title template, uses a weak or irrelevant visual, traps the title in an oversized empty panel, or crops an identifying feature. A technically valid but merely acceptable cover does not pass when the body is more art-directed.
- The deck has no designed closing payoff.
- A named mixed audience receives a generic topic order, or must endure specialist detail before understanding the shared stakes, decision, or relevance.
- A mixed or company-wide audience encounters a decision-critical unfamiliar acronym or entity with no explanation, or the presentation compensates by covering slides in unnecessary glossary notes.
- Raster assets are not WebP, except that SVG remains preferred for true vector content.
- Reviewers approve from HTML source without inspecting settled rendered slides.
- Full Validation lacks all-slide AI coverage, required adaptive profiles, review-batch membership, concrete observations, stable reviewer references, or passing change-type verdicts.
- Full Validation omits any slide generated in the risk-based `cross_review_batches`, adds unbound substitute records, or uses a cross-reviewer from the primary-reviewer set.
- A named character/person slide lacks grounded identity targets, cue-based identity verdicts, or uses the wrong subject or variant.
- Any slide contains a visible placeholder, temporary/dummy asset, empty media promise, or generic substitute graphic where the composition claims a real subject image. One occurrence blocks delivery regardless of the numeric score.
- Typography remains the neutral runtime-shell stack, bare `system-ui`, or an unrelated generic face instead of a deliberate language- and topic-appropriate display/body system.
- A display title or quote strands one or two Korean characters or punctuation on its final line. Glyph-row collision, text overlap, foreground bite into glyph ink, and navigation coverage are measured by `measure_text_bounds.js` and `measure_geometry.js`; an open warning from either is itself a blocking failure until a `CONFIRM` or `REFUTE` observation closes it.
