# Quick Draft Authoring

Quick Draft is the speed-first creation path. **15 minutes maximum** for an ordinary 10-15 slide presentation. That is a ceiling, not a quality claim: when the work will not fit, cut scope — fewer images, fewer bespoke slides, shorter notes — rather than running long.

A workable split of the 15 minutes: 3 for storyboard and theme contract, 5 for image discovery, 5 for build, 2 for notes and the Korean polishing pass.

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

- **Image discovery is capped at 5 minutes.** Place 6-10 images. Download at most 12 originals. Full-size-inspect only the ones you intend to place; judge the rest from the source page listing and its reported dimensions. `asset-discovery.md` describes strict-mode discovery for Full Validation — its "collect more candidates than the deck needs and inspect every downloaded original at full size" instruction does not apply here and will not fit in this budget.
- One search pass per visual role. Take the first candidate that clears the lightweight gate in `high-volume-media-workflow.md` step 2 — correct subject, recorded source page, enough pixels for the slot, no obvious disqualifier — and move on. Do not compare alternatives you already have a usable answer for.
- Count only images that pass the visual-contribution and stock-substitution tests in `media-strategy.md`. Do not fill the image target with interchangeable stock photography.
- Explicit media-heavy, catalog, portfolio, artwork, or fan-art requests raise the roster, not the clock: use the batch contact-sheet accelerator once the numeric trigger in `high-volume-media-workflow.md` is met, and state at delivery that discovery was bounded.
- Settle visible copy and notes before running `humanize-korean`, then perform one combined pass and inspect the semantic diff.
- Write concise notes for roughly 30-60 seconds of delivery: purpose, natural talk track, emphasis, transition, and only necessary source or caveat guidance.
- Keep production-language fragments out of visible slides. Validation mode, slide count, requested workflow, and phrases such as `개념 강의 + 팀 활동` remain private unless the audience needs them as logistics.
- Quick Draft has no rendered navigation check. Place every footer definition, source, logo, and caption outside the lower-right navigation exclusion zone during authoring; use `.nav-safe-note` for footer term notes.

## Stop Condition

Deliver the HTML, notes, sources cache, and local assets immediately after authoring. Do not render, open a browser, run validators, create review evidence, calculate a score, or request another reviewer. State clearly that Quick Draft was not rendered or validated.

If the user explicitly requests every slide to have unique art direction, a very large image collection, or exhaustive research, say up front that this exceeds the 15-minute ceiling, name the expected duration, and let the user decide before starting. Do not silently overrun.
