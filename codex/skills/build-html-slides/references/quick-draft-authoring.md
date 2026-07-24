# Quick Draft Authoring

Quick Draft is the speed-first creation path. For an ordinary 10-15 slide presentation, aim for roughly 10-20 minutes under normal local conditions. This is a planning target, not a timeout or a quality claim.

## Reuse Before Custom Work

- Copy `assets/runtime-shell.html`; never recreate the stage fitter, navigation, keyboard controls, or print runtime.
- Freeze the shared color tokens, typography, navigation treatment, and spacing scale once near the start.
- Use four or five reusable composition families for the ordinary body:
  - hero or full-bleed;
  - split media and copy;
  - editorial evidence;
  - columns or comparison;
  - gallery, timeline, or sequence.
- The cover, closing, and at most two signature slides may receive bespoke composition or CSS.
- Build the other slides from shared family classes and small modifiers. Do not write hundreds of lines of slide-specific CSS or create a new layout system for every slide.
- Reuse composition grammar, not empty card grids. A shared family may change content density, image proportion, alignment, and emphasis while retaining its tested structure.

## Bound The Expensive Passes

- For an ordinary 10-15 slide presentation, seek roughly 6-10 strong factual or atmospheric images when imagery helps. Stop once identity, evidence, context, and rhythm needs are covered.
- Explicit media-heavy, catalog, portfolio, artwork, or fan-art requests may require more discovery. Keep that research intentional instead of widening every query indefinitely.
- Settle visible copy and notes before running `humanize-korean`, then perform one combined pass and inspect the semantic diff.
- Write concise notes for roughly 30-60 seconds of delivery: purpose, natural talk track, emphasis, transition, and only necessary source or caveat guidance.

## Stop Condition

Deliver the HTML, notes, sources cache, and local assets immediately after authoring. Do not render, open a browser, run validators, create review evidence, calculate a score, or request another reviewer. State clearly that Quick Draft was not rendered or validated.

If the user explicitly requests every slide to have unique art direction, a very large image collection, or exhaustive research, explain that the turnaround may approach Full Validation authoring time even though validation remains disabled.
