# Presentation Quality Bar

Use this reference before storyboarding and again during visual review. It captures the reusable qualities of strong product, entertainment, and technical decks without copying any one deck.

## What strong decks do

- Lead with a point of view. Each slide states a claim, decision, tension, or transition instead of naming a topic.
- Build visual rhythm. Alternate image-led, statement, evidence, process, comparison, and decision slides instead of repeating one card grid.
- Make imagery carry meaning. Product shots prove the object, screenshots prove the experience, people create stakes, and generated scenes establish atmosphere or a chapter change.
- Use one art direction across many compositions. Typography, color roles, line weight, radii, image treatment, and source treatment stay coherent while layouts change.
- Design the ending. The last slide resolves the opening promise and leaves one useful action or memorable statement.
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

Do not use the same dominant composition on three consecutive slides. Do not use a generic card grid more than twice in a 10-slide deck unless the subject is explicitly a catalog or dashboard. Change the information shape, not only the background color.

## Imagery expectations

- Promotional, entertainment, travel, lifestyle, portfolio, and product decks: use meaningful raster imagery across most of the story.
- Technical and strategy decks: combine diagrams and data layouts with enough factual or atmospheric imagery to establish stakes and provide chapter rhythm.
- Use distinct assets for distinct narrative jobs. A different crop of the same image is not a new visual idea.
- Convert every raster deliverable asset to WebP before referencing it in HTML. Keep SVG for logos, icons, and editable vector diagrams.
- Avoid low-resolution thumbnails, screenshots with unreadable embedded text, generic stock filler, and decorative images that do not support the slide claim.
- Reject images that do not visibly match the named subject. Character/person decks require canonical-reference comparison as defined in `identity-review.md`; metadata and source tags alone are insufficient.

## Composition checks

- The eye should find the claim first, evidence second, and source or caveat last.
- Use scale contrast: at least one dominant element per slide. Avoid five equally loud cards.
- Let image crops, diagonal fields, rules, and whitespace create direction. Do not solve every layout with centered content.
- Use deliberate asymmetry when it improves energy, but keep alignment lines obvious.
- Keep sources and controls quiet but readable. They must not compete with the headline or collide with the main composition.
- Use surface changes as chapter punctuation, not random decoration.
- Judge container occupancy, not only alignment. Large panels containing a few words, short bullets floating at the top of tall cards, and empty decorative rectangles are unfinished compositions. Use open layout or add evidence instead of enlarging the box.

## Anti-regression rubric

Score each dimension from 0 to 3 on rendered slides.

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| Story | disconnected topics | understandable list | coherent arc | memorable argument with payoff |
| Art direction | default template | colors changed only | cohesive system | distinctive, topic-specific visual world |
| Layout rhythm | one repeated layout | minor variation | several useful families | deliberate pacing and chapter resets |
| Typography | cramped or generic | readable | strong hierarchy | expressive and language-aware |
| Imagery | absent or filler | sparse/repetitive | purposeful | narrative, sourced, well-cropped, and varied |
| Composition | clipped/underfilled/overfull | mechanically aligned | balanced | confident focal hierarchy and movement |
| Evidence | unsupported or detached | present but weak | integrated sources | evidence strengthens the visual argument |
| Presentation utility | broken or awkward | functional | smooth controls and notes | rehearsal-ready and audience-aware |

This rubric is used only in Full Validation. After the render/fix loop is settled, run `--finalize` and score exactly once. Require at least 20/24 with every dimension at least 2. Record all eight dimensions, the calculated total, a stable independent editor `reviewer_ref`, concrete notes, and the three weakest slides (or every slide when fewer than three) in `review.json`. Quick Draft does not calculate this score. A passing structural validator does not compensate for a failing visual score.

## Blocking quality failures

- The output still looks like the starter template.
- Three or more consecutive slides share the same dominant layout.
- A product, game, place, person, or event deck relies mainly on text and generic cards.
- A rendered slide contains oversized low-information surfaces or decorative empty boxes that are not justified by a hero, chapter, comparison, interaction, or fixed-format visual.
- The cover lacks a clear first-viewport identity signal for the named subject.
- The deck has no designed closing payoff.
- A named mixed audience receives a generic topic order, or must endure specialist detail before understanding the shared stakes, decision, or relevance.
- Raster assets are not WebP, except that SVG remains preferred for true vector content.
- Reviewers approve from HTML source without inspecting settled rendered slides.
- Full Validation lacks all-slide AI coverage, or a Quick Draft AI-routed slide lacks its adaptive profiles, review-batch membership, concrete observation, stable reviewer reference, and passing change-type verdict.
- Full Validation lacks an independent hash-bound cross-review for the cover, closing, or a slide explicitly marked `data-visual-critical="true"`.
- A named character/person slide lacks grounded identity targets, cue-based identity verdicts, or uses the wrong subject or variant.
