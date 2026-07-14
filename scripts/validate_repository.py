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
    require(tree_hashes(STANDALONE) == tree_hashes(PLUGIN_SKILL), "skill distributions differ")

    license_file = ROOT / "LICENSE"
    notices_file = ROOT / "THIRD_PARTY_NOTICES.md"
    require(license_file.is_file(), "root LICENSE is missing")
    require(notices_file.is_file(), "root THIRD_PARTY_NOTICES.md is missing")
    for distribution in (STANDALONE, PLUGIN_ROOT):
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

    print(f"Repository validation passed ({len(tree_hashes(STANDALONE))} skill files).")


if __name__ == "__main__":
    main()
