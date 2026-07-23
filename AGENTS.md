# Repository Agent Instructions

## Installation tasks

When a user gives this repository URL to an AI agent and asks it to install or update build-html-slides:

1. Follow the platform-specific installation path in `README.md`. Install either the plugin or the standalone skill for a platform, never both.
2. The supported distributions already bundle Archify. Do not install any other optional companion skill, image-generation tool, MCP server, plugin, credential, or paid service without explicit user consent.
3. After a successful installation, the final response MUST include all applicable post-install guidance below. Do not omit it just because the user asked for a short response.
4. Explain that Quick Draft is creation-only and needs no browser preflight. Only when Full Validation or explicit browser validation is requested, run the installed skill's `scripts/check_environment.py`. Do not treat Playwright/Chromium as silently installable; if the preflight reports them missing, ask first. After explicit consent, prefer `scripts/install_browser_dependencies.py --consent`, and add `--with-deps` only when system-library installation was also approved.

### Required for every installation

- Explain that [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) is an optional companion, not a dependency and not bundled with build-html-slides.
- Explain that its `humanize-korean` skill can polish Korean slide copy and presenter notes after facts, numbers, proper nouns, and citations are settled.
- State the actual invocation: Claude Code uses `/humanize-korean`; Codex uses `$humanize-korean` and provides the Fast single-call mode.
- Do not claim that im-not-ai was installed unless the user explicitly requested it and the installation actually succeeded.
- Explain that Archify v2.12.0 from [`tt-a1i/archify`](https://github.com/tt-a1i/archify) is bundled as an independent skill for architecture, topology, sequence, workflow, lifecycle, data-flow, and complex flow diagrams.
- Explain that Archify produces self-contained HTML with inline SVG and image export controls; build-html-slides keeps its source HTML and inserts the diagram SVG or WebP into the deck.
- If an unrelated Archify installation already exists, preserve it unless the user explicitly requested `--force`; do not replace a newer or customized copy silently.
- Check whether `humanize-korean` is already available after the main installation succeeds. If it is missing, ask one concise follow-up: `선택 도구인 im-not-ai(한국어 윤문)도 설치할까요?`
- Do not install im-not-ai, credentials, or system packages until the user explicitly agrees.
- Available `humanize-korean` and bundled Archify must be invoked automatically when their task-specific routing rules match; availability is sufficient consent for use. Do not ask for permission on every deck.

### Required when Claude Code was installed

- Explain that base Claude Code can inspect rendered images but does not include a raster image generator comparable to a Codex environment that exposes ImageGen.
- Explain that users who want generated backgrounds, illustrations, or concept art must separately connect a compatible image-generation plugin, MCP server, or external tool.
- State that build-html-slides still works without a generator by using supplied, official, licensed, or web-sourced imagery plus HTML/CSS/SVG diagrams.
- Ask for consent before installing or configuring any generator, credentials, or paid service.

### Required when Gemini CLI was installed

- Explain that build-html-slides uses Gemini CLI Agent Skills and activates from a matching natural-language request after skill consent.
- Do not assume a raster image generator is available. Inspect the current Gemini tool set; if none is configured, use sourced visuals and HTML/CSS/SVG or ask before adding any generator, extension, credentials, or paid service.

Always remind the user to start a new Codex task, Claude Code session, or Gemini CLI session after installation.
