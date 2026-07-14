# Style Presets Reference

Curated visual styles for `build-html-slides`.

Use this file for:
- the mandatory viewport-fitting CSS base
- the no-crop slide shell and media placement rules
- preset selection and mood mapping
- CSS gotchas and validation rules

Use this reference for structural safety, not as an art-direction substitute. Choose imagery, diagrams, and illustration according to the subject and `theme-gallery.md`; promotional and narrative decks should not collapse into abstract shapes and generic cards.

## Viewport Fit Is Non-Negotiable

Every slide must fully fit in one viewport.

### Golden Rule

```text
Each slide = exactly one viewport height.
Too much content = split into more slides.
Never scroll inside a slide.
Never rely on monitor resolution, browser chrome height, or a fixed 1920x1080 canvas.
```

### Resolution Safety Gate

Apply this gate to single-slide previews, rough drafts, and final decks. A deck that fails any item is not ready to show.

- No horizontal page scroll at any viewport size.
- No vertical page scroll inside a slide; navigation between slides is the only vertical movement.
- No meaningful text, logo, title art, diagram, screenshot, badge, or slide control crosses any viewport edge.
- No meaningful corner element uses a negative offset.
- No slide depends on fixed `width: 1920px`, `height: 1080px`, `min-width: 1920px`, or unscaled 16:9 wrappers.
- No fixed-stage scale is calculated from `window.innerWidth` / `window.innerHeight` alone; use `window.visualViewport.width/height` first.
- Background media may crop only when it is purely atmospheric; readable or brand-critical media must use `object-fit: contain`.
- A 2:1, ultrawide, poster, transparent-logo, game/anime key visual, product shot, or title art asset must not be placed in a 16:9 frame with `object-fit: cover` unless all cropped edges are decorative.
- Every raster image referenced by the deliverable is WebP. Keep SVG only for true vector logos, icons, and editable diagrams; convert PNG, JPEG, GIF, TIFF, BMP, and AVIF inputs before use.
- Test short-height browser viewports, not just full monitor sizes. Browser tabs, address bars, bookmarks bars, and OS taskbars reduce the available viewport.

### Density Limits

| Slide Type | Maximum Content |
|------------|-----------------|
| Title slide | 1 heading + 1 subtitle + optional tagline |
| Content slide | 1 heading + 4-6 bullets or 2 paragraphs |
| Feature grid | 6 cards maximum |
| Code slide | 8-10 lines maximum |
| Quote slide | 1 quote + attribution |
| Image slide | 1 image, ideally under 60vh |

## Mandatory Base CSS

Copy this block into every generated presentation and then theme on top of it.

