#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STANDALONE = ROOT / "codex/skills/build-html-slides"
ARCHIFY_STANDALONE = ROOT / "codex/skills/archify"
PLUGIN_ROOT = ROOT / "plugins/build-html-slides"
PLUGIN_SKILL = PLUGIN_ROOT / "skills/build-html-slides"
PLUGIN_ARCHIFY = PLUGIN_ROOT / "skills/archify"
CLAUDE_SKILL = ROOT / ".claude/skills/build-html-slides"
CLAUDE_ARCHIFY = ROOT / ".claude/skills/archify"
GEMINI_SKILL = ROOT / ".gemini/skills/build-html-slides"
GEMINI_ARCHIFY = ROOT / ".gemini/skills/archify"
CLAUDE_PLUGIN = ROOT / ".claude-plugin/plugin.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin/marketplace.json"
ARCHIFY_UPSTREAM_COMMIT = "324c0c063bd5f89a36a582fcb9a3efb53caa4285"
ARCHIFY_PACKAGE_SHA256 = "3a52613634287fe90f39f076c98cb1271cce58737458e632e7766e1a6b443849"

# The bundled Archify version has exactly one source of truth. Restating it as a
# constant here made this validator agree with stale documentation instead of
# catching it.
ARCHIFY_VERSION = json.loads((ARCHIFY_STANDALONE / "package.json").read_text(encoding="utf-8"))["version"]

# Every place a human writes the Archify version down. Each pattern captures the
# version so a stale literal is reported rather than merely missing.
ARCHIFY_VERSION_PATTERNS = (
    r"[Aa]rchify\s+v(\d+\.\d+\.\d+)",
    r"ARCHIFY-GEMINI-v(\d+\.\d+\.\d+)",
    r"archify[^\n]{0,40}?version\s+(\d+\.\d+\.\d+)",
)

# README.md is the canonical Korean document and the repository landing page.
# README.ko.md is a pointer that keeps older links working; it must stay short
# so the two can never drift into two competing full documents again.
README_KO_POINTER_MAX_BYTES = 2048


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archify_versions_mentioned(text: str) -> set[str]:
    found: set[str] = set()
    for pattern in ARCHIFY_VERSION_PATTERNS:
        found.update(re.findall(pattern, text))
    return found


IGNORED_DIRECTORIES = frozenset({"__pycache__", ".pytest_cache", ".omc", ".git"})
IGNORED_NAMES = frozenset({".build-html-slides-copy-origin", ".DS_Store"})
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})


