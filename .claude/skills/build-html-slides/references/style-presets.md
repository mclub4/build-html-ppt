# Stage And Layout Reference

Use this file for the canonical 16:9 stage, viewport fitting, media safety, navigation geometry, typography, and density. Theme selection belongs in `theme-playbook.md` and `theme-gallery.md`. Validation modes and profile routing belong only in `validation-contract.md`.

## Canonical Stage

Every presentation uses one logical 1280×720 canvas. The browser may be wider, taller, shorter, zoomed, or partially occupied by browser chrome; the composition remains 16:9 and scales uniformly into the available visual viewport.

Start from `../assets/runtime-shell.html`. Preserve these invariants:

```css
.stage-wrap {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.stage {
  position: absolute;
  width: 1280px;
  height: 720px;
  transform-origin: top left;
}

.slide {
  position: absolute;
  inset: 0;
  overflow: hidden;
  isolation: isolate;
}
```

```js
const STAGE_WIDTH = 1280;
const STAGE_HEIGHT = 720;

function fitStage() {
  const viewport = window.visualViewport;
  const width = viewport?.width ?? document.documentElement.clientWidth;
  const height = viewport?.height ?? document.documentElement.clientHeight;
  const offsetLeft = viewport?.offsetLeft ?? 0;
  const offsetTop = viewport?.offsetTop ?? 0;
  const scale = Math.min(width / STAGE_WIDTH, height / STAGE_HEIGHT);

  stage.style.left = `${offsetLeft + Math.max(0, (width - STAGE_WIDTH * scale) / 2)}px`;
  stage.style.top = `${offsetTop + Math.max(0, (height - STAGE_HEIGHT * scale) / 2)}px`;
  stage.style.transform = `scale(${scale})`;

  nav.style.right = `${Math.max(0, document.documentElement.clientWidth - offsetLeft - width) + 14}px`;
  nav.style.bottom = `${Math.max(0, document.documentElement.clientHeight - offsetTop - height) + 14}px`;
}
```

Listen to window resize/orientation changes and `visualViewport` resize/scroll events. Anchor progress and edge-click regions to the same offsets and dimensions as the stage; do not leave fixed controls at the layout viewport edge during browser zoom. Use `document.documentElement.clientWidth/clientHeight` only as fallback. Do not calculate the stage ratio from `window.innerWidth` or `window.innerHeight` alone.

There is no second fluid `.deck` layout contract. Do not resize each slide to the browser's changing aspect ratio. A 1366×650 viewport shows a centered scaled 16:9 stage with side margins; it does not stretch the composition to 1366×650.

## Required Slide Structure

```html
<section class="slide" data-title="Exact slide title">
  <div class="slide-media" aria-hidden="true">
    <!-- Decorative media only. -->
  </div>
  <div class="slide-content">
    <!-- Copy and meaningful, non-croppable visuals. -->
  </div>
</section>
```

Every slide has exactly one direct `.slide-media` and one direct `.slide-content` child.

```css
.slide-media {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.slide-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
```

Keep controls outside the scaled stage and above it. Do not let decorative pseudo-elements, SVGs, or images cross in front of titles, labels, sources, or controls.

## Resolution Safety Gate

Apply this gate to drafts and final decks:

- the complete 1280×720 stage remains visible inside the actual visual viewport;
- no horizontal or vertical scrolling occurs inside a slide;
- no meaningful text, logo, title art, key visual, diagram, screenshot, badge, or control crosses the logical canvas;
- no meaningful corner element uses a negative offset;
- browser zoom and short-height windows do not cut the stage;
- all raster references are local WebP;
- readable and edge-important media is not cropped;
- navigation numerals and icons remain centered at every page count.

If content does not fit, shorten, split, simplify, or redesign the slide. Do not solve overflow by shrinking the entire deck's typography.

## Media Classification

Classify each image before placement:

