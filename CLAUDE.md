# Claude Code Repository Instructions

Read and follow `AGENTS.md`, especially its installation-task contract.

After installing this repository for Claude Code, the final response must tell the user that:

- `im-not-ai` and its `humanize-korean` skill are optional companions for polishing Korean slide copy and presenter notes; they are not bundled or installed automatically. After a separate installation, invoke it with `/humanize-korean` in Claude Code.
- Base Claude Code can inspect rendered captures but does not include a raster image generator. Generated backgrounds, illustrations, and concept art require a separately configured compatible plugin, MCP server, or external image-generation tool.
- The slide skill works without image generation, and no optional tool, credential, or paid service may be installed or configured without explicit consent.
- A new Claude Code session is required to load the installed skill reliably.
