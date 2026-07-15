#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STANDALONE = ROOT / "codex/skills/build-html-slides"
PLUGIN_ROOT = ROOT / "plugins/build-html-slides"
PLUGIN_SKILL = PLUGIN_ROOT / "skills/build-html-slides"
CLAUDE_SKILL = ROOT / ".claude/skills/build-html-slides"
CLAUDE_PLUGIN = ROOT / ".claude-plugin/plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin/marketplace.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name != ".build-html-slides-copy-origin"
        and path.suffix != ".pyc"
        and "__pycache__" not in path.parts
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def main() -> None:
    require((STANDALONE / "SKILL.md").is_file(), "standalone SKILL.md is missing")
    require((PLUGIN_SKILL / "SKILL.md").is_file(), "plugin SKILL.md is missing")
    require((CLAUDE_SKILL / "SKILL.md").is_file(), "Claude SKILL.md is missing")
    require(tree_hashes(STANDALONE) == tree_hashes(PLUGIN_SKILL), "skill distributions differ")
    require(tree_hashes(STANDALONE) == tree_hashes(CLAUDE_SKILL), "Claude skill distribution differs")

    license_file = ROOT / "LICENSE"
    notices_file = ROOT / "THIRD_PARTY_NOTICES.md"
    require(license_file.is_file(), "root LICENSE is missing")
    require(notices_file.is_file(), "root THIRD_PARTY_NOTICES.md is missing")
    for distribution in (STANDALONE, CLAUDE_SKILL, PLUGIN_ROOT):
        require((distribution / "LICENSE").is_file(), f"{distribution} LICENSE is missing")
        require(digest(distribution / "LICENSE") == digest(license_file), f"{distribution} LICENSE differs")
        require((distribution / "THIRD_PARTY_NOTICES.md").is_file(), f"{distribution} third-party notices are missing")
        require(
            digest(distribution / "THIRD_PARTY_NOTICES.md") == digest(notices_file),
            f"{distribution} third-party notices differ",
        )

    package = json.loads((ROOT / "package.json").read_text())
    plugin = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text())
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    claude_plugin = json.loads(CLAUDE_PLUGIN.read_text())
    claude_marketplace = json.loads(CLAUDE_MARKETPLACE.read_text())

    require(plugin["name"] == "build-html-slides", "plugin name mismatch")
    require(plugin["version"] == package["version"], "package and plugin versions differ")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])), "version is not strict semver")
    require(plugin.get("license") == "MIT", "plugin license must be MIT")
    require(plugin.get("skills") == "./skills/", "plugin skill path mismatch")
    require(marketplace.get("name") == "build-html-slides", "marketplace name mismatch")
    require(len(marketplace.get("plugins", [])) == 1, "marketplace must contain one plugin")
    require(marketplace["plugins"][0]["name"] == plugin["name"], "marketplace plugin mismatch")

    prompts = plugin.get("interface", {}).get("defaultPrompt", [])
    require(isinstance(prompts, list) and 1 <= len(prompts) <= 3, "defaultPrompt must contain 1-3 prompts")
    require(all(len(prompt) <= 128 for prompt in prompts), "defaultPrompt exceeds 128 characters")

    require(claude_plugin["name"] == plugin["name"], "Claude plugin name mismatch")
    require(claude_plugin["version"] == package["version"], "package and Claude plugin versions differ")
    require(claude_plugin.get("license") == "MIT", "Claude plugin license must be MIT")
    require(claude_plugin.get("skills") == ["./.claude/skills/"], "Claude plugin skill path mismatch")
    require(claude_marketplace.get("name") == "build-html-slides", "Claude marketplace name mismatch")
    require(claude_marketplace.get("metadata", {}).get("version") == package["version"], "Claude marketplace version mismatch")
    claude_entries = claude_marketplace.get("plugins", [])
    require(len(claude_entries) == 1, "Claude marketplace must contain one plugin")
    require(claude_entries[0].get("name") == claude_plugin["name"], "Claude marketplace plugin mismatch")
    require(claude_entries[0].get("version") == package["version"], "Claude marketplace plugin version mismatch")

    agents = sorted((ROOT / "agents").glob("build-html-slides-*.md"))
    require(len(agents) == 2, "Claude plugin must contain two review agents")
    for agent in agents:
        content = agent.read_text(encoding="utf-8")
        require(content.startswith("---\n"), f"Claude agent frontmatter missing: {agent.name}")
        require(re.search(r"^name: build-html-slides-[a-z-]+$", content, re.MULTILINE) is not None, f"Claude agent name invalid: {agent.name}")
        require("model: inherit" in content, f"Claude agent must inherit the session model: {agent.name}")

    agent_guidance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude_guidance = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    require("final response MUST include" in agent_guidance, "agent post-install reporting contract is missing")
    require("im-not-ai" in agent_guidance and "humanize-korean" in agent_guidance, "agent im-not-ai guidance is missing")
    require("/humanize-korean" in agent_guidance and "$humanize-korean" in agent_guidance, "agent im-not-ai invocation guidance is missing")
    require("drawio-skill" in agent_guidance and "draw.io desktop CLI" in agent_guidance, "agent drawio companion guidance is missing")
    require("also install" not in agent_guidance or "explicitly agrees" in agent_guidance, "optional companion consent contract is missing")
    require("does not include a raster image generator" in agent_guidance, "agent Claude image-generation guidance is missing")
    require("Read and follow `AGENTS.md`" in claude_guidance, "Claude repository guidance does not inherit AGENTS.md")
    require("AI 에이전트에게 설치를 맡긴 경우" in readme, "README AI-agent installation guidance is missing")
    require("Claude Code 기본 설치에는 래스터 이미지 생성기가 포함되지 않습니다" in readme, "README Claude image-generation notice is missing")
    require("Post-install guidance:" in installer, "installer post-install guidance is missing")
    require("epoko77-ai/im-not-ai" in installer, "installer im-not-ai notice is missing")
    require("Agents365-ai/drawio-skill" in installer, "installer drawio notice is missing")
    require("Do not install either companion" in installer, "installer optional companion consent notice is missing")
    require("does not include a raster image generator by default" in installer, "installer Claude image-generation notice is missing")

    print(f"Repository validation passed ({len(tree_hashes(STANDALONE))} shared skill files).")


if __name__ == "__main__":
    main()