```css
/* ===========================================
   VIEWPORT FITTING: MANDATORY BASE STYLES
   =========================================== */

html, body {
    height: 100%;
    width: 100%;
    margin: 0;
    overflow-x: hidden;
}

html {
    scroll-snap-type: y mandatory;
    scroll-behavior: smooth;
}

*, *::before, *::after {
    box-sizing: border-box;
}

body {
    min-height: 100vh;
    min-height: 100dvh;
    overflow-x: hidden;
}

.deck {
    width: 100%;
    min-height: 100vh;
    min-height: 100dvh;
    overflow-x: hidden;
    position: relative;
}

.slide {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    min-height: 100dvh;
    max-width: 100vw;
    max-height: 100dvh;
    overflow: hidden;
    scroll-snap-align: start;
    display: flex;
    flex-direction: column;
    position: relative;
    isolation: isolate;
    contain: layout paint;
}

.slide-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: 100%;
    max-height: 100%;
    overflow: hidden;
    padding: var(--slide-padding);
    position: relative;
    z-index: 2;
}

:root {
    --title-size: clamp(1.5rem, 5vw, 4rem);
    --h2-size: clamp(1.25rem, 3.5vw, 2.5rem);
    --h3-size: clamp(1rem, 2.5vw, 1.75rem);
    --body-size: clamp(0.75rem, 1.5vw, 1.125rem);
    --small-size: clamp(0.65rem, 1vw, 0.875rem);

    --slide-padding: clamp(1rem, 4vw, 4rem);
    --content-gap: clamp(0.5rem, 2vw, 2rem);
    --element-gap: clamp(0.25rem, 1vw, 1rem);
    --safe-edge: clamp(0.75rem, 2vw, 2rem);
}

.card, .container, .content-box {
    max-width: min(90vw, 1000px);
    max-height: min(80vh, 700px);
}

.feature-list, .bullet-list {
    gap: clamp(0.4rem, 1vh, 1rem);
}

.feature-list li, .bullet-list li {
    font-size: var(--body-size);
    line-height: 1.4;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr));
    gap: clamp(0.5rem, 1.5vw, 1rem);
}

img, .image-container {
    max-width: 100%;
    max-height: min(50vh, 400px);
    object-fit: contain;
}

.slide-bg,
.bleed-media {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: 0;
}

.safe-media,
.logo,
.title-art,
.key-visual,
.diagram,
.ui-screenshot {
    max-width: min(100%, 42vw, 520px);
    max-height: min(45dvh, 420px);
    object-fit: contain;
}

.key-visual {
    width: min(100%, 86vw);
    height: min(62dvh, 720px);
    max-width: calc(100vw - (2 * var(--safe-edge)));
    max-height: calc(100dvh - (2 * var(--safe-edge)));
}

.corner-safe,
.slide-controls {
    position: absolute;
    z-index: 5;
    inset-inline-end: calc(var(--safe-edge) + env(safe-area-inset-right));
    inset-block-end: calc(var(--safe-edge) + env(safe-area-inset-bottom));
    max-width: calc(100vw - (2 * var(--safe-edge)));
    max-height: calc(100dvh - (2 * var(--safe-edge)));
}

.corner-safe img,
.corner-safe svg,
.slide-controls {
    max-width: min(35vw, 420px);
    max-height: min(28dvh, 240px);
}

.slide h1,
.slide h2,
.slide h3,
.slide p,
.slide li,
.slide blockquote {
    overflow-wrap: anywhere;
}

@media (max-height: 700px) {
    :root {
        --slide-padding: clamp(0.75rem, 3vw, 2rem);
        --content-gap: clamp(0.4rem, 1.5vw, 1rem);
        --title-size: clamp(1.25rem, 4.5vw, 2.5rem);
        --h2-size: clamp(1rem, 3vw, 1.75rem);
    }
}

@media (max-height: 600px) {
    :root {
        --slide-padding: clamp(0.5rem, 2.5vw, 1.5rem);
        --content-gap: clamp(0.3rem, 1vw, 0.75rem);
        --title-size: clamp(1.1rem, 4vw, 2rem);
        --body-size: clamp(0.7rem, 1.2vw, 0.95rem);
    }

    .nav-dots, .keyboard-hint, .decorative {
        display: none;
    }
}

@media (max-height: 500px) {
    :root {
        --slide-padding: clamp(0.4rem, 2vw, 1rem);
        --title-size: clamp(1rem, 3.5vw, 1.5rem);
        --h2-size: clamp(0.9rem, 2.5vw, 1.25rem);
        --body-size: clamp(0.65rem, 1vw, 0.85rem);
    }
}

@media (max-width: 600px) {
    :root {
        --title-size: clamp(1.25rem, 7vw, 2.5rem);
    }

    .grid {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.2s !important;
    }

    html {
        scroll-behavior: auto;
    }
}
```

## No-Crop Slide Shell

Use this structure for every preview and every finished deck. It prevents the common failure where a slide is authored as a fixed 16:9 image or frame, then the browser viewport is shorter than expected and the bottom-right art or controls get cut off.

```html
<main class="deck">
  <section class="slide" aria-label="Slide title">
    <div class="slide-media" aria-hidden="true">
      <img class="slide-bg" src="background.webp" alt="">
    </div>
    <div class="slide-content">
      <!-- Meaningful text and readable media stay here. -->
      <div class="corner-safe">
        <!-- Optional readable logo. No negative offsets. -->
      </div>
    </div>
  </section>
</main>
```

Rules:
- `.slide-bg` can use `object-fit: cover` because it is decorative.
- Put any readable logo, title art, diagram, screenshot, or character art that must not crop inside `.slide-content`, `.safe-media`, or `.corner-safe`.
- If a wide source image is both aesthetic backdrop and meaningful key visual, use two layers: a decorative blurred/covered backdrop plus a foreground `.key-visual` with `object-fit: contain`.
- Never place meaningful content with `right: -...`, `bottom: -...`, `transform: translate(...)` beyond the viewport, or dimensions larger than `100vw` / `100dvh`.
- Do not use `position: absolute` for main copy unless the bounding box is constrained by safe insets.

## Key Visual Aspect Ratio Rule

Before placing a supplied image, classify it:

- `decorative background`: safe to crop with `object-fit: cover`.
- `key visual`: must remain fully readable/recognizable with `object-fit: contain`.
- `mixed`: use the same image twice, once as a decorative covered backdrop and once as a contained foreground.

