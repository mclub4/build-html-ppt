# Claude Code Repository Instructions

Read and follow `AGENTS.md`, especially its installation-task contract.

After installing this repository for Claude Code, the final response must tell the user that:

- `im-not-ai` and its `humanize-korean` skill are optional companions for polishing Korean slide copy and presenter notes; they are not bundled or installed automatically. After a separate installation, invoke it with `/humanize-korean` in Claude Code.
- `tt-a1i/archify` is an optional companion for architecture, topology, ERD, UML, sequence, workflow, lifecycle, and complex flow diagrams. It produces self-contained HTML with inline SVG and export controls.
- After build-html-slides is installed, check which companions are missing and ask whether the user wants to install `im-not-ai` and/or `archify`. Do not install either skill or any dependency before the user agrees.
- If either companion is already installed, use it automatically when the deck needs Korean final-copy polishing or a qualified technical diagram. Availability is sufficient consent for use; no separate per-deck question is allowed.
- Base Claude Code can inspect rendered captures but does not include a raster image generator. Generated backgrounds, illustrations, and concept art require a separately configured compatible plugin, MCP server, or external image-generation tool.
- The slide skill works without image generation, and no optional tool, credential, or paid service may be installed or configured without explicit consent.
- A new Claude Code session is required to load the installed skill reliably.
