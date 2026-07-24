# Claude Code Repository Instructions

Read and follow `AGENTS.md`, especially its installation-task contract.

After installing this repository for Claude Code, the final response must tell the user that:

- `tt-a1i/archify` is **bundled**. The supported distributions ship it, and `./install.sh` installs it as an independent skill alongside build-html-slides without asking. Never offer to install Archify and never ask for consent to install it; it is already there. It produces self-contained HTML with inline SVG and export controls for architecture, topology, ERD, UML, sequence, workflow, lifecycle, and complex flow diagrams.
- The one exception is an unrelated pre-existing Archify installation: the installer preserves it and prints `Bundled Archify skipped; existing installation preserved`. In that case tell the user their copy was kept and that `--force` would replace it after backing it up to `<home>/.build-html-slides-backups/`.
- `im-not-ai` and its `humanize-korean` skill are optional companions for polishing Korean slide copy and presenter notes. They are **not** bundled and are never installed automatically. After a separate installation, invoke it with `/humanize-korean` in Claude Code.
- After build-html-slides is installed, check whether `humanize-korean` is present. Only if it is missing, ask one concise follow-up about installing `im-not-ai`. Do not install it, any dependency, credential, or paid service before the user agrees.
- If a companion is already installed — bundled Archify always, `humanize-korean` when present — use it automatically when the deck needs a qualified technical diagram or Korean final-copy polishing. Availability is sufficient consent for use; no separate per-deck question is allowed.
- Base Claude Code can inspect rendered captures but does not include a raster image generator. Generated backgrounds, illustrations, and concept art require a separately configured compatible plugin, MCP server, or external image-generation tool.
- The slide skill works without image generation, and no optional tool, credential, or paid service may be installed or configured without explicit consent.
- A new Claude Code session is required to load the installed skill reliably.