Common failure to avoid: a `2:1` key visual placed in a `16:9` slide with `cover` will crop the left/right or top/bottom edges. If an official logo, title art, face, product, UI, subtitle, or composition edge matters, this is a failed draft.

Safe mixed-media pattern:

```html
<div class="slide-media" aria-hidden="true">
  <div class="visual-frame">
    <img class="visual-backdrop" src="key-visual.webp" alt="">
  </div>
</div>
<div class="slide-content">
  <img class="key-visual" src="key-visual.webp" alt="Readable description">
</div>
```

```css
.visual-frame {
    position: absolute;
    inset: 0;
    overflow: hidden;
    z-index: 0;
}

.visual-backdrop {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: blur(18px) brightness(0.55) saturate(1.1);
    transform: scale(1.06);
}
```

## Optional 16:9 Export Stage

Use this only when the user explicitly needs a 16:9 export or screenshot frame. Do not use it for normal browser playback.

```css
.stage {
    width: min(100vw, calc(100dvh * 16 / 9));
    height: min(100dvh, calc(100vw * 9 / 16));
    margin: auto;
    position: relative;
    overflow: hidden;
}

.stage .slide {
    width: 100%;
    height: 100%;
}
```

Never set `.stage` or `.slide` to raw `1920px` by `1080px` without a scale-to-fit wrapper.

If existing content is already authored as a fixed `1920x1080` stage, wrap and scale it from the actual visual viewport. Do not rely on `window.innerWidth` / `window.innerHeight` alone.

```html
<main class="stage-fit">
  <section class="fixed-stage">
    <!-- Existing 1920x1080 slide content. -->
  </section>
</main>
```

```css
.stage-fit {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100dvh;
    overflow: hidden;
    background: var(--deck-bg, #000);
}

.fixed-stage {
    position: absolute;
    width: 1920px;
    height: 1080px;
    transform: scale(var(--stage-scale, 1));
    transform-origin: top left;
}
```

```js
const STAGE_WIDTH = 1920;
const STAGE_HEIGHT = 1080;

function syncStageScale() {
  const viewport = window.visualViewport;
  const width = viewport?.width ?? document.documentElement.clientWidth;
  const height = viewport?.height ?? document.documentElement.clientHeight;
  const scale = Math.min(width / STAGE_WIDTH, height / STAGE_HEIGHT);
  const stage = document.querySelector('.fixed-stage');
  stage.style.left = `${Math.max(0, (width - STAGE_WIDTH * scale) / 2)}px`;
  stage.style.top = `${Math.max(0, (height - STAGE_HEIGHT * scale) / 2)}px`;
  stage.style.setProperty('--stage-scale', String(scale));
}

syncStageScale();
window.addEventListener('resize', syncStageScale);
window.addEventListener('orientationchange', syncStageScale);
window.visualViewport?.addEventListener('resize', syncStageScale);
window.visualViewport?.addEventListener('scroll', syncStageScale);
```

After adding a fixed-stage wrapper, still run the Resolution Safety Gate. The stage must be centered, fully visible, and free of clipped meaningful content at browser zoom levels such as 80%, 100%, 125%, and 150%.

## Viewport Checklist

- every `.slide` has `height: 100vh`, `height: 100dvh`, and `overflow: hidden`
- `html`, `body`, `.deck`, and `*` reset margin, sizing, and overflow so default body margins cannot create hidden scroll
- all typography uses `clamp()`
- all spacing uses `clamp()` or viewport units
- images have `max-height` constraints
- meaningful images, logos, title art, diagrams, and screenshots use `object-fit: contain`
- background-only media may use `object-fit: cover`
- `2:1` or ultrawide key visuals are either contained or split into decorative backdrop plus contained foreground
- corner elements use safe insets and never negative offsets
- fixed legacy stages use `visualViewport`-based scale, not `innerWidth` / `innerHeight` alone
- grids adapt with `auto-fit` + `minmax()`
- short-height breakpoints exist at `700px`, `600px`, and `500px`
- draft previews are checked at short-height laptop sizes before the user sees them
- if anything feels cramped, split the slide

## Mood to Preset Mapping

