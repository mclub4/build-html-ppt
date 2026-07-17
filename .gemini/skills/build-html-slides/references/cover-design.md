# Cover Design Contract

Treat slide 1 as the highest-priority art-direction decision in the deck. The cover must establish subject identity, audience promise, and visual tone within roughly three seconds. It is not a generic title page and must not be the least-developed slide because the body took longer.

## Plan Before Building

Before implementing the cover, write a private one-line brief containing:

- the literal subject, product, place, person, event, or decision the audience must recognize;
- the opening promise or tension that makes the next slide worth seeing;
- one dominant visual anchor;
- display-type character and title line count;
- composition direction, focal point, and required safe area;
- any logo, date, presenter, confidentiality, or source metadata that genuinely belongs.

Consider at least two materially different cover directions in planning, such as full-bleed editorial image versus contained object composition, or cinematic scene versus typographic thesis. Choose the direction that best fits the audience and subject. This comparison does not require two finished renders.

## Visual Standard

- Make the named subject a first-glance signal. Use its literal name or offer as the primary title; put explanatory value in supporting copy.
- Give the cover one dominant focal hierarchy: subject or key visual first, title immediately legible, secondary metadata quiet.
- For an existing physical, observable, branded, entertainment, travel, scientific, or person-led subject, use the strongest accurate official, supplied, licensed, or sourced visual as the identity anchor. Do not replace it with generated lookalike art, generic geometry, a chart, or an empty mood field.
- Generated scenery, texture, or conceptual art may support the cover when it cannot be mistaken for the real subject. It may lead only for an abstract thesis, confidential system, or clearly hypothetical scenario with no honest documentary referent.
- Use logos, posters, title art, products, screenshots, diagrams, and character compositions with `contain` or a deliberately protected foreground. A covered backdrop may support them, but must not crop the identifying edges.
- For abstract or confidential topics, earn a typographic or diagrammatic cover with a distinctive thesis, composition, and visual system. A large empty rectangle with a title is not a concept.
- Avoid dashboards, repeated card grids, agenda lists, multi-column reports, and oversized rounded title panels on slide 1 unless the format itself is the subject.
- Keep the title to a deliberate one-to-three-line composition where possible. Fix copy width, line breaks, type size, or font choice when Korean endings, punctuation, proper nouns, or brand names wrap awkwardly.
- Keep navigation, credits, logos, and source metadata outside the title and focal-image safety zones.

## Cover Review Gate

The renderer treats slide 1 as visual-critical in every rendered mode. AI must open every generated profile for the cover, even in Quick Draft. Review it as a cover, not merely as a slide whose elements fit inside bounds.

After the first settled render, open the cover at full size and perform a dedicated refinement pass. Check authentic subject recognition, focal crop, image resolution, title line composition, display/body contrast, color integration, depth and edge treatment, logo and metadata placement, source treatment, and navigation clearance. Resolve weak details before reviewing ordinary slides; the cover should feel at least as intentional as the strongest body slide.

Fail the cover when any of these is true:

- the named subject is ambiguous or visually subordinate;
- an existing named subject is represented only by generated or generic imagery without an authentic identity anchor;
- the title could belong to an unrelated generic deck;
- the key visual is weak, irrelevant, blurry, visibly upscaled, or incorrectly cropped;
- a logo, face, product edge, title art, map, or identifying feature is cut off;
- title wrapping, contrast, or hierarchy fails at normal, short, or zoom150;
- the composition looks like an unfinished placeholder, empty panel, dashboard, or body slide;
- persistent navigation competes with the title, credit, logo, or key visual;
- the opening promise and the next slide have no coherent handoff.

Do not approve the cover only because geometry passes. If slide 1 is merely acceptable while the rest of the deck is art-directed, revise it before delivery.
