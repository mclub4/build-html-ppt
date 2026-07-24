# Image Generation Capability

Use this reference when original atmosphere, editorial illustration, conceptual scenes, cutouts, textures, or bespoke backgrounds would materially improve the deck.

## Capability Check

Inspect the tools available in the current agent session before planning generated assets. A qualifying tool must generate or edit raster images and return an image file that can be stored with the deck. Image reading, web search, HTML rendering, and text-only tools are not image generators.

- When a generator is available, use it for original non-factual visuals that support a defined slide role.
- When no generator is available, continue with supplied assets, sourced imagery, diagrams, typography, and HTML/CSS composition. Missing image generation does not fail `check_environment.py`.
- If the user explicitly requests generated imagery, or the agreed concept cannot be delivered without it, explain that no image generator is configured and ask whether to continue with sourced visuals or configure a generator.
- Never install a package, add an MCP server, configure credentials, or switch to a paid image service without explicit consent.

Claude Code can inspect rendered PNG captures with its image-reading capability, but a base Claude Code installation does not provide raster image generation. Use a connected plugin, MCP server, or other configured generator when present. Codex may expose ImageGen directly. Gemini CLI capabilities also depend on the tools or extensions configured in the current session. Treat any available generator as one qualifying implementation of this contract rather than a mandatory dependency; never assume one from the platform name alone.

## Truth Boundary

Classify the visual role before invoking a generator:

- `subject`: an existing named person, idol group, character, released game, product, place, event, artwork, organization, or other thing the audience is expected to recognize;
- `evidence`: documentary photography, gameplay or interface screenshots, packaging, archival material, measured results, scientific imagery, or a visual used to prove a factual claim;
- `atmosphere`, `concept`, `scenario`, or `decorative`: non-factual support that establishes mood, explains an abstract idea, depicts a clearly hypothetical situation, or adds texture without claiming authenticity.

Use sourced real material for `subject` and `evidence`. This applies to entertainment and nostalgia decks as strongly as it does to business and science: a fourth-generation girl-group introduction needs actual group/member photography, and a 1990s-2000s game retrospective needs authentic gameplay, title screens, box art, advertisements, hardware, or official key art. Do not generate lookalikes, replacement screenshots, invented game art, or approximate period imagery because it is faster or visually consistent.

Generated imagery may support a cover as atmosphere or concept, but a cover about an existing named subject must also contain an authentic sourced identity anchor. For a fictional scenario, abstract thesis, confidential system, or event that has no documentary image, generation may carry the main visual when the slide makes that status clear. If an essential factual asset cannot be secured, redesign the slide, reduce the claim, or disclose the limitation; never conceal the gap with synthetic media.

Mark every generated raster use with one allowed purpose:

```html
<img src="assets/generated-stage-atmosphere.webp"
     data-media-purpose="atmosphere"
     alt="추상적인 무대 조명 배경">
```

Record it as `source_kind: generated` in `sources.json`. `source_cache.py --check` rejects a generated asset with no declared purpose, a factual `subject` or `evidence` purpose, or an identity-candidate role.

## Generation Rules

- Generate atmosphere, editorial concepts, clearly hypothetical scenes, scene-setting backgrounds, textures, and original illustrative metaphors.
- For abstract mechanisms, compare a generated concept illustration with a diagram, chart, annotated screenshot, and sourced contextual photograph. Use generation when it explains the idea more directly than generic stock and cannot be mistaken for a real interface, product, institution, transaction, person, or evidence state.
- Do not fabricate documentary evidence, product screenshots, logos, interfaces, people, events, charts, or technical states that the audience could mistake for factual material.
- Give every generated image a narrative job and record `source_kind: generated`, the tool/provider, prompt summary, generation time, and local hash in `sources.json`.
- Convert final raster output to WebP while preserving useful source dimensions and aspect ratio.
- Inspect generated images for malformed text, anatomy, logos, watermarks, accidental signatures, unsafe crops, and visual inconsistencies before using them.
