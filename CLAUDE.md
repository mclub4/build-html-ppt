# Claude Code Repository Instructions

Read and follow `AGENTS.md`, especially its installation-task contract.

After installing this repository for Claude Code, the final response must tell the user that:

- `im-not-ai` and its `humanize-korean` skill are optional companions for polishing Korean slide copy and presenter notes; they are not bundled or installed automatically. After a separate installation, invoke it with `/humanize-korean` in Claude Code.
- `Agents365-ai/drawio-skill` is an optional companion for editable architecture, topology, ERD, UML, sequence, BPMN, swimlane, and complex flow diagrams. Local export requires the draw.io desktop CLI; Graphviz is optional for large automatic layouts.
- After build-html-slides is installed, check which companions are missing and ask whether the user wants to install `im-not-ai` and/or `drawio-skill`. Do not install either skill, draw.io, Graphviz, or system packages before the user agrees.
- If either companion is already installed, use it automatically when the deck needs Korean final-copy polishing or a qualified technical diagram; no separate per-deck request is required.
- Base Claude Code can inspect rendered captures but does not include a raster image generator. Generated backgrounds, illustrations, and concept art require a separately configured compatible plugin, MCP server, or external image-generation tool.
- The slide skill works without image generation, and no optional tool, credential, or paid service may be installed or configured without explicit consent.
- A new Claude Code session is required to load the installed skill reliably.
