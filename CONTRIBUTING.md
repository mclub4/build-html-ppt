# Contributing

Issues and focused pull requests are welcome.

1. Keep the standalone skill under `codex/skills/build-html-slides` as the source of truth.
2. Run `./scripts/sync-distributions.sh` after changing the skill.
3. Run `npm run check`, `npm run check:browser`, and `npm test` before opening a pull request.
4. Keep generated decks, browser captures, source caches, and `node_modules` out of commits.

Changes that alter validation contracts should include or update focused tests.

