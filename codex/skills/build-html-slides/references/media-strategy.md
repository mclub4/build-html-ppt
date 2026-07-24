# Subject Media Strategy

Use this before storyboarding so factual rigor does not accidentally turn a presentation into a text report.

## Default media decision

Unless the user explicitly asks for pure HTML, no photography, no external images, or a typography/diagram-only treatment, perform a bounded search for relevant sourced photographs or factual imagery before finalizing the storyboard. Do not ask separately whether to search; visual discovery is part of ordinary deck planning.

This is a relevance rule, not an image quota. Select photographs when they improve subject recognition, factual grounding, scale, process context, human stakes, atmosphere, or visual rhythm. Omit them on slides where a chart, screenshot, diagram, generated concept illustration, typographic statement, or whitespace communicates the claim better. A decision to use no photography should follow a semantic fit judgment, not convenience, verification cost, or failure to search. A sourced photograph is not automatically more useful than a generated concept visual merely because it is real.

## Classify the visual job semantically

Do not infer from keywords or a fixed topic list. Reason from what the audience needs to see:

1. **Physical or observable subject**: facilities, machinery, products, infrastructure, places, people, organisms, tissue, experiments, clinical or laboratory phenomena. Default to sourced real-world or scientific imagery alongside charts and diagrams.
2. **Interface or process subject**: software behavior, workflows, abstract systems, policies, and operating models. Screenshots, diagrams, charts, and selective contextual photography may be sufficient.
3. **Abstract, confidential, or unavailable subject**: concepts with no honest visual referent, protected systems, explicit pure-HTML requests, or cases where appropriate media cannot be secured. Typography, data, and diagrams may lead, but record the rationale instead of silently omitting imagery.

Full Validation changes assurance depth, provenance, and inspection. It must not remove useful photography or scientific imagery merely because charts and SVGs are easier to verify.

## Require a visual contribution

Before selecting an asset, assign the slide's primary visual job:

- **evidence:** proves a factual claim or shows a measured, documented, or observed state;
- **identity:** lets the audience recognize a real person, place, product, organization, work, interface, or object;
- **mechanism:** explains a process, relationship, system, comparison, or causal model;
- **concept:** makes an abstract idea understandable without pretending to be factual evidence;
- **atmosphere:** establishes emotion, setting, or chapter rhythm without carrying the claim.

For every candidate, state what the audience learns from it that the headline and body do not already provide. Reject or demote it when that answer is vague.

Apply the **stock substitution test**: if an unrelated image from the same broad stock category could replace the candidate without weakening or changing the slide's meaning, the image is generic atmosphere rather than evidence, identity, mechanism, or concept. Do not use such an image as the main explanatory visual. Keep it only when atmosphere is the deliberate job, usually on a cover, chapter transition, or closing, and when it strengthens the presentation's art direction.

Compare media types before committing:

| Communication need | Prefer |
|---|---|
| real subject, product, place, interface, facility, event, or documented outcome | sourced authentic photo, screenshot, archival, or scientific image |
| flow, relationship, architecture, comparison, or measured pattern | diagram, chart, annotated screenshot, or table |
| abstract mechanism with no honest documentary image | clearly labeled generated concept illustration or slide-native explanatory visual |
| emotional framing or chapter rhythm | sourced or generated atmosphere with no factual implication |

Do not count an image toward coverage merely because it is present. An image earns its area only when its role and claim contribution are clear.

## Plan coverage, not decoration

For a physical or observable subject:

- establish the real subject on the cover or within the opening sequence;
- assign factual imagery to the major entities, facilities, instruments, materials, organisms, or research modalities that the audience must recognize;
- alternate image-led context with chart-, table-, and diagram-led explanation;
- let data slides remain data-first when a photograph would add no information;
- use images as evidence, identification, scale, human stakes, process context, or chapter rhythm, never as generic filler.

For a 12-20 slide deck, four to eight distinct sourced visual anchors is a useful planning range when the subject materially benefits from real imagery. This is not a quota or validator threshold. Use fewer when each image carries the story; use more only when additional assets add distinct information without expanding research indefinitely.

## Domain examples

### AI-driven semiconductor market change

Charts should explain market movement, but sourced visuals should establish the physical value chain: wafer fabrication, advanced packaging or HBM, GPU accelerators and servers, EUV or other critical equipment, data-center racks, power delivery, and cooling. On company-specific slides, prefer the relevant company's official newsroom, media kit, product, facility, or event imagery. A generic circuit-board background is not a substitute.

### Cancer treatment research and development

Use the modality that supports the claim: microscopy, histology or pathology, medical imaging, immune-cell or tumor-microenvironment imagery, therapy delivery, laboratory instrumentation, or a sourced clinical/research setting. Record specimen, stain, modality, scale, and study context when known. Do not present generated cells, tumors, scans, or treatment scenes as research evidence. Patient imagery must be ethically sourced, non-exploitative, and necessary to the story.

### Existing entertainment catalog or nostalgia retrospective

When introducing real idol generations, artists, films, animation, released games, consoles, magazines, toys, or past campaigns, the named items are factual subjects. Give each prominently introduced item an authentic visual such as an official or supplied photo, performance still, title screen, gameplay capture, box art, advertisement, hardware photo, logo, poster, or properly attributed fan work when appropriate to the story and distribution context. A generated idol, game screenshot, package, poster, or period imitation is not an acceptable substitute. Use generation only for clearly non-factual atmosphere, chapter transitions, hypothetical scenes, or decorative support.

### Financial education or fintech explainer

Use real interfaces, payment devices, institutions, or customer settings when the slide is about an actual product, service, adoption context, or documented behavior. Do not use a generic payment-terminal, student-with-phone, handshake, padlock, or trading-screen stock photo as the main visual for settlement, open banking, alternative-data scoring, fraud detection, consent, or consumer protection when it explains none of those mechanisms. Prefer annotated real interfaces, payment-flow diagrams, data-permission maps, normal-versus-suspicious pattern comparisons, and layered trust or recovery models. A generated concept illustration may lead when it explains an abstract mechanism more clearly and is visibly non-factual; it must not invent a real app, transaction, institution, or evidence state.

## Source and truth rules

- Prefer official corporate or institutional media, government or public archives, open-license scientific repositories, and source publications whose reuse terms fit the distribution context.
- Citation alone does not grant reuse rights. For public or commercial decks, verify the applicable license or use a safer official, licensed, supplied, or original alternative.
- Separate factual evidence from conceptual illustration in captions and presenter notes.
- Generated imagery may establish atmosphere or explain an abstract concept, but it cannot impersonate a real facility, product, experiment, pathology image, scan, patient, or measured result.
- For every generated raster, declare `data-media-purpose` as `atmosphere`, `concept`, `scenario`, or `decorative`. Existing named subjects and documentary evidence remain sourced even when a generated alternative would be faster or more stylistically uniform.
- Cache selected assets in `sources.json`; reuse unchanged verified assets on later revisions.

## Review failure

Treat subject-media fit and claim contribution as visual quality issues. A deck about a materially observable industry, product chain, place, person, experiment, or biological phenomenon should fail review when it is represented almost entirely by text, tables, charts, or generic SVGs despite suitable subject imagery being reasonably available. It should also fail when generic stock photographs occupy explanatory space but do not identify the subject, prove the claim, explain the mechanism, or provide a deliberate atmospheric role. Do not fail a deliberately abstract or confidential deck when the authoring rationale is sound and the chosen media answer the communication job.
