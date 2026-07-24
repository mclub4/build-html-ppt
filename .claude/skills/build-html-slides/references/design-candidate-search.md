# Design Candidate Search

Use this step after audience and story routing but before writing the final theme contract. It expands the search space without turning a subject noun into a preset.

## Semantic input

The agent selects these facets from the full request and research context:

- one subject family from `subject-routing.md`;
- one primary communication job;
- luminosity preference: `paper`, `mixed`, `dark`, or `any`;
- density, real-media need, visual variance, and motion from 1 to 10.

Do not derive these values with a substring, regex, BM25, or keyword-only classifier over the raw prompt. The same subject can have different jobs, audiences, evidence, and emotional tone. Make the semantic judgment first, then call the bounded candidate tool.

```bash
python3 scripts/suggest_design_directions.py \
  --subject-family hardware-semiconductor-manufacturing \
  --communication-job research-sharing \
  --luminosity mixed \
  --density 7 --media-need 9 --variance 6 --motion 3 --json
```

The tool returns three deliberately different candidates. Compare all three against the actual audience, available authentic media, writing system, room, and desired pacing. Reject at least one with a concrete reason. The highest numeric score is not an automatic winner, and a named candidate is never mandatory.

For software, architecture, platform, and technical-explainer presentations, the comparison must include materially different body grammars rather than three recolored system diagrams. When available, compare:

- one evidence-led schematic or operational direction;
- one contemporary editorial, geometric, or type-led direction;
- one authentic-interface, documentary, or real-media direction.

Paper Systems is not the automatic answer to a rejected dark-console style. Reject it when it would produce a pale report made from repeated top headings, equal cards, muted green rules, and generic tables. Whatever direction wins must name one distinctive visual motif, one typography contrast, and at least four information-native composition families before HTML authoring.

## Design dials

- `variance 1-3`: highly restrained; repeated alignment is acceptable when information architecture is the point.
- `variance 4-7`: varied composition families with a stable visual system; normal default range.
- `variance 8-10`: expressive scale, asymmetry, collage, or unusual transitions; reserve for a compatible audience and story.
- `motion 1-3`: almost static; simple fades and explanatory reveals.
- `motion 4-7`: purposeful staged transitions and occasional kinetic moments.
- `motion 8-10`: motion-led storytelling; never let animation obscure reading, print, or reduced-motion behavior.
- `density 1-3`: hero, chapter, or keynote pacing.
- `density 4-7`: normal presentation density.
- `density 8-10`: expert review, reference, or evidence-heavy material; split slides before shrinking type.

These dials are internal art-direction constraints, not visible UI controls and not promises that every slide has the same density or motion.

`variance` describes composition change, not decorative noise. A deck with different card counts but the same top-title-plus-panel skeleton still has low variance.

## Candidate data boundary

`design-candidates.json` is an original presentation-specific index. It stores communication jobs, luminosity, density, real-media need, composition families, and cliches to avoid. It does not vendor external style, palette, font, or product-classification data. Add a candidate only when it introduces a genuinely different presentation grammar; do not grow the file into a list of product categories.
