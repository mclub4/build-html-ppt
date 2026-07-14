# Image Generation Capability

Use this reference when original atmosphere, editorial illustration, conceptual scenes, cutouts, textures, or bespoke backgrounds would materially improve the deck.

## Capability Check

Inspect the tools available in the current agent session before planning generated assets. A qualifying tool must generate or edit raster images and return an image file that can be stored with the deck. Image reading, web search, HTML rendering, and text-only tools are not image generators.

- When a generator is available, use it for original non-factual visuals that support a defined slide role.
- When no generator is available, continue with supplied assets, sourced imagery, diagrams, typography, and HTML/CSS composition. Missing image generation does not fail `check_environment.py`.
- If the user explicitly requests generated imagery, or the agreed concept cannot be delivered without it, explain that no image generator is configured and ask whether to continue with sourced visuals or configure a generator.
- Never install a package, add an MCP server, configure credentials, or switch to a paid image service without explicit consent.

Claude Code can inspect rendered PNG captures with its image-reading capability, but a base Claude Code installation does not provide raster image generation. Use a connected plugin, MCP server, or other configured generator when present. Codex may expose ImageGen directly; treat it as one qualifying implementation of this contract rather than a mandatory dependency.

## Generation Rules

- Generate atmosphere, editorial concepts, scene-setting backgrounds, textures, and original illustrative metaphors.
- Do not fabricate documentary evidence, product screenshots, logos, interfaces, people, events, charts, or technical states that the audience could mistake for factual material.
- Give every generated image a narrative job and record `source_kind: generated`, the tool/provider, prompt summary, generation time, and local hash in `sources.json`.
- Convert final raster output to WebP while preserving useful source dimensions and aspect ratio.
- Inspect generated images for malformed text, anatomy, logos, watermarks, accidental signatures, unsafe crops, and visual inconsistencies before using them.