| Role | Treatment |
| --- | --- |
| Decorative atmosphere | `cover` is allowed; important edges must not carry meaning |
| Meaningful key visual | `contain`; keep logos, faces, products, UI, title art, and composition edges visible |
| Mixed | covered/softened backdrop plus a contained foreground copy |

Safe mixed pattern:

```html
<div class="slide-media" aria-hidden="true">
  <img class="visual-backdrop" src="key-visual.webp" alt="">
</div>
<div class="slide-content">
  <img class="key-visual" src="key-visual.webp" alt="Meaningful description">
</div>
```

```css
.visual-backdrop {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: blur(18px) brightness(0.56) saturate(0.9);
  transform: scale(1.06);
}

.key-visual {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
```

Never use `cover` for transparent logos, posters, product shots, UI screenshots, diagrams, game/anime title art, or character compositions unless every cropped edge is deliberately disposable.

## Logical Canvas Typography

### Automatic type direction

Choose the type system without asking a separate font question unless the user supplied brand rules or requests control. Infer it from language, subject, audience, and tone, then declare and apply `--font-display`, `--font-body`, and `--font-mono`. The runtime shell's neutral Korean-safe stack is only a fallback; a finished deck must make a deliberate choice and must not reduce typography to bare `system-ui`.

Useful starting directions, not fixed templates:

| Deck character | Display direction | Body/data direction |
| --- | --- | --- |
| Consumer travel magazine | Bold contemporary Korean sans for city, food, and itinerary covers; serif/sans editorial contrast only when the destination story benefits from it | Pretendard, SUIT, or Noto Sans KR |
| Heritage, reflective travel, culture | MaruBuri or Noto Serif KR when warmth, history, or literary pacing matters; a restrained grotesk for contemporary treatment | Pretendard, SUIT, or Noto Sans KR |
| Finance, stablecoin, enterprise | IBM Plex Sans KR, Pretendard, or SUIT with firm numeric hierarchy | Same family or Noto Sans KR; IBM Plex Mono for code/addresses |
| Product, technology, strategy | Pretendard, SUIT, Noto Sans KR, or another clean humanist sans | Same family with distinct weight/width; JetBrains Mono or IBM Plex Mono only for technical tokens |
| Game, anime, entertainment | One topic-appropriate expressive display face for short headlines | Pretendard, SUIT, or Noto Sans KR for all explanatory copy |
| Premium, fashion, hospitality | An elegant licensed serif or high-contrast display face | A quiet sans with compatible Korean metrics |

Test the exact Korean/Latin/numeral mix before committing. Use no more than two primary families plus one mono family. A novelty face belongs only in short display copy, never paragraphs or tables. When portability requires bundled fonts, use local WOFF2 files with redistribution-compatible licenses and retain their license/credit; otherwise use an intentional cross-platform fallback stack. Never load a remote font at runtime.

Use values appropriate to the 1280×720 logical canvas:

- display title: typically 44–68px;
- section title: typically 32–48px;
- body: typically 18–24px;
- support/source text: typically 13–16px;
- code: at least 13px.

These values scale with the stage. Do not use viewport-width font sizing that changes the internal hierarchy independently of the stage scale.

Check Korean glyph quality, punctuation, numerals, and Latin/Korean mixing. Avoid unrelated fallback faces. Keep letter spacing at zero unless a short all-caps/mono label has a specific reason.

### Rendered line safety

Validate settled browser lines after local fonts finish loading. Element width and `scrollWidth` are insufficient because broken line composition can remain inside its box.

