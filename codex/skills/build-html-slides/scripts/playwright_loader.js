'use strict';

const os = require('os');
const path = require('path');

function managedRuntimeRoot() {
  return path.resolve(
    process.env.BUILD_HTML_SLIDES_RUNTIME || path.join(os.homedir(), '.build-html-slides', 'runtime')
  );
}

function playwrightCandidates() {
  const configured = process.env.BUILD_HTML_SLIDES_PLAYWRIGHT_ROOT;
  return [
    'playwright',
    configured ? path.join(path.resolve(configured), 'node_modules', 'playwright') : null,
    configured ? path.resolve(configured) : null,
    path.join(managedRuntimeRoot(), 'node_modules', 'playwright'),
    path.join(os.homedir(), '.local', 'lib', 'node_modules', 'playwright'),
    '/usr/local/lib/node_modules/playwright',
    '/usr/lib/node_modules/playwright',
  ].filter(Boolean);
}

function loadPlaywright() {
  for (const candidate of playwrightCandidates()) {
    try {
      return require(candidate);
    } catch (error) {
      if (error.code !== 'MODULE_NOT_FOUND') throw error;
    }
  }
  throw new Error(
    'Playwright is not installed. After user approval, run '
    + '`python3 scripts/install_browser_dependencies.py --consent` from the skill directory.'
  );
}

module.exports = { loadPlaywright, managedRuntimeRoot, playwrightCandidates };