def is_transient(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return (
        path.name in IGNORED_NAMES
        or path.suffix in IGNORED_SUFFIXES
        or bool(IGNORED_DIRECTORIES.intersection(relative.parts))
    )


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not is_transient(path, root)
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def main() -> None:
    # No CI is exactly how a sync-blocking bug reached the working tree
    # unnoticed. The workflow itself is part of the contract.
    workflows = sorted((ROOT / ".github/workflows").glob("*.yml")) + sorted(
        (ROOT / ".github/workflows").glob("*.yaml")
    )
    require(bool(workflows), "no GitHub Actions workflow enforces npm run check and npm test")
    workflow_text = "\n".join(path.read_text(encoding="utf-8") for path in workflows)
    require("npm run check" in workflow_text, "CI must run npm run check")
    require(re.search(r"run:\s*npm test\b", workflow_text) is not None, "CI must run npm test")
    require("playwright install" in workflow_text, "CI must install the Playwright browser the render tests need")
    require("pull_request" in workflow_text, "CI must run on pull_request")

    require((STANDALONE / "SKILL.md").is_file(), "standalone SKILL.md is missing")
    require((STANDALONE / "scripts/install_browser_dependencies.py").is_file(), "managed browser installer is missing")
    require((STANDALONE / "scripts/playwright_loader.js").is_file(), "shared Playwright loader is missing")
    require((STANDALONE / "scripts/validation_contract.json").is_file(), "machine validation contract is missing")
    require((STANDALONE / "scripts/suggest_design_directions.py").is_file(), "design candidate search is missing")
    require((STANDALONE / "scripts/suggest_chart.py").is_file(), "chart suggestion tool is missing")
    require((STANDALONE / "scripts/build_media_contact_sheet.js").is_file(), "media contact-sheet builder is missing")
    require((STANDALONE / "references/design-candidates.json").is_file(), "design candidate data is missing")
    require((STANDALONE / "references/chart-selection.json").is_file(), "chart selection data is missing")
    require((STANDALONE / "references/high-volume-media-workflow.md").is_file(), "high-volume media workflow is missing")
    require((PLUGIN_SKILL / "SKILL.md").is_file(), "plugin SKILL.md is missing")
    require((CLAUDE_SKILL / "SKILL.md").is_file(), "Claude SKILL.md is missing")
    require((GEMINI_SKILL / "SKILL.md").is_file(), "Gemini SKILL.md is missing")
    require(tree_hashes(STANDALONE) == tree_hashes(PLUGIN_SKILL), "skill distributions differ")
    require(tree_hashes(STANDALONE) == tree_hashes(CLAUDE_SKILL), "Claude skill distribution differs")
    require(tree_hashes(STANDALONE) == tree_hashes(GEMINI_SKILL), "Gemini skill distribution differs")
    require((ARCHIFY_STANDALONE / "SKILL.md").is_file(), "bundled Archify SKILL.md is missing")
    require((PLUGIN_ARCHIFY / "SKILL.md").is_file(), "plugin Archify SKILL.md is missing")
    require((CLAUDE_ARCHIFY / "SKILL.md").is_file(), "Claude Archify SKILL.md is missing")
    require((GEMINI_ARCHIFY / "SKILL.md").is_file(), "Gemini Archify SKILL.md is missing")
    require(tree_hashes(ARCHIFY_STANDALONE) == tree_hashes(PLUGIN_ARCHIFY), "plugin Archify distribution differs")
    require(tree_hashes(ARCHIFY_STANDALONE) == tree_hashes(CLAUDE_ARCHIFY), "Claude Archify distribution differs")
    require(tree_hashes(ARCHIFY_STANDALONE) == tree_hashes(GEMINI_ARCHIFY), "Gemini Archify distribution differs")

    license_file = ROOT / "LICENSE"
    notices_file = ROOT / "THIRD_PARTY_NOTICES.md"
    require(license_file.is_file(), "root LICENSE is missing")
    require(notices_file.is_file(), "root THIRD_PARTY_NOTICES.md is missing")
    for distribution in (STANDALONE, CLAUDE_SKILL, GEMINI_SKILL, PLUGIN_ROOT):
        require((distribution / "LICENSE").is_file(), f"{distribution} LICENSE is missing")
        require(digest(distribution / "LICENSE") == digest(license_file), f"{distribution} LICENSE differs")
        require((distribution / "THIRD_PARTY_NOTICES.md").is_file(), f"{distribution} third-party notices are missing")
        require(
            digest(distribution / "THIRD_PARTY_NOTICES.md") == digest(notices_file),
            f"{distribution} third-party notices differ",
        )

    archify_license = ARCHIFY_STANDALONE / "LICENSE"
    require(archify_license.is_file(), "bundled Archify LICENSE is missing")
    for distribution in (PLUGIN_ARCHIFY, CLAUDE_ARCHIFY, GEMINI_ARCHIFY):
        require((distribution / "LICENSE").is_file(), f"{distribution} Archify LICENSE is missing")
        require(digest(distribution / "LICENSE") == digest(archify_license), f"{distribution} Archify LICENSE differs")

    package = json.loads((ROOT / "package.json").read_text())
    archify_package = json.loads((ARCHIFY_STANDALONE / "package.json").read_text())
    machine_contract = json.loads((STANDALONE / "scripts/validation_contract.json").read_text())
    plugin = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text())
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    claude_plugin = json.loads(CLAUDE_PLUGIN.read_text())
    claude_marketplace = json.loads(CLAUDE_MARKETPLACE.read_text())

    require(plugin["name"] == "build-html-slides", "plugin name mismatch")
    require(machine_contract.get("schema_version") == 13, "validation contract schema mismatch")
    require(
        package.get("devDependencies", {}).get("playwright") == machine_contract.get("playwright_version"),
        "package and managed Playwright versions differ",
    )
    require(plugin["version"] == package["version"], "package and plugin versions differ")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", plugin["version"])), "version is not strict semver")
    require(plugin.get("license") == "MIT", "plugin license must be MIT")
    require(plugin.get("skills") == "./skills/", "plugin skill path mismatch")
    require(archify_package.get("name") == "archify", "bundled Archify package name mismatch")
    require(archify_package.get("version") == ARCHIFY_VERSION, "bundled Archify version mismatch")
    require(archify_package.get("license") == "MIT", "bundled Archify license metadata mismatch")
    require(archify_package.get("engines", {}).get("node") == ">=18", "bundled Archify Node contract mismatch")
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
    readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    readme_ko = (ROOT / "README.ko.md").read_text(encoding="utf-8")
    readme_ja = (ROOT / "README.ja.md").read_text(encoding="utf-8")
    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
    updater = (ROOT / "update.sh").read_text(encoding="utf-8")
    packager = (ROOT / "scripts/package-release.sh").read_text(encoding="utf-8")
    notices = notices_file.read_text(encoding="utf-8")
    skill = (STANDALONE / "SKILL.md").read_text(encoding="utf-8")
    media_strategy = (STANDALONE / "references/media-strategy.md").read_text(encoding="utf-8")

    # Bundled Archify version cross-check, before the per-document "guidance is
    # missing" assertions, so a version bump reports which file is stale rather
    # than that some sentence disappeared.
    require(
        "codex/skills/archify/package.json" in installer,
        "install.sh must derive the bundled Archify version from codex/skills/archify/package.json",
    )
    require(
        "archify v$ARCHIFY_VERSION" in installer,
        "install.sh must print the derived bundled Archify version",
    )
    for name, text in (
        ("install.sh", installer),
        ("AGENTS.md", agent_guidance),
        ("CLAUDE.md", claude_guidance),
        ("THIRD_PARTY_NOTICES.md", notices),
        ("README.md", readme),
        ("README.en.md", readme_en),
        ("README.ko.md", readme_ko),
        ("README.ja.md", readme_ja),
    ):
        stale = sorted(archify_versions_mentioned(text) - {ARCHIFY_VERSION})
        require(
            not stale,
            f"{name} names Archify version(s) {', '.join(stale)} "
            f"but codex/skills/archify/package.json declares {ARCHIFY_VERSION}",
        )

    legacy_diagram_name = "draw" + "io"
    for path in (
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "install.sh",
        STANDALONE / "SKILL.md",
        STANDALONE / "references/architecture-diagrams.md",
    ):
        require(legacy_diagram_name not in path.read_text(encoding="utf-8").lower(), f"legacy diagram companion reference remains: {path}")
    require("final response MUST include" in agent_guidance, "agent post-install reporting contract is missing")
    require("im-not-ai" in agent_guidance and "humanize-korean" in agent_guidance, "agent im-not-ai guidance is missing")
    require("/humanize-korean" in agent_guidance and "$humanize-korean" in agent_guidance, "agent im-not-ai invocation guidance is missing")
    require("tt-a1i/archify" in agent_guidance and "self-contained HTML" in agent_guidance, "agent Archify bundle guidance is missing")
    require(
        "bundled" in agent_guidance and f"Archify v{ARCHIFY_VERSION}" in agent_guidance,
        "agent bundled Archify version guidance is missing",
    )
    require("im-not-ai" in agent_guidance and "explicitly agrees" in agent_guidance, "optional im-not-ai consent contract is missing")
    require("does not include a raster image generator" in agent_guidance, "agent Claude image-generation guidance is missing")
    require("Required when Gemini CLI was installed" in agent_guidance, "agent Gemini post-install guidance is missing")
    require("availability is sufficient consent for use" in agent_guidance, "installed companion auto-use contract is missing")
    require("Read and follow `AGENTS.md`" in claude_guidance, "Claude repository guidance does not inherit AGENTS.md")

    # CLAUDE.md used to describe Archify as optional and consent-gated while
    # install.sh installed it unconditionally, so an agent following CLAUDE.md
    # asked a question it could not honour.
    require("bundled" in claude_guidance.lower(), "CLAUDE.md must state that Archify is bundled")
    require(
        "Never offer to install Archify" in claude_guidance,
        "CLAUDE.md must forbid asking for consent to install the bundled Archify",
    )
    require(
        "not** bundled" in claude_guidance and "im-not-ai" in claude_guidance,
        "CLAUDE.md must keep im-not-ai explicitly unbundled",
    )
    require(
        "no optional tool, credential, or paid service may be installed or configured without explicit consent"
        in claude_guidance,
        "CLAUDE.md must keep the explicit-consent contract for optional tooling",
    )
    require(
        "does not include a raster image generator" in claude_guidance,
        "CLAUDE.md must keep the image-generation consent notice",
    )

    # README structure: README.md is the canonical Korean landing page, and
    # README.ko.md is a short pointer at it. Byte-identical README files let a
    # single edit drift a second document while every assertion still passed.
    readme_files = {
        "README.md": readme,
        "README.en.md": readme_en,
        "README.ko.md": readme_ko,
        "README.ja.md": readme_ja,
    }
    names = sorted(readme_files)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            require(
                readme_files[first] != readme_files[second],
                f"{first} and {second} are byte-identical; they must not be maintained as two documents",
            )
    require(
        len(readme_ko.encode("utf-8")) <= README_KO_POINTER_MAX_BYTES,
        "README.ko.md must stay a short pointer to README.md, not a second Korean document",
    )
    require("[README.md](README.md)" in readme_ko, "README.ko.md must link to the canonical README.md")

    require("AI 에이전트에게 설치를 맡긴 경우" in readme, "README AI-agent installation guidance is missing")
    require("Claude Code 기본 설치에는 래스터 이미지 생성기가 포함되지 않습니다" in readme, "README Claude image-generation notice is missing")
    require("Gemini CLI Agent Skill" in readme, "README Gemini installation guidance is missing")
    require(f"Archify v{ARCHIFY_VERSION}을 독립 스킬로 함께 제공" in readme, "README bundled Archify guidance is missing")
    require("다시 허락을 묻지 않고 자동 사용" in readme, "README installed skill auto-use guidance is missing")
    require("GitHub Releases" in readme, "README release-asset origin notice is missing")
    require("README.en.md" in readme and "README.ja.md" in readme, "README language navigation is missing")
    require("README.md" in readme_en and "README.ja.md" in readme_en, "English README language navigation is missing")
    require("README.md" in readme_ja and "README.en.md" in readme_ja, "Japanese README language navigation is missing")
    require("squint contact sheet" in readme_en, "English README squint guidance is missing")
    require("squint contact sheet" in readme_ja, "Japanese README squint guidance is missing")
    require("squint review" in readme, "Korean README squint guidance is missing")
    require(f"bundles Archify v{ARCHIFY_VERSION}" in readme_en, "English README bundled Archify guidance is missing")
    require(f"Archify v{ARCHIFY_VERSION}を同梱" in readme_ja, "Japanese README bundled Archify guidance is missing")
    require("Post-install guidance:" in installer, "installer post-install guidance is missing")
    require("epoko77-ai/im-not-ai" in installer, "installer im-not-ai notice is missing")
    require("tt-a1i/archify" in installer, "installer Archify notice is missing")
    require("Bundled Archify skipped; existing installation preserved" in installer, "installer Archify preservation contract is missing")
    require("ask whether to install im-not-ai only" in installer, "installer optional im-not-ai consent notice is missing")
    require("does not include a raster image generator by default" in installer, "installer Claude image-generation notice is missing")
    require("Gemini CLI Agent Skills" in installer, "installer Gemini post-install notice is missing")
    require("Available humanize-korean and bundled Archify are used automatically" in installer, "installer skill auto-use notice is missing")

    # Installer regressions that shipped silently before CI existed.
    require(
        "scripts/validate_repository.py" in installer and "--skip-validation" in installer,
        "install.sh must verify distribution parity before installing, with a documented opt-out flag",
    )
    require(
        ".build-html-slides-backups" in installer,
        "install.sh must back up outside the skills scan root; a backup beside the skill registers as a duplicate skill",
    )
    require(
        ".build-html-slides-backups" in uninstaller,
        "uninstall.sh must clean or report the installer's backups",
    )
    require(
        "$dest.bak.$STAMP" not in installer,
        "install.sh must not create backups inside the skills scan root",
    )
    require(
        re.search(r"^\s*run\s+cp\s+-R\b", installer, re.MULTILINE) is None,
        "install.sh must copy directory trees through the transient-artifact filter, not cp -R",
    )
    for artifact in ("__pycache__", ".pytest_cache", "*.pyc"):
        require(
            artifact in installer,
            f"install.sh copy mode must exclude {artifact} from the user's home",
        )
    require(
        "scripts/validate_repository.py" in updater,
        "update.sh must validate the pulled commit before reinstalling",
    )
    require(
        "remote get-url" in updater,
        "update.sh must report a missing remote instead of surfacing a raw git error",
    )
    require(
        "refs/tags/v$VERSION" in packager,
        "package-release.sh must refuse to rebuild an already tagged version",
    )
    require("pure-HTML, image-free, or typography/diagram-only" in skill, "skill default photo-discovery contract is missing")
    require("perform a bounded search for relevant sourced photographs" in media_strategy, "media strategy default discovery contract is missing")
    require("suggest_design_directions.py" in skill, "skill design-candidate routing is missing")
    require("Squint review is an auxiliary" in skill, "skill squint limitation contract is missing")
    require("Bundled distributions include `archify`" in skill, "skill bundled Archify routing is missing")
    require("tt-a1i/archify" in notices, "Archify third-party notice is missing")
    require("Cocoon-AI/architecture-diagram-generator" in notices, "Archify upstream attribution is missing")
    require(ARCHIFY_VERSION in notices, "Archify version notice is missing")
    require(ARCHIFY_UPSTREAM_COMMIT in notices, "Archify commit notice is missing")
    require(ARCHIFY_PACKAGE_SHA256 in notices, "Archify package digest notice is missing")


    print(
        "Repository validation passed "
        f"({len(tree_hashes(STANDALONE))} slide-skill files, "
        f"{len(tree_hashes(ARCHIFY_STANDALONE))} Archify files)."
    )


if __name__ == "__main__":
    main()