- Do not leave only one or two Korean characters, a sentence ending such as `다.`, or closing punctuation on the last line of a display title or quote. Rephrase, rebalance the text box, reduce the display size, or add a phrase-boundary break.
- Set Korean display line-height from the actual face and weight. Start with enough separation for the font's glyph metrics; never tighten multiline copy below `0.9` without rendered proof, and reject any visible row collision regardless of the declared CSS value.
- Keep footer copy, credits, and captions outside the persistent navigation rectangle at every retained profile.
- `measure_text_bounds.js` reconstructs Chromium lines, checks Korean final-line fragments, line advance, sibling text intersections, and navigation occlusion under the existing `text_bounds` automation gate.
- `data-line-break-ok` is limited to an intentional one- or two-character poster/chapter treatment that remains visibly balanced. It bypasses only the orphan-line heuristic, never collision or bounds checks. `data-text-overlap-ok` is limited to deliberate legible overprint and still requires AI inspection; do not use either attribute to silence an accidental layout defect.

## Density

Use these as warning thresholds, not mechanical templates:

| Slide job | Typical limit |
| --- | --- |
| Cover | one title, one supporting line, optional mark |
| Argument | one claim plus two to four evidence groups |
| Comparison | two to four comparable columns/rows |
| Code | roughly 8–12 readable lines |
| Quote | one quote plus attribution/context |
| Image-led | one dominant image plus minimal copy |

Split a slide when the audience must read and compare too many independent ideas at once.

### Container Fit

Whitespace and empty boxes are not interchangeable. Whitespace can connect a focal element to the slide edge and establish hierarchy. A large filled or bordered rectangle with little content reads as unfinished UI.

- Size cards and panels from their content instead of forcing equal heights by default.
- A short label, one sentence, or one small bullet group should normally remain unboxed, use a compact content-sized surface, or sit beside meaningful evidence.
- Large surfaces must earn their area through comparison, grouping, interaction, a chart, a diagram, an image, an annotated object, or a deliberate hero/chapter composition.
- Do not use a tall card merely to occupy an empty grid track. Change the composition: open typography, editorial split, dominant image, metric cluster, timeline, rule-based list, or asymmetric evidence layout.
- Do not add low-contrast rectangles, outlines, empty slots, or decorative boxes that resemble missing content.
- `data-density-ignore` is reserved for intentional hero/chapter whitespace or fixed-format UI mockups. The rendered slide must still look complete, and the visual reviewer must explain why the empty area is intentional.

## Navigation Panel

Keep the runtime order exactly:

1. previous icon;
2. three-cell current input / separator / total counter;
3. next icon;
4. fullscreen icon.

Theme only `--nav-surface`, `--nav-border`, `--nav-ink`, `--nav-muted`, `--nav-accent`, and `--nav-hover` unless a different interaction model is requested.

The page input is part of the counter, not a separate bordered card. Give current, separator, and total the same explicit height, zero vertical padding, `line-height: 1`, grid/flex centering, and tabular numerals. Keep their centers within 1.5px. Do not show slide titles or truncated labels in the control panel.

Use familiar icons with accessible names. Every visible interactive element must work, expose a focus state, and use a semantic button or link.

## Motion And Print

- Use restrained opacity and small transforms around 300–600ms.
- Respect `prefers-reduced-motion`.
- Keep authored animation in the delivered HTML; Chromium validation disables it only in the capture context.
- Print each logical slide at 1280×720, one slide per page, with controls and progress hidden.

## Validation Profiles

Do not redefine profile sizes here or in deck-specific instructions. Use `validation-contract.md` and `scripts/render_slides.js` as the single profile contract.

## Anti-Patterns

- raw 1920×1080 or 1280×720 stages without a visualViewport fitter;
- fluid slides that change composition aspect ratio with the browser;
- `window.innerWidth`/`innerHeight` as the only scale source;
- meaningful media with negative offsets or `cover` cropping;
- raster images hidden in CSS backgrounds;
- one large rounded panel around an entire slide;
- oversized low-information cards, empty outlined rectangles, and equal-height boxes containing only a few words;
- repeated three-card grids as the default composition;
- type shrunk below readable size to avoid splitting content;
- a display title or quote with a one- or two-character Korean orphan line, punctuation-only line, colliding glyph rows, or text hidden under navigation;
- page counters centered with padding guesses or transforms;
- a starter palette treated as the deck's art direction.
