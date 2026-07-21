# Repository Agent Instructions

## Installation tasks

When a user gives this repository URL to an AI agent and asks it to install or update build-html-slides:

1. Follow the platform-specific installation path in `README.md`. Install either the plugin or the standalone skill for a platform, never both.
2. Do not install optional companion skills, image-generation tools, MCP servers, plugins, credentials, or paid services without explicit user consent.
3. After a successful installation, the final response MUST include all applicable post-install guidance below. Do not omit it just because the user asked for a short response.
4. Do not treat Playwright/Chromium as silently installable. Run the installed skill's `scripts/check_environment.py`; if it reports them missing, ask first. After explicit consent, prefer `scripts/install_browser_dependencies.py --consent`, and add `--with-deps` only when system-library installation was also approved.

### Required for every installation

- Explain that [`epoko77-ai/im-not-ai`](https://github.com/epoko77-ai/im-not-ai) is an optional companion, not a dependency and not bundled with build-html-slides.
- Explain that its `humanize-korean` skill can polish Korean slide copy and presenter notes after facts, numbers, proper nouns, and citations are settled.
- State the actual invocation: Claude Code uses `/humanize-korean`; Codex uses `$humanize-korean` and provides the Fast single-call mode.
- Do not claim that im-not-ai was installed unless the user explicitly requested it and the installation actually succeeded.
- Explain that [`tt-a1i/archify`](https://github.com/tt-a1i/archify) is an optional companion for architecture, topology, ERD, UML, sequence, workflow, lifecycle, and complex flow diagrams. It is not bundled.
- Explain that Archify produces self-contained HTML with inline SVG and image export controls; build-html-slides keeps its source HTML and inserts the diagram SVG or WebP into the deck.
- Check whether `humanize-korean` and `archify` are already available on the installed platform. After the main installation succeeds, ask one concise follow-up for only the missing companions: `선택 도구인 im-not-ai(한국어 윤문)와 Archify(아키텍처·ERD·UML·흐름도)도 설치할까요?`
- Do not install either companion, credentials, or system packages until the user explicitly agrees. If one companion is already present, ask only about the missing one.
- When a companion is already installed, build-html-slides must invoke it automatically when its task-specific routing rules match; availability is sufficient consent for use. Do not ask for permission on every deck.

### Required when Claude Code was installed

- Explain that base Claude Code can inspect rendered images but does not include a raster image generator comparable to a Codex environment that exposes ImageGen.
- Explain that users who want generated backgrounds, illustrations, or concept art must separately connect a compatible image-generation plugin, MCP server, or external tool.
- State that build-html-slides still works without a generator by using supplied, official, licensed, or web-sourced imagery plus HTML/CSS/SVG diagrams.
- Ask for consent before installing or configuring any generator, credentials, or paid service.

### Required when Gemini CLI was installed

- Explain that build-html-slides uses Gemini CLI Agent Skills and activates from a matching natural-language request after skill consent.
- Do not assume a raster image generator is available. Inspect the current Gemini tool set; if none is configured, use sourced visuals and HTML/CSS/SVG or ask before adding any generator, extension, credentials, or paid service.

Always remind the user to start a new Codex task, Claude Code session, or Gemini CLI session after installation.
