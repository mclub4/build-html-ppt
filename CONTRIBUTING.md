# Contributing

Issues and focused pull requests are welcome.

1. Keep the shared skill under `codex/skills/build-html-slides` as the source of truth. `.claude/skills/`, `.gemini/skills/`, and `plugins/` are generated mirrors; never edit them directly.
2. Run `./scripts/sync-distributions.sh` after changing it; the script updates the Codex plugin, Claude skill, and Gemini skill copies.
3. Run `npm run check`, `npm run check:browser`, and `npm test` before opening a pull request. `.github/workflows/ci.yml` runs the same commands on every push and pull request, so a skipped sync fails CI instead of reaching a release.
4. Keep generated decks, browser captures, source caches, and `node_modules` out of commits.

Changes that alter validation contracts should include or update focused tests.

## Repository conventions the validator enforces

- **Bundled Archify version.** `codex/skills/archify/package.json` is the only place the version is defined. `install.sh` derives it at runtime; `AGENTS.md`, `THIRD_PARTY_NOTICES.md`, and the READMEs state it as text, and `scripts/validate_repository.py` fails if any of them names a different version.
- **READMEs.** `README.md` is the canonical Korean document and the repository landing page. `README.en.md` and `README.ja.md` are the translations. `README.ko.md` is a short pointer that keeps older links working — do not grow it into a second Korean document. The validator rejects any two byte-identical README files.
- **Release archives.** `dist/` is gitignored and no archive is ever committed. `./scripts/package-release.sh` builds them locally and refuses to rebuild a version that already carries a git tag; bump `package.json` first.
- **Installer safety.** `install.sh` verifies distribution parity before writing anything (`--skip-validation` opts out for offline or minimal environments), filters transient artifacts out of `--copy` installs, and backs up displaced installations to `<home>/.build-html-slides-backups/` rather than beside the skill, where the agent's skills scan would register the backup as a duplicate skill.