| Mood | Good Presets |
|------|--------------|
| Impressed / Confident | Bold Signal, Electric Studio, Dark Botanical |
| Excited / Energized | Creative Voltage, Neon Cyber, Split Pastel |
| Calm / Focused | Notebook Tabs, Paper & Ink, Swiss Modern |
| Inspired / Moved | Dark Botanical, Vintage Editorial, Pastel Geometry |
| Raw / Provocative | Raw Grid, Riso Dispatch, Creative Voltage |
| Analytical / Explanatory | Atlas Lab, Blueprint Systems, Swiss Modern |
| Human / Observational | Documentary Frame, Riso Dispatch, Paper & Ink |
| Futuristic / Dimensional | Spatial Product, Neon Cyber, Retro Future |
| Trustworthy / Financial | Stable Ledger, Swiss Modern, Electric Studio |

## Preset Catalog

### 1. Bold Signal

- Vibe: confident, high-impact, keynote-ready
- Best for: pitch decks, launches, statements
- Fonts: Archivo Black + Space Grotesk
- Palette: charcoal base, hot orange focal card, crisp white text
- Signature: oversized section numbers, high-contrast card on dark field

### 2. Electric Studio

- Vibe: clean, bold, agency-polished
- Best for: client presentations, strategic reviews
- Fonts: Manrope only
- Palette: black, white, saturated cobalt accent
- Signature: two-panel split and sharp editorial alignment

### 3. Creative Voltage

- Vibe: energetic, retro-modern, playful confidence
- Best for: creative studios, brand work, product storytelling
- Fonts: Syne + Space Mono
- Palette: electric blue, neon yellow, deep navy
- Signature: halftone textures, badges, punchy contrast

### 4. Dark Botanical

- Vibe: elegant, premium, atmospheric
- Best for: luxury brands, thoughtful narratives, premium product decks
- Fonts: Cormorant + IBM Plex Sans
- Palette: near-black, warm ivory, blush, gold, terracotta
- Signature: blurred abstract circles, fine rules, restrained motion

### 5. Notebook Tabs

- Vibe: editorial, organized, tactile
- Best for: reports, reviews, structured storytelling
- Fonts: Bodoni Moda + DM Sans
- Palette: cream paper on charcoal with pastel tabs
- Signature: paper sheet, colored side tabs, binder details

### 6. Pastel Geometry

- Vibe: approachable, modern, friendly
- Best for: product overviews, onboarding, lighter brand decks
- Fonts: Plus Jakarta Sans only
- Palette: pale blue field, cream card, soft pink/mint/lavender accents
- Signature: vertical pills, rounded cards, soft shadows

### 7. Split Pastel

- Vibe: playful, modern, creative
- Best for: agency intros, workshops, portfolios
- Fonts: Outfit only
- Palette: peach + lavender split with mint badges
- Signature: split backdrop, rounded tags, light grid overlays

### 8. Vintage Editorial

- Vibe: witty, personality-driven, magazine-inspired
- Best for: personal brands, opinionated talks, storytelling
- Fonts: Fraunces + Work Sans
- Palette: cream, charcoal, dusty warm accents
- Signature: geometric accents, bordered callouts, punchy serif headlines

### 9. Neon Cyber

- Vibe: futuristic, techy, kinetic
- Best for: AI, infra, dev tools, future-of-X talks
- Fonts: Clash Display + Satoshi
- Palette: midnight navy, cyan, magenta
- Signature: glow, particles, grids, data-radar energy

### 10. Terminal Green

- Vibe: developer-focused, hacker-clean
- Best for: APIs, CLI tools, engineering demos
- Fonts: JetBrains Mono only
- Palette: GitHub dark + terminal green
- Signature: scan lines, command-line framing, precise monospace rhythm

### 11. Swiss Modern

- Vibe: minimal, precise, data-forward
- Best for: corporate, product strategy, analytics
- Fonts: Archivo + Nunito
- Palette: white, black, signal red
- Signature: visible grids, asymmetry, geometric discipline

### 12. Paper & Ink

- Vibe: literary, thoughtful, story-driven
- Best for: essays, keynote narratives, manifesto decks
- Fonts: Cormorant Garamond + Source Serif 4
- Palette: warm cream, charcoal, crimson accent
- Signature: pull quotes, drop caps, elegant rules

### 13. Raw Grid

- Vibe: blunt, experimental, high-conviction
- Best for: startup provocations, creative technology, decisive internal proposals
- Fonts: Archivo Black + IBM Plex Mono
- Palette: white or black, signal red, electric yellow
- Signature: exposed grids, thick rules, square labels, abrupt scale changes

### 14. Riso Dispatch

- Vibe: tactile, independent, culturally charged
- Best for: music, community campaigns, portfolios, cultural storytelling
- Fonts: Barlow Condensed + IBM Plex Serif
- Palette: paper white, fluorescent coral, cobalt or soy green
- Signature: halftone imagery, overprint, torn masks, hand-set captions

