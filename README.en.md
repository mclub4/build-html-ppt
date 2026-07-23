<p align="center">
  <img src="assets/readme-hero.svg" alt="Build HTML Slides for Codex, Claude Code, and Gemini CLI" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/mclub4/build-html-ppt/releases"><img alt="Release" src="https://img.shields.io/github/v/release/mclub4/build-html-ppt?color=f06b52" /></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-57c7b6" /></a>
  <img alt="Codex, Claude Code, and Gemini CLI" src="https://img.shields.io/badge/support-Codex%20%2B%20Claude%20Code%20%2B%20Gemini%20CLI-20252b" />
</p>

<p align="center">
  <a href="README.ko.md">한국어</a> · <strong>English</strong> · <a href="README.ja.md">日本語</a>
</p>

<h1 align="center">Build HTML Slides</h1>

<p align="center">
  A presentation skill that helps Codex, Claude Code, and Gemini CLI build art-directed HTML decks and speaker notes around the real audience, communication job, and evidence.
</p>

<h2 align="center">
  <a href="https://html-ppt-gallery.unequaled-condor.workers.dev/">Explore presentations made with Build HTML Slides</a>
</h2>

<p align="center">
  <a href="https://html-ppt-gallery.unequaled-condor.workers.dev/">
    <img src="assets/gallery-preview.webp" alt="Build HTML Slides gallery preview" width="100%" />
  </a>
</p>

> Supports OpenAI Codex CLI / Codex App, Anthropic Claude Code, and Google Gemini CLI. This is a community project and is not an official project of those platform vendors.

## Status and modes

Build HTML Slides is experimental. It targets desktop presentation playback first; mobile behavior is not assured unless responsive support was explicitly requested and validated.

- **Quick Draft:** creates the HTML deck, local assets, `sources.json`, and Markdown speaker notes, then delivers immediately. It does not open a browser or claim visual validation.
- **Full Validation:** renders every slide, runs deterministic geometry and interaction checks, routes full-size PNGs to AI visual reviewers, and performs one independent final quality pass.

For roughly 15 slides, the planning target is about 10 minutes for Quick Draft and about one hour for Full Validation with Codex GPT-5.6 at Medium reasoning. Research breadth, image discovery, model choice, and machine speed can change this substantially. The target for 20-25 Full Validation slides is 40-90 minutes.

## Outputs

- one offline-portable HTML presentation;
- one `OUTPUT-notes.md` file with a natural talk track, emphasis, transitions, and source caveats;
- local WebP imagery and editable SVG diagrams;
- `sources.json` with URLs, file hashes, source kind, verification date, and credit;
- keyboard, click, direct page input, fullscreen, hash, and print navigation;
- a fixed 1280x720 stage that scales from `visualViewport` without cropping the deck.

## Audience-aware design intelligence

The skill does not map a topic word directly to a theme. It first combines:

1. one of twelve broad subject families and its evidence obligations;
2. one of ten communication jobs, such as education, decision, launch, research, postmortem, roadmap, or curation;
3. the actual audience, desired room outcome, authentic media, and writing system;
4. density, real-media need, visual variance, and motion dials from 1 to 10.

It then retrieves three materially different design candidates, compares them, and rejects at least one with a concrete reason. Subject families control evidence, not palette or fonts. A technology topic therefore does not automatically become a dark console deck.

The presentation-specific candidate index includes paper-led systems, constructive geometry, organic systems, scholarly review, archival analog, editorial grids, documentary photography, product keynotes, scientific atlases, and other optional directions. Kinetic typography, exaggerated minimalism, 3D product evidence, and parallax are limited treatment grammars rather than mandatory full-deck themes.

Chart recommendations are selected from the data shape, not the subject. The chart contract records when to use or avoid each form, category limits, direct labeling, and non-color encodings.

## Full Validation and squint review

Full Validation captures `normal`, short-height, and real Chromium 150% page-zoom profiles. Automatic text bounds, font integrity, container density, control geometry, image geometry, placeholders, source cache, notes, and browser interactions run before AI review.

