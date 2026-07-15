# Subject Media Strategy

Use this before storyboarding so factual rigor does not accidentally turn a presentation into a text report.

## Classify the visual job semantically

Do not infer from keywords or a fixed topic list. Reason from what the audience needs to see:

1. **Physical or observable subject**: facilities, machinery, products, infrastructure, places, people, organisms, tissue, experiments, clinical or laboratory phenomena. Default to sourced real-world or scientific imagery alongside charts and diagrams.
2. **Interface or process subject**: software behavior, workflows, abstract systems, policies, and operating models. Screenshots, diagrams, charts, and selective contextual photography may be sufficient.
3. **Abstract, confidential, or unavailable subject**: concepts with no honest visual referent, protected systems, or cases where appropriate media cannot be secured. Typography, data, and diagrams may lead, but record the rationale instead of silently omitting imagery.

Full Validation changes assurance depth, provenance, and inspection. It must not remove useful photography or scientific imagery merely because charts and SVGs are easier to verify.

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

## Source and truth rules

- Prefer official corporate or institutional media, government or public archives, open-license scientific repositories, and source publications whose reuse terms fit the distribution context.
- Citation alone does not grant reuse rights. For public or commercial decks, verify the applicable license or use a safer official, licensed, supplied, or original alternative.
- Separate factual evidence from conceptual illustration in captions and presenter notes.
- Generated imagery may establish atmosphere or explain an abstract concept, but it cannot impersonate a real facility, product, experiment, pathology image, scan, patient, or measured result.
- Cache selected assets in `sources.json`; reuse unchanged verified assets on later revisions.

## Review failure

Treat subject-media fit as a visual quality issue. A deck about a materially observable industry, product chain, place, person, experiment, or biological phenomenon should fail review when it is represented almost entirely by text, tables, charts, or generic SVGs despite suitable subject imagery being reasonably available. Do not fail a deliberately abstract or confidential deck when the authoring rationale is sound and the chosen media answer the communication job.