### 15. Atlas Lab

- Vibe: precise, curious, evidence-led
- Best for: science, medicine, climate, research communication
- Fonts: Source Serif 4 + IBM Plex Sans
- Palette: laboratory white, ink, specimen teal, finding amber
- Signature: numbered plates, leader lines, magnified details, calibrated scales

### 16. Blueprint Systems

- Vibe: engineered, methodical, implementation-ready
- Best for: architecture, robotics, hardware, protocols, build plans
- Fonts: IBM Plex Sans + IBM Plex Mono
- Palette: drafting blue, white linework, safety orange
- Signature: dimension grids, exploded assemblies, cutaways, revision marks

### 17. Documentary Frame

- Vibe: humane, grounded, observational
- Best for: field reports, social impact, travel, oral history, case studies
- Fonts: Newsreader + Source Sans 3
- Palette: true photo color, black/white resets, restrained ochre accent
- Signature: full-frame photography, location/date slugs, testimony, evidence captions

### 18. Spatial Product

- Vibe: dimensional, premium, quietly futuristic
- Best for: AI products, spatial computing, mobility, digital twins
- Fonts: Manrope + IBM Plex Mono
- Palette: neutral field, luminous cyan, warm coral accent
- Signature: depth planes, isolated products, anchored labels, restrained translucency

### 19. Stable Ledger

- Vibe: institutional, transparent, globally connected
- Best for: fintech, stablecoins, payments, treasury, settlement, compliance
- Fonts: Inter + IBM Plex Mono
- Palette: warm white, deep ink, reserve green, settlement blue, risk amber
- Signature: tabular ledgers, reserve composition, mint/burn balance, payment rails, timestamped sources

## Direct Selection Prompts

If the user already knows the style they want, let them pick directly from the preset names above instead of forcing preview generation.

## Animation Feel Mapping

| Feeling | Motion Direction |
|---------|------------------|
| Dramatic / Cinematic | slow fades, parallax, large scale-ins |
| Techy / Futuristic | glow, particles, grid motion, scramble text |
| Playful / Friendly | springy easing, rounded shapes, floating motion |
| Professional / Corporate | subtle 200-300ms transitions, clean slides |
| Calm / Minimal | very restrained movement, whitespace-first |
| Editorial / Magazine | strong hierarchy, staggered text and image interplay |

## CSS Gotcha: Negating Functions

Never write these:

```css
right: -clamp(28px, 3.5vw, 44px);
margin-left: -min(10vw, 100px);
```

Browsers ignore them silently.

Always write this instead:

```css
right: calc(-1 * clamp(28px, 3.5vw, 44px));
margin-left: calc(-1 * min(10vw, 100px));
```

## Canonical Validation Profiles

Generate evidence with `scripts/render_slides.js`; do not substitute ad hoc sizes in the review manifest.

- Quick Draft and Full Validation default to the same three profiles: `normal` 1920x1080, `short` 1366x650, and `zoom150` with a 1280x720 CSS viewport captured at 1920x1080.
- Add `tablet` 1024x768 and `mobile` 390x844 only when the user requests responsive mobile/tablet support. Do not run them for an ordinary presentation.
- The zoom profiles deliberately reduce available CSS pixels while retaining a high-resolution PNG. They expose browser zoom/display-scaling overflow that a 1920x1080 screenshot alone hides.
- Keep every generated profile as deterministic evidence, but route AI inspection adaptively. `normal` is always required. Cover, closing, `data-visual-critical="true"`, requested responsive targets, and warning-bearing profiles require additional AI inspection. Automated geometry failures block vision entirely until fixed.
- Additional sizes may be explored for a specific target device, but they supplement rather than replace the three default profiles.

## Canonical Navigation Panel

Keep the starter runtime's exact interaction order: previous icon, three-cell `current input / total` counter, next icon, fullscreen icon. Use inline SVG icons and preserve the numeric input behavior. Change only theme tokens such as `--nav-surface`, `--nav-border`, `--nav-ink`, `--nav-muted`, `--nav-accent`, and `--nav-hover`. The current page input should read as part of the counter, not a separate bordered card. Keep the panel compact at the bottom-right and geometrically center the input, separator, and total.

## Anti-Patterns

Do not use:
- purple-on-white startup templates
- Inter / Roboto / Arial as the visual voice unless the user explicitly wants utilitarian neutrality
- bullet walls, tiny type, or code blocks that require scrolling
- decorative illustrations when abstract geometry would do the job better