After slide-level fixes settle, finalization reuses the current `normal` PNGs to generate one downscaled, lightly blurred **squint contact sheet**. The independent quality editor checks only:

- focal hierarchy;
- emphasis range;
- deck rhythm;
- color and density balance.

Squint review is a cheap auxiliary overview. It cannot prove text overlap, awkward line breaks, crop, distortion, overflow, identity, or image appropriateness. Those remain full-size inspection responsibilities. The artifact is hash-bound to every current normal capture and adds no deck rerender.

## Requirements

- Codex CLI / App, Claude Code, or Gemini CLI;
- Python 3.10+;
- Node.js 18+;
- Playwright and Chromium only for Full Validation.

For repository development:

```bash
npm install
npx playwright install chromium
npm run check:browser
```

Quick Draft does not inspect or install browser dependencies. Full Validation first runs a non-mutating preflight. Missing browser tooling is installed only after explicit user consent:

```bash
python3 <installed-skill>/scripts/install_browser_dependencies.py --consent
```

## Installation

Choose either the plugin or standalone skill on a given platform. Installing both can show duplicate skill entries.

### Claude Code plugin

```bash
claude plugin marketplace add mclub4/build-html-ppt
claude plugin install build-html-slides@build-html-slides
```

### Codex plugin

```bash
codex plugin marketplace add mclub4/build-html-ppt
codex plugin add build-html-slides@build-html-slides
```

### Gemini CLI Agent Skill

```bash
gemini skills install ./BUILD-HTML-SLIDES-GEMINI-vX.Y.Z.skill
gemini skills install ./ARCHIFY-GEMINI-v2.12.0.skill
gemini skills list
```

### Standalone installation from the repository

```bash
git clone https://github.com/mclub4/build-html-ppt.git
cd build-html-ppt
./install.sh
```

Restart the agent session after installation.

## Post-install guidance for AI agents

An AI agent that installs this repository must explain that:

- [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) is an optional Korean prose companion, not a bundled dependency;
- this repository bundles Archify v2.12.0 from [`tt-a1i/archify`](https://github.com/tt-a1i/archify) as an independent skill for architecture, topology, sequence, workflow, lifecycle, data-flow, and complex system diagrams;
- available `humanize-korean` and bundled `archify` are used automatically when their routing conditions match; an unrelated existing Archify install is preserved unless `--force` is explicit;
- Claude Code does not include a raster image generator by default, so generated raster art requires a separately configured compatible plugin, MCP server, or external tool;
- no optional companion or image-generation service is installed or configured without consent. Only missing `humanize-korean` should prompt an optional companion-install question.

## Usage

Natural-language requests work after installation:

```text
Create a 12-slide HTML presentation for executives and engineers.
Put the business decision and current-state impact before the technical design.
Show me Quick Draft and Full Validation first, then wait for my choice.
```

```text
Revise slides 4 and 7 only. This is an ordinary edit; do not create new validation evidence.
```

Full Validation uses one entrypoint:

```bash
python3 scripts/validate_all.py OUTPUT.html --mode full --phase prepare
python3 scripts/validate_all.py OUTPUT.html --phase verify
python3 scripts/validate_all.py OUTPUT.html --phase finalize-prepare
python3 scripts/validate_all.py OUTPUT.html --phase finalize-verify
```

Review files are stored outside the deliverable directory by default under the active agent home:

```text
~/.codex/build-html-slides/workspaces/<deck-id>/
~/.claude/build-html-slides/workspaces/<deck-id>/
~/.gemini/build-html-slides/workspaces/<deck-id>/
```

## Development

```bash
npm test
npm run test:e2e
npm run check
```

The canonical skill lives in `codex/skills/build-html-slides`. Run `scripts/sync-distributions.sh` to synchronize Codex plugin, Claude Code, and Gemini CLI distributions.

## License

MIT. See [LICENSE](LICENSE). Third-party adaptations already included in the repository are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The presentation design candidate index and ranking scripts are original project material; no external style, palette, font, or product-classification dataset is vendored.
