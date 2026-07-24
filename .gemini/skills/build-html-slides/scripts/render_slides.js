#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { fileURLToPath, pathToFileURL } = require('url');
const { loadPlaywright } = require('./playwright_loader');

const CONTRACT_PATH = path.join(__dirname, 'validation_contract.json');
const CONTRACT = JSON.parse(fs.readFileSync(CONTRACT_PATH, 'utf8'));
const BASE_PROFILES = [...CONTRACT.base_profiles];
const RESPONSIVE_PROFILES = [...CONTRACT.responsive_profiles];
const PROFILES = Object.fromEntries(Object.entries(CONTRACT.profiles).map(([name, profile]) => [name, {
  viewport: profile.viewport,
  visualViewport: profile.visual_viewport,
  screenshot: profile.screenshot,
  zoom: profile.zoom,
  scaleMode: profile.scale_mode,
}]));
const CHECKS_BY_CHANGE = CONTRACT.checks_by_change;
const AUTOMATION_CHECKS_BY_CHANGE = CONTRACT.automation_checks_by_change;
const REVIEW_BATCH_SIZE = CONTRACT.review_batch_size;
const IMPACT_SCOPES = new Set(CONTRACT.impact_scopes);
const CONTENT_CHANGE_CATEGORIES = new Set(CONTRACT.content_change_categories);
const SQUINT_REVIEW_CHECKS = [...CONTRACT.squint_review_checks];
const MEDIA_WAIT_TIMEOUT_MS = 15000;
const QUALITY_DIMENSIONS = [
  'story', 'art_direction', 'layout_rhythm', 'typography',
  'imagery', 'composition', 'evidence', 'presentation_utility',
];
const CHROMIUM_LAUNCH_OPTIONS = {
  headless: true,
  args: ['--allow-file-access-from-files'],
};
const MOTION_OVERRIDE = `
  *, *::before, *::after {
    animation: none !important;
    caret-color: transparent !important;
    scroll-behavior: auto !important;
    transition: none !important;
  }
`;
// Measurement scripts are compiled once per page (CSP-safe, see installPageRuntime) and then
// invoked per slide/profile by manifest field name.
const MEASURE_NAMESPACE = '__buildHtmlSlidesMeasure';
const MEASURE_SCRIPTS = {
  text_geometry: 'measure_text_bounds.js',
  contrast_geometry: 'measure_contrast.js',
  container_density: 'measure_container_density.js',
  control_geometry: 'measure_geometry.js',
  image_geometry: 'measure_image_geometry.js',
};
const MEASURE_FIELD_BY_CHECK = {
  text_bounds: 'text_geometry',
  contrast: 'contrast_geometry',
  container_density: 'container_density',
  controls: 'control_geometry',
  image_geometry: 'image_geometry',
  font_integrity: 'font_integrity',
};
// Debug overlay geometry thresholds. Every value is a deterministic measurement input, never a
// reviewer judgement call.
const DEBUG_OVERLAY_CONFIG = {
  minContainerAreaRatio: 0.012,
  maxContainers: 48,
  maxTextLines: 320,
  maxEntries: 900,
  overflowTolerance: 1.5,
  minOverflowArea: 24,
  minCollisionArea: 24,
  backdropAreaRatio: 0.85,
  navPadding: 14,
  navExclusion: { width: 280, height: 84 },
  palette: {
    slide: { stroke: '#ffffff', fill: 'transparent', width: 1, style: 'dashed', ink: '#101010' },
    container: { stroke: '#00e5ff', fill: 'rgba(0,229,255,0.06)', width: 2, style: 'solid', ink: '#00181c' },
    image: { stroke: '#ff2fd0', fill: 'rgba(255,47,208,0.06)', width: 2, style: 'solid', ink: '#1c0016' },
    'text-line': { stroke: '#76ff03', fill: 'transparent', width: 1, style: 'solid', ink: '#0d1a00' },
    'nav-zone': { stroke: '#ffab00', fill: 'rgba(255,171,0,0.12)', width: 2, style: 'dashed', ink: '#1a1100' },
    'nav-controls': { stroke: '#ffab00', fill: 'transparent', width: 2, style: 'solid', ink: '#1a1100' },
    warning: { stroke: '#ffab00', fill: 'rgba(255,171,0,0.30)', width: 2, style: 'solid', ink: '#1a1100' },
    issue: { stroke: '#ff1744', fill: 'rgba(255,23,68,0.38)', width: 3, style: 'solid', ink: '#ffffff' },
    default: { stroke: '#d0d0d0', fill: 'transparent', width: 1, style: 'solid', ink: '#101010' },
  },
};

function usage(message) {
  if (message) process.stderr.write(`ERROR: ${message}\n`);
  process.stderr.write(
    'usage: node render_slides.js DECK.html [REVIEW_DIR] --mode quick|full '
    + '[--review-risk standard|high] [--slides 3,5-7] '
    + '[--change-type all|text|image|navigation] [--responsive] '
    + '[--fingerprint-cache PATH]\n'
    + '       node render_slides.js DECK.html [REVIEW_DIR] --finalize-prepare\n'
    + '       node render_slides.js --check\n'
    + '       node render_slides.js --fingerprints DECK.html\n'
    + '       node render_slides.js --classify-change DECK.html REVIEW_DIR '
    + 'all|text|image|navigation quick|full standard|high true|false\n'
    + '       node render_slides.js --workspace-dir DECK.html\n'
    + '       node render_slides.js --review-dir DECK.html\n'
    + '       node render_slides.js --clean-workspace DECK.html\n'
  );
  process.exit(2);
}

function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function workspaceRoot() {
  if (process.env.BUILD_HTML_SLIDES_WORKSPACE_ROOT) {
    return path.resolve(process.env.BUILD_HTML_SLIDES_WORKSPACE_ROOT);
  }
  let agentHome;
  if (process.env.BUILD_HTML_SLIDES_AGENT_HOME) {
    agentHome = process.env.BUILD_HTML_SLIDES_AGENT_HOME;
  } else if (process.env.CLAUDE_CONFIG_DIR || process.env.CLAUDE_HOME) {
    agentHome = process.env.CLAUDE_CONFIG_DIR || process.env.CLAUDE_HOME;
  } else if (process.env.GEMINI_HOME) {
    agentHome = process.env.GEMINI_HOME;
  } else {
    const scriptParts = fs.realpathSync.native(__filename).split(path.sep);
    const runsFromClaude = scriptParts.includes('.claude');
    const runsFromGemini = scriptParts.includes('.gemini');
    agentHome = runsFromClaude
      ? path.join(os.homedir(), '.claude')
      : (runsFromGemini
        ? path.join(os.homedir(), '.gemini')
        : (process.env.CODEX_HOME || path.join(os.homedir(), '.codex')));
  }
  return path.join(path.resolve(agentHome), 'build-html-slides', 'workspaces');
}

async function measureFontIntegrity(page, cdp) {
  const collected = await page.evaluate(() => {
    const normalizeFamily = value => value.trim().replace(/^['"]|['"]$/g, '').toLowerCase();
    const declaredFamilies = new Set();
    const declaredSources = new Map();
    const collectRules = rules => {
      for (const rule of rules) {
        if (rule.type === CSSRule.FONT_FACE_RULE) {
          const family = normalizeFamily(rule.style.getPropertyValue('font-family'));
          declaredFamilies.add(family);
          const sources = declaredSources.get(family) || [];
          sources.push(rule.style.getPropertyValue('src'));
          declaredSources.set(family, sources);
        } else if (rule.cssRules) {
          collectRules(rule.cssRules);
        }
      }
    };
    for (const sheet of document.styleSheets) {
      try { collectRules(sheet.cssRules); } catch (_error) { /* local offline decks remain inspectable */ }
    }

    const active = document.querySelector('.slide.active');
    if (!active) return { candidates: [], usage: [] };
    document.getElementById('__font-integrity-audit')?.remove();
    const root = document.createElement('div');
    root.id = '__font-integrity-audit';
    root.setAttribute('aria-hidden', 'true');
    root.style.cssText = 'position:fixed;left:0;top:0;color:transparent;pointer-events:none;z-index:2147483647';
    document.body.appendChild(root);

    const records = [];
    const usage = [];
    const seen = new Set();
    const usageSeen = new Set();
    const loadedFamilies = new Set(
      [...(document.fonts || [])]
        .filter(face => face.status === 'loaded')
        .map(face => normalizeFamily(face.family))
    );
    const elements = [...active.querySelectorAll('*')].filter(element => (
      element.namespaceURI === 'http://www.w3.org/1999/xhtml'
      && !element.closest('[data-text-bounds-ignore]')
    ));
    for (const element of elements) {
      const direct = [...element.childNodes]
        .filter(node => node.nodeType === Node.TEXT_NODE)
        .map(node => node.nodeValue)
        .join('');
      if (!direct.trim()) continue;
      const style = getComputedStyle(element);
      const families = style.fontFamily.match(/(?:"[^"]*"|'[^']*'|[^,])+/g) || [];
      const normalizedFamilies = families.map(normalizeFamily);
      const family = normalizedFamilies.find(value => declaredFamilies.has(value)) || '';
      const source = element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id
        || direct.trim().replace(/\s+/g, ' ').slice(0, 48) || element.tagName.toLowerCase();
      const styleKey = [
        style.fontFamily, style.fontWeight, style.fontStyle,
        style.fontStretch, style.fontVariationSettings,
      ].join('|');
      if (!usageSeen.has(styleKey)) {
        usageSeen.add(styleKey);
        const id = `font-usage-${usage.length + 1}`;
        element.dataset.fontUsageId = id;
        const faceSources = family ? (declaredSources.get(family) || []) : [];
        usage.push({
          id,
          source,
          primaryFamily: normalizedFamilies[0] || '',
          declaredFamily: family,
          stack: style.fontFamily,
          weight: style.fontWeight,
          styleKey,
          loadedFace: family ? loadedFamilies.has(family) : false,
          bundledWoff2: faceSources.some(value => (
            /url\([^)]*\.woff2[^)]*\)/i.test(value)
            && !/https?:\/\//i.test(value)
          )),
        });
      }
      const hangul = [...new Set(Array.from(direct).filter(character => /[\uAC00-\uD7A3]/.test(character)))];
      if (!hangul.length) continue;
      if (!family) continue;
      for (const character of hangul) {
        const key = `${styleKey}|${character}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const id = `font-audit-${records.length + 1}`;
        const probe = document.createElement('span');
        probe.dataset.fontIntegrityId = id;
        probe.textContent = character;
        Object.assign(probe.style, {
          position: 'absolute',
          left: '0',
          top: '0',
          fontFamily: style.fontFamily,
          fontWeight: style.fontWeight,
          fontStyle: style.fontStyle,
          fontStretch: style.fontStretch,
          fontSize: style.fontSize,
          fontVariationSettings: style.fontVariationSettings,
          fontFeatureSettings: style.fontFeatureSettings,
          fontSynthesis: 'none',
          whiteSpace: 'pre',
        });
        root.appendChild(probe);
        records.push({ id, character, family, styleKey, weight: style.fontWeight, source });
      }
    }
    return { candidates: records, usage };
  });

  const candidates = collected.candidates || [];
  const usage = collected.usage || [];
  if (!candidates.length && !usage.length) {
    return { ok: true, checked: 0, issues: [], warnings: [], used_fonts: [] };
  }
  await cdp.send('DOM.enable');
  await cdp.send('CSS.enable');
  await cdp.send('DOM.getDocument', { depth: -1 });
  const platformFontsFor = async selector => {
    const evaluated = await cdp.send('Runtime.evaluate', {
      expression: `document.querySelector(${JSON.stringify(selector)})`,
      returnByValue: false,
    });
    const objectId = evaluated.result?.objectId;
    if (!objectId) return [];
    const { nodeId } = await cdp.send('DOM.requestNode', { objectId });
    if (!nodeId) return [];
    const result = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
    return result.fonts || [];
  };
  const audited = [];
  for (const candidate of candidates) {
    const fonts = await platformFontsFor(`[data-font-integrity-id="${candidate.id}"]`);
    const font = [...fonts].sort((left, right) => right.glyphCount - left.glyphCount)[0] || null;
    audited.push({
      ...candidate,
      signature: font ? `${font.isCustomFont ? 'custom' : 'system'}:${font.postScriptName || font.familyName}` : 'missing',
      custom: font?.isCustomFont === true,
    });
  }
  const usedFonts = [];
  for (const item of usage) {
    const fonts = await platformFontsFor(`[data-font-usage-id="${item.id}"]`);
    const platformFonts = fonts.map(font => ({
      family: font.familyName || '',
      postscript: font.postScriptName || '',
      custom: font.isCustomFont === true,
      glyph_count: font.glyphCount || 0,
    }));
    usedFonts.push({
      source: item.source,
      primary_family: item.primaryFamily,
      declared_family: item.declaredFamily,
      stack: item.stack,
      weight: item.weight,
      bundled_woff2: item.bundledWoff2,
      loaded_face: item.loadedFace,
      custom: item.loadedFace || platformFonts.some(font => font.custom && font.glyph_count > 0),
      platform_fonts: platformFonts,
    });
  }
  await page.evaluate(() => {
    document.getElementById('__font-integrity-audit')?.remove();
    document.querySelectorAll('[data-font-usage-id]').forEach(element => {
      delete element.dataset.fontUsageId;
    });
  });

  const issues = [];
  const groups = new Map();
  for (const item of audited) {
    const records = groups.get(item.styleKey) || [];
    records.push(item);
    groups.set(item.styleKey, records);
  }
  for (const records of groups.values()) {
    const customCounts = new Map();
    for (const record of records.filter(item => item.custom)) {
      customCounts.set(record.signature, (customCounts.get(record.signature) || 0) + 1);
    }
    const expected = [...customCounts.entries()].sort((left, right) => right[1] - left[1])[0]?.[0] || null;
    const fallback = records.filter(record => !record.custom || (expected && record.signature !== expected));
    if (!fallback.length) continue;
    const characters = [...new Set(fallback.map(record => record.character))]
      .sort((left, right) => left.codePointAt(0) - right.codePointAt(0));
    const rendered = characters.map(character => (
      `${character}(U+${character.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')})`
    )).join(', ');
    const sample = fallback[0];
    issues.push(
      `${sample.source}: locally declared font-family "${sample.family}" weight ${sample.weight} `
      + `falls back to another platform font for Hangul ${rendered}; use a complete Korean font or rebuild the subset after copy changes`
    );
  }
  for (const font of usedFonts) {
    if (font.declared_family && font.bundled_woff2 && !font.custom) {
      issues.push(
        `${font.source}: bundled WOFF2 family "${font.declared_family}" did not become the actual rendered font`
      );
    }
  }
  return {
    ok: issues.length === 0,
    checked: candidates.length,
    issues,
    warnings: [],
    used_fonts: usedFonts,
  };
}

function deckWorkspaceId(deck) {
  const absolute = path.resolve(deck);
  const resolved = fs.existsSync(absolute) ? fs.realpathSync.native(absolute) : absolute;
  const stem = path.basename(resolved, path.extname(resolved)).normalize('NFKC');
  const slug = stem
    .replace(/[^\p{L}\p{N}._-]+/gu, '-')
    .replace(/^[-_.]+|[-_.]+$/g, '')
    .slice(0, 48) || 'deck';
  return `${slug}-${sha256(resolved).slice(0, 10)}`;
}

function defaultWorkspaceDirectory(deck) {
  return path.join(workspaceRoot(), deckWorkspaceId(deck));
}

function defaultReviewDirectory(deck) {
  return path.join(defaultWorkspaceDirectory(deck), 'review');
}

function parseSlideSelection(value) {
  const selected = new Set();
  for (const token of value.split(',')) {
    const match = token.trim().match(/^(\d+)(?:-(\d+))?$/);
    if (!match) usage(`invalid --slides selection: ${value}`);
    const start = Number(match[1]);
    const end = Number(match[2] || match[1]);
    if (start < 1 || end < start) usage(`invalid --slides range: ${token}`);
    for (let number = start; number <= end; number += 1) selected.add(number);
  }
  return selected;
}

function parseArguments(argv) {
  if (argv.length < 1) usage();
  const deck = path.resolve(argv[0]);
  const explicitOutput = argv[1] && !argv[1].startsWith('--');
  const output = explicitOutput ? path.resolve(argv[1]) : defaultReviewDirectory(deck);
  const optionStart = explicitOutput ? 2 : 1;
  let mode = null;
  let slides = null;
  let changeType = 'all';
  let responsive = false;
  let reviewRisk = 'standard';
  let phase = 'iteration';
  let finalizeOnly = false;
  let fingerprintCache = null;
  for (let index = optionStart; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--mode' && argv[index + 1]) {
      mode = argv[++index];
    } else if (argument === '--review-risk' && argv[index + 1]) {
      reviewRisk = argv[++index];
    } else if (argument === '--slides' && argv[index + 1]) {
      slides = parseSlideSelection(argv[++index]);
    } else if (argument === '--change-type' && argv[index + 1]) {
      changeType = argv[++index];
    } else if (argument === '--responsive') {
      responsive = true;
    } else if (argument === '--finalize-prepare' || argument === '--finalize') {
      phase = 'final';
      finalizeOnly = true;
    } else if (argument === '--fingerprint-cache' && argv[index + 1]) {
      fingerprintCache = path.resolve(argv[++index]);
    } else {
      usage(`unknown argument: ${argument}`);
    }
  }
  if (mode !== null && !['quick', 'full'].includes(mode)) usage(`mode must be quick or full: ${mode}`);
  if (!finalizeOnly && mode === null) usage('--mode quick|full is required; select the user-approved mode explicitly');
  if (!['standard', 'high'].includes(reviewRisk)) usage(`review risk must be standard or high: ${reviewRisk}`);
  if (!CHECKS_BY_CHANGE[changeType]) usage(`invalid change type: ${changeType}`);
  if (!fs.existsSync(deck) || !fs.statSync(deck).isFile()) usage(`deck not found: ${deck}`);
  const protectedPaths = new Set([path.parse(output).root, os.homedir(), process.cwd(), path.dirname(deck), deck]);
  if (protectedPaths.has(output) || deck.startsWith(`${output}${path.sep}`)) {
    usage(`review directory must be a dedicated disposable child path: ${output}`);
  }
  if (finalizeOnly && slides) usage('--finalize-prepare cannot be combined with --slides');
  return {
    deck,
    output,
    workspace: explicitOutput ? path.dirname(output) : defaultWorkspaceDirectory(deck),
    workspaceStorage: explicitOutput ? 'explicit-review-dir' : 'agent-home',
    mode,
    reviewRisk,
    slides,
    changeType,
    responsive,
    phase,
    finalizeOnly,
    fingerprintCache,
  };
}

function profileNames(responsive) {
  return responsive ? [...BASE_PROFILES, ...RESPONSIVE_PROFILES] : [...BASE_PROFILES];
}

function expandWithNeighbors(selected, slideCount) {
  const expanded = new Set();
  for (const number of selected) {
    for (const candidate of [number - 1, number, number + 1]) {
      if (candidate >= 1 && candidate <= slideCount) expanded.add(candidate);
    }
  }
  return expanded;
}

async function waitForMedia(page) {
  await page.evaluate(async timeoutMs => {
    const mediaReady = (async () => {
      if (document.fonts?.ready) await document.fonts.ready;
      await Promise.all([...document.images].map(image => image.complete ? null : new Promise(resolve => {
        image.addEventListener('load', resolve, { once: true });
        image.addEventListener('error', resolve, { once: true });
      })));
    })();
    await Promise.race([
      mediaReady,
      new Promise((_resolve, reject) => setTimeout(
        () => reject(new Error(`fonts or images did not settle within ${timeoutMs}ms`)),
        timeoutMs
      )),
    ]);
  }, MEDIA_WAIT_TIMEOUT_MS);
  await waitForFrames(page);
}

async function waitForStyles(page) {
  await page.evaluate(async timeoutMs => {
    const pending = [...document.querySelectorAll('link[rel~="stylesheet"]')]
      .filter(link => !link.sheet)
      .map(link => new Promise(resolve => {
        link.addEventListener('load', resolve, { once: true });
        link.addEventListener('error', resolve, { once: true });
      }));
    if (!pending.length) return;
    await Promise.race([
      Promise.all(pending),
      new Promise(resolve => setTimeout(resolve, timeoutMs)),
    ]);
  }, MEDIA_WAIT_TIMEOUT_MS);
}

async function waitForFrames(page) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

/* eslint-disable */
// Runs inside the page, never in Node. Installs window[namespace].debugOverlay, which draws
// labelled, colour-coded boundary rectangles over the live pixels so a visual reviewer can see
// which card owns which image, where each text line's ink box sits, and where the reserved
// navigation zone is. Overflow and intersection regions are filled in a warning colour.
//
// Overlay entry interface (also accepted from any measure_*.js result under an `overlay` key):
//   { kind: string, rect: {x, y, width, height} | DOMRect-like, label: string,
//     severity: 'info' | 'warning' | 'issue' }
// Coordinates are CSS pixels in viewport space, exactly as getBoundingClientRect() reports them.
function debugOverlayRuntime(namespace, config) {
  const OVERLAY_ID = '__build-html-slides-debug-overlay';
  const round = value => Math.round(value * 10) / 10;
  const boxOf = rect => ({
    x: round(rect.x ?? rect.left ?? 0),
    y: round(rect.y ?? rect.top ?? 0),
    width: round(rect.width ?? 0),
    height: round(rect.height ?? 0),
  });
  const areaOf = rect => Math.max(0, rect.width) * Math.max(0, rect.height);
  const intersect = (left, right) => {
    const x = Math.max(left.x, right.x);
    const y = Math.max(left.y, right.y);
    return {
      x: round(x),
      y: round(y),
      width: round(Math.min(left.x + left.width, right.x + right.width) - x),
      height: round(Math.min(left.y + left.height, right.y + right.height) - y),
    };
  };
  const union = (left, right) => {
    const x = Math.min(left.x, right.x);
    const y = Math.min(left.y, right.y);
    return {
      x: round(x),
      y: round(y),
      width: round(Math.max(left.x + left.width, right.x + right.width) - x),
      height: round(Math.max(left.y + left.height, right.y + right.height) - y),
    };
  };
  // Strips of `inner` that fall outside `outer`; empty when inner is contained.
  const outsideStrips = (inner, outer, tolerance) => {
    const strips = [];
    const add = (x, y, width, height) => {
      if (width > tolerance && height > tolerance) {
        strips.push({ x: round(x), y: round(y), width: round(width), height: round(height) });
      }
    };
    const innerRight = inner.x + inner.width;
    const innerBottom = inner.y + inner.height;
    const outerRight = outer.x + outer.width;
    const outerBottom = outer.y + outer.height;
    add(inner.x, inner.y, Math.min(innerRight, outer.x) - inner.x, inner.height);
    add(Math.max(inner.x, outerRight), inner.y, innerRight - Math.max(inner.x, outerRight), inner.height);
    const bandLeft = Math.max(inner.x, outer.x);
    const bandRight = Math.min(innerRight, outerRight);
    add(bandLeft, inner.y, bandRight - bandLeft, Math.min(innerBottom, outer.y) - inner.y);
    add(bandLeft, Math.max(inner.y, outerBottom), bandRight - bandLeft, innerBottom - Math.max(inner.y, outerBottom));
    return strips;
  };
  const describe = element => {
    if (!element || !element.tagName) return 'node';
    const classes = (element.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    return [
      element.tagName.toLowerCase(),
      element.id ? `#${element.id}` : '',
      classes.length ? `.${classes.join('.')}` : '',
    ].join('');
  };
  const opaqueBackground = value => {
    const match = /^rgba?\(([^)]+)\)/.exec(value || '');
    if (!match) return false;
    const parts = match[1].split(',').map(part => Number.parseFloat(part));
    return parts.length < 4 || parts[3] > 0.02;
  };
  const visible = element => {
    const style = getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const collect = () => {
    const active = document.querySelector('.slide.active');
    if (!active) return [];
    const entries = [];
    const slideRect = boxOf(active.getBoundingClientRect());
    entries.push({ kind: 'slide', rect: slideRect, label: 'active slide', severity: 'info' });
    const slideArea = Math.max(1, slideRect.width * slideRect.height);

    const containerCandidates = [];
    const imageNodes = [];
    const mediaTags = new Set(['IMG', 'VIDEO', 'CANVAS', 'SVG', 'PICTURE', 'IMAGE']);
    for (const element of active.querySelectorAll('*')) {
      if (element.id === OVERLAY_ID || element.closest(`#${OVERLAY_ID}`)) continue;
      if (!visible(element)) continue;
      const rect = boxOf(element.getBoundingClientRect());
      const style = getComputedStyle(element);
      const media = mediaTags.has(element.tagName);
      const backgroundImage = (style.backgroundImage || 'none').includes('url(');
      if (media || backgroundImage) {
        imageNodes.push({
          element,
          rect,
          label: `${media ? 'image' : 'background'} ${describe(element)}`,
        });
      }
      if (media) continue;
      if (areaOf(rect) < slideArea * config.minContainerAreaRatio) continue;
      const clipped = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX)
        || ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY);
      const framed = ['Top', 'Right', 'Bottom', 'Left']
        .some(side => Number.parseFloat(style[`border${side}Width`]) > 0)
        || opaqueBackground(style.backgroundColor)
        || Number.parseFloat(style.borderTopLeftRadius) > 0
        || (style.boxShadow && style.boxShadow !== 'none')
        || clipped;
      if (!framed) continue;
      containerCandidates.push({ element, rect, clipped, label: describe(element) });
    }
    containerCandidates.sort((left, right) => areaOf(right.rect) - areaOf(left.rect));
    const containers = containerCandidates.slice(0, config.maxContainers);
    const containerByElement = new Map(containers.map(item => [item.element, item]));
    containers.forEach(item => entries.push({
      kind: 'container', rect: item.rect, label: `card ${item.label}`, severity: 'info',
    }));

    const slideOwner = { element: active, rect: slideRect, clipped: false, label: 'active slide' };
    const ownerOf = element => {
      let node = element.parentElement;
      while (node && node !== active) {
        if (containerByElement.has(node)) return containerByElement.get(node);
        node = node.parentElement;
      }
      return slideOwner;
    };
    for (const image of imageNodes) {
      entries.push({ kind: 'image', rect: image.rect, label: image.label, severity: 'info' });
      const owner = ownerOf(image.element);
      const strips = outsideStrips(image.rect, owner.rect, config.overflowTolerance);
      const escaped = strips.reduce((total, strip) => total + areaOf(strip), 0);
      if (escaped < config.minOverflowArea) continue;
      const worst = Math.round(Math.max(...strips.map(strip => Math.max(strip.width, strip.height))));
      const label = owner.clipped
        ? `${image.label} is cropped by ${owner.label} (${worst}px hidden)`
        : `${image.label} escapes ${owner.label} by ${worst}px`;
      strips.forEach((strip, index) => entries.push({
        kind: owner.clipped ? 'clipped' : 'overflow',
        rect: strip,
        label: index === 0 ? label : '',
        severity: owner.clipped ? 'warning' : 'issue',
      }));
    }

    const textLines = [];
    const walker = document.createTreeWalker(active, NodeFilter.SHOW_TEXT);
    while (walker.nextNode() && textLines.length < config.maxTextLines) {
      const node = walker.currentNode;
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      const parent = node.parentElement;
      if (!parent || parent.closest(`#${OVERLAY_ID}`) || !visible(parent)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      let first = true;
      for (const raw of range.getClientRects()) {
        if (raw.width < 1 || raw.height < 1) continue;
        const entry = {
          kind: 'text-line',
          rect: boxOf(raw),
          label: first ? describe(parent) : '',
          severity: 'info',
        };
        first = false;
        textLines.push({ rect: entry.rect, element: parent });
        entries.push(entry);
        if (textLines.length >= config.maxTextLines) break;
      }
    }

    // Text ink sitting on top of a discrete photo is the "price over the product shot" defect.
    // A near-full-bleed backdrop is excluded: that is a deliberate art-direction pattern and the
    // contrast measurement already governs it.
    for (const image of imageNodes) {
      if (areaOf(image.rect) >= slideArea * config.backdropAreaRatio) continue;
      let flagged = false;
      for (const line of textLines) {
        if (image.element.contains(line.element)) continue;
        const overlap = intersect(line.rect, image.rect);
        if (areaOf(overlap) < config.minCollisionArea) continue;
        entries.push({
          kind: 'text-over-image',
          rect: overlap,
          label: flagged ? '' : `text ink over ${image.label}`,
          severity: 'warning',
        });
        flagged = true;
      }
    }

    const rootStyle = getComputedStyle(document.documentElement);
    const declared = (name, fallback) => {
      const value = Number.parseFloat(rootStyle.getPropertyValue(name));
      return Number.isFinite(value) && value > 0 ? value : fallback;
    };
    const stageScale = active.offsetWidth ? slideRect.width / active.offsetWidth : 1;
    const zoneWidth = declared('--nav-exclusion-width', config.navExclusion.width) * stageScale;
    const zoneHeight = declared('--nav-exclusion-height', config.navExclusion.height) * stageScale;
    let zone = {
      x: round(slideRect.x + slideRect.width - zoneWidth),
      y: round(slideRect.y + slideRect.height - zoneHeight),
      width: round(zoneWidth),
      height: round(zoneHeight),
    };
    const nav = document.querySelector('.controls, .nav');
    const navRect = nav && visible(nav) ? boxOf(nav.getBoundingClientRect()) : null;
    if (navRect) {
      zone = union(zone, {
        x: navRect.x - config.navPadding,
        y: navRect.y - config.navPadding,
        width: navRect.width + config.navPadding * 2,
        height: navRect.height + config.navPadding * 2,
      });
      entries.push({ kind: 'nav-controls', rect: navRect, label: 'navigation controls', severity: 'info' });
    }
    entries.push({ kind: 'nav-zone', rect: zone, label: 'navigation exclusion zone', severity: 'info' });
    for (const line of textLines) {
      const overlap = intersect(line.rect, zone);
      if (areaOf(overlap) < config.minCollisionArea) continue;
      const onControls = navRect && areaOf(intersect(line.rect, navRect)) >= config.minCollisionArea;
      entries.push({
        kind: 'collision',
        rect: overlap,
        label: onControls ? 'text under navigation controls' : 'text inside nav exclusion zone',
        severity: onControls ? 'issue' : 'warning',
      });
    }
    return entries;
  };

  const normalize = entries => (Array.isArray(entries) ? entries : []).flatMap(entry => {
    const rect = entry && entry.rect;
    if (!rect) return [];
    const box = boxOf(rect);
    if (!Number.isFinite(box.x) || !Number.isFinite(box.y) || box.width <= 0 || box.height <= 0) return [];
    const severity = ['info', 'warning', 'issue'].includes(entry.severity) ? entry.severity : 'info';
    return [{
      kind: String(entry.kind || 'measurement'),
      rect: box,
      label: String(entry.label || ''),
      severity,
    }];
  });

  const clear = () => {
    const existing = document.getElementById(OVERLAY_ID);
    if (existing) existing.remove();
  };

  const paletteFor = entry => {
    if (entry.severity === 'issue') return config.palette.issue;
    if (entry.severity === 'warning') return config.palette.warning;
    return config.palette[entry.kind] || config.palette.default;
  };

  const render = options => {
    clear();
    const settings = options || {};
    const entries = [...collect(), ...normalize(settings.entries)].slice(0, config.maxEntries);
    const layer = document.createElement('div');
    layer.id = OVERLAY_ID;
    layer.setAttribute('aria-hidden', 'true');
    layer.setAttribute('data-text-bounds-ignore', '');
    layer.setAttribute('data-contrast-ignore', '');
    Object.assign(layer.style, {
      position: 'fixed',
      left: '0px',
      top: '0px',
      width: '100%',
      height: '100%',
      margin: '0px',
      pointerEvents: 'none',
      zIndex: '2147483647',
    });
    const counts = {};
    const chips = [];
    for (const entry of entries) {
      counts[entry.kind] = (counts[entry.kind] || 0) + 1;
      const palette = paletteFor(entry);
      const box = document.createElement('div');
      Object.assign(box.style, {
        position: 'absolute',
        left: `${entry.rect.x}px`,
        top: `${entry.rect.y}px`,
        width: `${Math.max(0, entry.rect.width)}px`,
        height: `${Math.max(0, entry.rect.height)}px`,
        boxSizing: 'border-box',
        borderWidth: `${palette.width}px`,
        borderStyle: palette.style,
        borderColor: palette.stroke,
        backgroundColor: palette.fill,
        pointerEvents: 'none',
      });
      if (entry.label) {
        const chip = document.createElement('span');
        chip.textContent = entry.label;
        Object.assign(chip.style, {
          position: 'absolute',
          left: '0px',
          top: entry.rect.y > 16 ? '-15px' : '0px',
          maxWidth: '440px',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          textOverflow: 'ellipsis',
          font: '700 11px/14px ui-monospace, Menlo, Consolas, monospace',
          letterSpacing: '0px',
          padding: '0px 4px',
          color: palette.ink,
          backgroundColor: palette.stroke,
        });
        box.appendChild(chip);
        chips.push({ chip, entry });
      }
      layer.appendChild(box);
    }
    const legend = document.createElement('div');
    // The legend must sit at the top-left: under the zoom150 profile the browser page scale
    // shrinks the visual viewport, so only the top-left corner of the layout viewport is
    // guaranteed to be inside every captured frame.
    Object.assign(legend.style, {
      position: 'absolute',
      left: '10px',
      top: '10px',
      padding: '8px 10px',
      backgroundColor: 'rgba(8,8,10,0.86)',
      color: '#f4f4f2',
      font: '600 12px/17px ui-monospace, Menlo, Consolas, monospace',
      borderRadius: '4px',
      maxWidth: '460px',
    });
    const caption = document.createElement('div');
    caption.textContent = String(settings.caption || 'debug overlay');
    Object.assign(caption.style, { marginBottom: '4px', color: '#ffffff' });
    legend.appendChild(caption);
    for (const [kind, total] of Object.entries(counts).sort()) {
      const row = document.createElement('div');
      const swatch = document.createElement('span');
      const sample = paletteFor({
        kind,
        severity: ['overflow', 'collision'].includes(kind)
          ? 'issue'
          : (['clipped', 'text-over-image'].includes(kind) ? 'warning' : 'info'),
      });
      Object.assign(swatch.style, {
        display: 'inline-block',
        width: '10px',
        height: '10px',
        marginRight: '6px',
        backgroundColor: sample.stroke,
      });
      row.appendChild(swatch);
      row.appendChild(document.createTextNode(`${kind} x${total}`));
      legend.appendChild(row);
    }
    layer.appendChild(legend);
    (document.body || document.documentElement).appendChild(layer);
    // Never let the legend hide a finding label: nudge colliding chips clear of it.
    const legendRect = legend.getBoundingClientRect();
    let nudged = 0;
    for (const { chip, entry } of chips) {
      const chipRect = chip.getBoundingClientRect();
      if (areaOf(intersect(boxOf(chipRect), boxOf(legendRect))) <= 0) continue;
      chip.style.left = `${Math.round(legendRect.right + 6 - entry.rect.x)}px`;
      chip.style.top = `${Math.round(legendRect.bottom + 4 + nudged * 16 - entry.rect.y)}px`;
      nudged += 1;
    }
    return { entries: entries.length, counts };
  };

  const api = window[namespace] || {};
  api.debugOverlay = { collect, render, clear };
  window[namespace] = api;
}
/* eslint-enable */

function measureRuntimeSource(sources) {
  const namespace = JSON.stringify(MEASURE_NAMESPACE);
  const registrations = Object.entries(sources).map(([field, source]) => (
    `  api[${JSON.stringify(field)}] = function () { return (\n${source}\n); };`
  )).join('\n');
  return [
    '(function () {',
    `  var api = window[${namespace}] || {};`,
    registrations,
    `  window[${namespace}] = api;`,
    '})();',
    `(${debugOverlayRuntime.toString()})(${namespace}, ${JSON.stringify(DEBUG_OVERLAY_CONFIG)});`,
  ].join('\n');
}

// Compiling the measurement sources once per page instead of eval-ing them for every
// slide x profile keeps Full Validation inside its time budget, and keeps the page free of
// author-originated eval() so a deck with a Content-Security-Policy still measures. CDP
// Runtime.evaluate is a debugger-privileged compile and is not subject to the page CSP.
async function installPageRuntime(cdp, source) {
  const result = await cdp.send('Runtime.evaluate', {
    expression: source,
    returnByValue: true,
    awaitPromise: false,
  });
  if (result.exceptionDetails) {
    throw new Error(`measurement runtime injection failed: ${result.exceptionDetails.text}`);
  }
}

async function runMeasurement(page, field) {
  return page.evaluate(([namespace, key]) => {
    const api = window[namespace];
    if (!api || typeof api[key] !== 'function') {
      throw new Error(`measurement runtime is not installed for ${key}`);
    }
    return api[key]();
  }, [MEASURE_NAMESPACE, field]);
}

function overlayEntriesFrom(measurements) {
  const entries = [];
  for (const [field, result] of Object.entries(measurements)) {
    for (const entry of result?.overlay || []) {
      entries.push({ ...entry, label: entry?.label || field });
    }
  }
  return entries;
}

function measurementCounts(measurements) {
  let issues = 0;
  let warnings = 0;
  for (const result of Object.values(measurements)) {
    issues += result?.issues?.length || 0;
    warnings += result?.warnings?.length || 0;
  }
  return { issues, warnings };
}

async function captureDebugOverlay(page, { entries, caption, path: imagePath }) {
  const summary = await page.evaluate(([namespace, options]) => (
    window[namespace].debugOverlay.render(options)
  ), [MEASURE_NAMESPACE, { entries, caption }]);
  try {
    await page.screenshot({ path: imagePath, fullPage: false });
  } finally {
    await page.evaluate(namespace => window[namespace].debugOverlay.clear(), MEASURE_NAMESPACE);
  }
  return summary;
}

// A deck may ship a Content-Security-Policy without 'unsafe-inline'; a dynamically appended
// <style> element is then parsed but never applied (style.sheet stays null). Constructed
// stylesheets are not subject to the inline-style directive, so they are the CSP-safe fallback.
// They also stay out of document.styleSheets, which keeps them invisible to collectFingerprints.
async function applyMotionOverride(page) {
  const applied = await page.evaluate(css => {
    const style = document.createElement('style');
    style.setAttribute('data-slide-validation-motion', 'off');
    style.textContent = css;
    (document.head || document.documentElement).appendChild(style);
    if (style.sheet) return 'style-element';
    style.remove();
    try {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(css);
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
      return 'constructed-stylesheet';
    } catch (_error) {
      return 'unavailable';
    }
  }, MOTION_OVERRIDE);
  if (applied === 'unavailable') {
    throw new Error('validation could not disable animations in this document');
  }
  if (applied !== 'style-element') {
    process.stderr.write(`NOTE: deck CSP blocked inline styles; motion disabled via ${applied}\n`);
  }
  return applied;
}

async function preparePage(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await applyMotionOverride(page);
  await waitForStyles(page);
  await waitForMedia(page);
}

async function prepareFingerprintPage(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await applyMotionOverride(page);
  await waitForStyles(page);
  await waitForFrames(page);
}

function htmlEscape(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

async function createSquintContactSheet(browser, manifest, output, workspace) {
  const tmpDirectory = path.join(workspace, 'tmp');
  fs.mkdirSync(tmpDirectory, { recursive: true });
  const htmlPath = path.join(tmpDirectory, 'squint-contact-sheet.html');
  const imagePath = path.join(tmpDirectory, 'squint-contact-sheet.png');
  const cards = manifest.slides.map(record => {
    const relative = record.captures?.normal?.path;
    if (!relative) throw new Error(`slide ${record.slide} has no normal capture for squint review`);
    const capturePath = path.resolve(output, relative);
    if (!fs.existsSync(capturePath)) throw new Error(`squint source capture not found: ${capturePath}`);
    return `<figure><div class="thumb"><img src="${htmlEscape(pathToFileURL(capturePath).href)}" alt=""></div>`
      + `<figcaption>${String(record.slide).padStart(2, '0')}</figcaption></figure>`;
  }).join('');
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}html,body{margin:0;background:#ecece8;color:#181816;font-family:Arial,sans-serif}
    main{width:1280px;padding:34px;display:grid;grid-template-columns:repeat(4,1fr);gap:22px 18px}
    figure{margin:0;min-width:0}.thumb{aspect-ratio:16/9;overflow:hidden;background:#bbb;border:1px solid #aaa}
    img{width:100%;height:100%;object-fit:cover;display:block;filter:blur(2.4px) saturate(.88);transform:scale(1.015)}
    figcaption{padding-top:7px;font-size:13px;font-weight:700;letter-spacing:0;color:#4b4b46}
  </style></head><body><main>${cards}</main></body></html>`;
  fs.writeFileSync(htmlPath, html);
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
  try {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'domcontentloaded' });
    await waitForMedia(page);
    await page.screenshot({ path: imagePath, fullPage: true });
  } finally {
    await page.close();
    fs.rmSync(htmlPath, { force: true });
  }
  const captureHashes = Object.fromEntries(manifest.slides.map(record => [
    String(record.slide), record.captures.normal.sha256,
  ]));
  return {
    status: 'pending',
    reviewer: '',
    reviewer_ref: '',
    review_method: 'vision-squint-contact-sheet',
    artifact_path: path.relative(output, imagePath).split(path.sep).join('/'),
    artifact_sha256: sha256(fs.readFileSync(imagePath)),
    normal_capture_sha256: captureHashes,
    checks: Object.fromEntries(SQUINT_REVIEW_CHECKS.map(name => [name, 'pending'])),
    observation: '',
    limitations: ['text-overlap', 'line-breaks', 'crop', 'distortion', 'overflow'],
  };
}

function hashLocalAsset(url, cache = null) {
  if (cache?.has(url)) return cache.get(url).fingerprint;
  if (!url || !url.startsWith('file:')) return url || '';
  try {
    const filePath = fileURLToPath(url);
    const stat = fs.statSync(filePath, { bigint: true });
    if (!stat.isFile()) return url;
    const digest = sha256(fs.readFileSync(filePath));
    const fingerprint = `${url}:${digest}`;
    cache?.set(url, {
      url,
      path: filePath,
      size: String(stat.size),
      mtime_ns: String(stat.mtimeNs),
      ctime_ns: String(stat.ctimeNs),
      sha256: digest,
      fingerprint,
    });
    return fingerprint;
  } catch (_error) {
    const fingerprint = `${url}:missing`;
    cache?.set(url, { url, path: '', size: '', mtime_ns: '', sha256: '', fingerprint });
    return fingerprint;
  }
}

function localAssetEvidence(url, deckDirectory, { requireWebP = false } = {}) {
  if (!url || !url.startsWith('file:')) {
    return { error: 'identity assets must use local file URLs' };
  }
  try {
    const filePath = fileURLToPath(url);
    if (!fs.statSync(filePath).isFile()) return { error: 'identity asset is not a file' };
    const relative = path.relative(deckDirectory, filePath);
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
      return { error: 'identity assets must stay inside the deck bundle' };
    }
    if (requireWebP && path.extname(filePath).toLowerCase() !== '.webp') {
      return { error: 'canonical identity references must be local WebP files' };
    }
    return {
      path: relative.split(path.sep).join('/'),
      sha256: sha256(fs.readFileSync(filePath)),
    };
  } catch (_error) {
    return { error: 'identity asset is missing or unreadable' };
  }
}

function checksFor(changeType, identityRequired) {
  const checks = [...CHECKS_BY_CHANGE[changeType]];
  if (identityRequired && ['all', 'image'].includes(changeType)) checks.push('identity');
  return checks;
}

function bindIdentityEvidence(record, deckDirectory, profiles) {
  const normalGeometry = record.captures.normal?.image_geometry;
  record.identity_required = normalGeometry?.identityRequired === true;
  record.identity_detection = normalGeometry?.identityDetection || 'none';
  record.identity_targets = [];
  record.identity_review = [];
  if (!record.identity_required) return;

  const items = (normalGeometry?.items || []).filter(item => !item.decorative && item.identity?.subjectId);
  for (const [index, item] of items.entries()) {
    const asset = localAssetEvidence(item.sourceUrl, deckDirectory);
    const reference = localAssetEvidence(item.identity.referenceUrl, deckDirectory, { requireWebP: true });
    const targetId = `slide-${record.slide}-identity-${index + 1}`;
    const identityErrors = [];
    if (asset.error) identityErrors.push(`${item.name}: ${asset.error}`);
    if (reference.error) identityErrors.push(`${item.name}: reference ${reference.error}`);
    if (!asset.error && !reference.error && asset.sha256 === reference.sha256) {
      identityErrors.push(`${item.name}: candidate and canonical identity reference must be different files`);
    }
    for (const profile of profiles) {
      const geometry = record.captures[profile]?.image_geometry;
      if (geometry && identityErrors.length) {
        geometry.issues = [...new Set([...(geometry.issues || []), ...identityErrors])];
        geometry.ok = false;
      }
    }
    record.identity_targets.push({
      target_id: targetId,
      subject_id: item.identity.subjectId,
      subject_name: item.identity.subjectName,
      mode: item.identity.mode,
      cues: item.identity.cues,
      asset_path: asset.path || '',
      asset_sha256: asset.sha256 || '',
      reference_path: reference.path || '',
      reference_sha256: reference.sha256 || '',
    });
  }
  if (['all', 'image'].includes(record.review_scope)) {
    record.identity_review = record.identity_targets.map(target => ({
      target_id: target.target_id,
      subject_name: target.subject_name,
      verdict: 'pending',
      observation: '',
    }));
  }
  record.checks = Object.fromEntries(checksFor(record.review_scope, record.identity_required).map(name => [name, 'pending']));
}

async function collectFingerprints(page) {
  const materials = await page.evaluate(() => {
    const slides = [...document.querySelectorAll('section.slide')];
    const head = document.head.cloneNode(true);
    head.querySelectorAll('[data-slide-validation-motion]').forEach(node => node.remove());
    head.querySelectorAll('style').forEach(node => { node.textContent = ''; });
    const body = document.body.cloneNode(true);
    body.querySelectorAll('section.slide').forEach(node => node.remove());
    const globalStyles = [];
    const slideStyles = slides.map(() => []);
    const slideAssets = slides.map(() => new Set());
    const globalStyleAssets = new Set();
    const globalStructureAssets = new Set();
    const runtimeDependencies = new Set();
    const sourceFiles = new Set();

    const cssDependencies = (cssText, baseUrl) => {
      const found = [];
      for (const match of cssText.matchAll(/url\(\s*(?:"([^"]+)"|'([^']+)'|([^)'"\s]+))\s*\)/gi)) {
        const value = match[1] || match[2] || match[3] || '';
        if (!value || value.startsWith('#') || value.startsWith('data:')) continue;
        try {
          found.push(new URL(value, baseUrl || document.baseURI).href);
        } catch (_error) {
          found.push(value);
        }
      }
      return found;
    };

    const selectorTargets = selectorText => {
      if (/\.active\b|:target\b|\[aria-hidden(?:[\]=])/i.test(selectorText)) return null;
      const query = selectorText
        .replace(/::[a-z-]+(?:\([^)]*\))?/gi, '')
        .replace(/:(?:hover|active|focus|focus-visible|focus-within|visited|target)(?![\w-])/gi, '');
      try {
        const matched = [...document.querySelectorAll(query)];
        if (matched.some(element => !element.closest('section.slide'))) return null;
        const targets = new Set();
        matched.forEach(element => {
          const owner = element.closest('section.slide');
          const index = slides.indexOf(owner);
          if (index >= 0) targets.add(index);
        });
        slides.forEach((slide, index) => {
          if (slide.matches(query)) targets.add(index);
        });
        return [...targets].sort((left, right) => left - right);
      } catch (_error) {
        return null;
      }
    };
    const classifyRules = (rules, context = '', baseUrl = document.baseURI) => {
      for (const rule of [...rules]) {
        if (rule.type === CSSRule.STYLE_RULE) {
          const material = `${context}${rule.cssText}`;
          const assets = cssDependencies(material, baseUrl);
          const targets = selectorTargets(rule.selectorText || '');
          if (targets?.length && targets.length < slides.length) {
            targets.forEach(index => {
              slideStyles[index].push(material);
              assets.forEach(asset => slideAssets[index].add(asset));
            });
          } else if (targets === null || targets?.length === 0 || targets?.length === slides.length) {
            globalStyles.push(material);
            assets.forEach(asset => globalStyleAssets.add(asset));
          }
          continue;
        }
        if (rule.cssRules && typeof rule.conditionText === 'string') {
          classifyRules(rule.cssRules, `${context}@${rule.constructor.name} ${rule.conditionText}{`, baseUrl);
          continue;
        }
        const material = `${context}${rule.cssText}`;
        cssDependencies(material, baseUrl).forEach(asset => globalStyleAssets.add(asset));
        globalStyles.push(material);
      }
    };
    for (const sheet of [...document.styleSheets]) {
      const owner = sheet.ownerNode;
      if (owner?.hasAttribute?.('data-slide-validation-motion')) continue;
      const explicit = (owner?.dataset?.slideScope || '').split(',')
        .map(value => Number.parseInt(value.trim(), 10))
        .filter(number => number >= 1 && number <= slides.length);
      if (explicit.length) {
        const material = owner?.textContent || '';
        const assets = cssDependencies(material, sheet.href || document.baseURI);
        explicit.forEach(number => {
          slideStyles[number - 1].push(material);
          assets.forEach(asset => slideAssets[number - 1].add(asset));
        });
        continue;
      }
      try {
        classifyRules(sheet.cssRules, '', sheet.href || document.baseURI);
        if (sheet.href) {
          sourceFiles.add(sheet.href);
        }
      } catch (_error) {
        if (sheet.href) globalStyleAssets.add(sheet.href);
        globalStyles.push(`unreadable-stylesheet:${sheet.href || owner?.outerHTML || ''}`);
      }
    }
    document.querySelectorAll('script[src], link[href]').forEach(element => {
      const value = element.src || element.href;
      if (value && !element.matches('link[rel~="stylesheet"]')) {
        if (element.matches('script[src]')) runtimeDependencies.add(value);
        else globalStructureAssets.add(value);
      }
    });

    const srcsetUrls = value => {
      const urls = [];
      let position = 0;
      while (position < value.length) {
        while (position < value.length && /[\s,]/.test(value[position])) position += 1;
        const start = position;
        while (position < value.length && !/\s/.test(value[position])) position += 1;
        let candidate = value.slice(start, position);
        const trailingCommas = candidate.match(/,+$/)?.[0]?.length || 0;
        if (trailingCommas) candidate = candidate.slice(0, -trailingCommas);
        if (candidate) urls.push(candidate);
        if (trailingCommas) continue;
        let parentheses = 0;
        while (position < value.length) {
          const character = value[position++];
          if (character === '(') parentheses += 1;
          else if (character === ')' && parentheses) parentheses -= 1;
          else if (character === ',' && !parentheses) break;
        }
      }
      return urls;
    };
    const mediaAssets = element => {
      const candidates = [
        element.currentSrc,
        element.src,
        element.poster,
        element.href?.baseVal || element.href,
        element.getAttribute('href'),
        element.getAttribute('xlink:href'),
      ];
      for (const attribute of ['srcset', 'imagesrcset']) {
        const value = element.getAttribute(attribute);
        if (value) candidates.push(...srcsetUrls(value));
      }
      return [...new Set(candidates.filter(Boolean).map(value => {
        try {
          return new URL(String(value), document.baseURI).href;
        } catch (_error) {
          return String(value);
        }
      }))];
    };
    document.querySelectorAll('link[imagesrcset], img, source, video, image').forEach(element => {
      if (!element.closest('section.slide')) {
        mediaAssets(element).forEach(value => globalStructureAssets.add(value));
      }
    });

    const slideMaterial = (slide, index) => {
      const mediaElements = [...slide.querySelectorAll('img, source, video, image')];
      const structure = slide.cloneNode(true);
      if (structure.hasAttribute('data-title')) structure.setAttribute('data-title', '#text');
      const walker = document.createTreeWalker(structure, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) walker.currentNode.nodeValue = '#text';
      structure.querySelectorAll('img, source, video, image').forEach(element => {
        element.replaceWith(document.createComment(`media:${element.tagName.toLowerCase()}`));
      });
      const text = [slide.dataset.title || ''];
      const textWalker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT);
      while (textWalker.nextNode()) text.push(textWalker.currentNode.nodeValue);
      return {
        html: slide.outerHTML,
        text,
        structure: structure.outerHTML,
        styles: slideStyles[index],
        media: mediaElements.map(element => element.outerHTML),
        assets: [
          ...mediaElements.flatMap(mediaAssets),
          ...[...(slide.hasAttribute('style') ? [slide] : []), ...slide.querySelectorAll('[style]')]
            .flatMap(element => cssDependencies(element.getAttribute('style') || '', document.baseURI)),
          ...slideAssets[index],
        ],
      };
    };
    head.querySelectorAll('style, link[rel~="stylesheet"]').forEach(node => node.remove());
    body.querySelectorAll('style, link[rel~="stylesheet"]').forEach(node => node.remove());
    const globalRuntime = [
      ...head.querySelectorAll('script'),
      ...body.querySelectorAll('script, button, input, select, textarea, [role="button"]'),
    ].map(node => node.outerHTML).join('\n');
    head.querySelectorAll('script').forEach(node => node.remove());
    body.querySelectorAll('script').forEach(node => node.remove());
    return {
      titles: slides.map(slide => slide.dataset.title || ''),
      criticalSlides: slides.map((slide, index) => (
        slide.dataset.visualCritical === 'true' ? index + 1 : null
      )).filter(Boolean),
      globalRuntime,
      globalStructure: `${head.outerHTML}\n${body.outerHTML}`,
      globalStyles: globalStyles.join('\n'),
      runtimeDependencies: [...runtimeDependencies],
      globalStructureAssets: [...globalStructureAssets],
      globalStyleAssets: [...globalStyleAssets],
      sourceFiles: [...sourceFiles],
      slides: slides.map(slideMaterial),
    };
  });
  const assetCache = new Map();
  const runtimeDependencyHashes = materials.runtimeDependencies.map(url => hashLocalAsset(url, assetCache)).sort();
  const globalStructureAssetHashes = materials.globalStructureAssets
    .map(url => hashLocalAsset(url, assetCache)).sort();
  const globalStyleAssetHashes = materials.globalStyleAssets.map(url => hashLocalAsset(url, assetCache)).sort();
  materials.sourceFiles.forEach(url => hashLocalAsset(url, assetCache));
  const globalComponents = {
    runtime_sha256: sha256(`${materials.globalRuntime}\n${runtimeDependencyHashes.join('\n')}`),
    structure_sha256: sha256(`${materials.globalStructure}\n${globalStructureAssetHashes.join('\n')}`),
    styles_sha256: sha256(`${materials.globalStyles}\n${globalStyleAssetHashes.join('\n')}`),
  };
  const components = {};
  const slides = {};
  materials.slides.forEach((slide, index) => {
    const assetHashes = slide.assets.map(url => hashLocalAsset(url, assetCache)).sort();
    const number = String(index + 1);
    components[number] = {
      text_sha256: sha256(slide.text.join('\n')),
      media_sha256: sha256(`${slide.media.join('\n')}\n${assetHashes.join('\n')}`),
      structure_sha256: sha256(slide.structure),
      styles_sha256: sha256(slide.styles.join('\n')),
      transition_sha256: sha256(
        slide.styles.filter(material => /(?:^|[;{\s-])(?:transition|animation)(?:[\s:-]|$)/i.test(material)).join('\n')
      ),
    };
    slides[number] = sha256(
      `${slide.html}\n${slide.styles.join('\n')}\n${assetHashes.join('\n')}`
    );
  });
  return {
    titles: materials.titles,
    critical_slides: materials.criticalSlides,
    global_sha256: sha256(
      `${globalComponents.runtime_sha256}\n${globalComponents.structure_sha256}\n${globalComponents.styles_sha256}`
    ),
    global_components: globalComponents,
    dependencies: [
      ...runtimeDependencyHashes, ...globalStructureAssetHashes, ...globalStyleAssetHashes,
    ].sort(),
    global_assets: [...new Set([
      ...materials.runtimeDependencies, ...materials.globalStructureAssets, ...materials.globalStyleAssets,
    ])],
    slide_assets: Object.fromEntries(materials.slides.map((slide, index) => [String(index + 1), slide.assets])),
    local_files: [...assetCache.values()].map(({ fingerprint: _fingerprint, ...entry }) => entry),
    components,
    slides,
  };
}

async function fingerprintsForDeck(deck) {
  const playwright = loadPlaywright();
  const browser = await playwright.chromium.launch(CHROMIUM_LAUNCH_OPTIONS);
  try {
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    await blockFingerprintVisuals(context);
    const page = await context.newPage();
    await prepareFingerprintPage(page, `${pathToFileURL(deck).href}#1`);
    const fingerprints = await collectFingerprints(page);
    await context.close();
    return fingerprints;
  } finally {
    await browser.close();
  }
}

function emptyRecord(number, title, sourceHash, changeType) {
  return {
    slide: number,
    title,
    source_sha256: sourceHash,
    review_scope: changeType,
    reviewer: '',
    reviewer_ref: '',
    visual_critical: false,
    review_batch_id: '',
    review_method: 'vision-batched-full-size',
    captures: {},
    debug_captures: {},
    required_ai_profiles: [],
    inspected_profiles: [],
    observation: '',
    identity_required: false,
    identity_detection: 'none',
    identity_targets: [],
    identity_review: [],
    checks: Object.fromEntries(checksFor(changeType, false).map(name => [name, 'pending'])),
    status: 'pending',
    notes: [],
  };
}

function refreshedRecord(number, title, sourceHash, changeType, previous = null) {
  const record = emptyRecord(number, title, sourceHash, changeType);
  if (previous && !['all', 'image'].includes(changeType)) {
    record.identity_required = previous.identity_required === true;
    record.identity_detection = previous.identity_detection || 'none';
    record.identity_targets = JSON.parse(JSON.stringify(previous.identity_targets || []));
  }
  return record;
}

function allowedImageUrls(fingerprints, renderTargets) {
  const allowed = new Set(fingerprints.global_assets || []);
  for (const number of renderTargets) {
    for (const url of fingerprints.slide_assets?.[String(number)] || []) allowed.add(url);
  }
  return allowed;
}

async function restrictImagesTo(context, allowed) {
  await context.route('**/*', async route => {
    const request = route.request();
    if (['image', 'media'].includes(request.resourceType()) && !allowed.has(request.url())) {
      await route.abort();
      return;
    }
    await route.continue();
  });
}

async function blockFingerprintVisuals(context) {
  await context.route('**/*', async route => {
    if (['image', 'media', 'font'].includes(route.request().resourceType())) {
      await route.abort();
    } else {
      await route.continue();
    }
  });
}

function loadExistingManifest(output) {
  const manifestPath = path.join(output, 'review.json');
  if (!fs.existsSync(manifestPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    throw new Error(`existing review manifest is invalid: ${error.message}`);
  }
}

function localFingerprintFilesUnchanged(entries) {
  if (!Array.isArray(entries)) return false;
  return entries.every(entry => {
    if (!entry || !entry.path || !entry.size || !entry.mtime_ns || !entry.ctime_ns) return false;
    try {
      const stat = fs.statSync(entry.path, { bigint: true });
      return stat.isFile()
        && String(stat.size) === entry.size
        && String(stat.mtimeNs) === entry.mtime_ns
        && String(stat.ctimeNs) === entry.ctime_ns;
    } catch (_error) {
      return false;
    }
  });
}

function loadFingerprintCache(cachePath, deck, deckHash) {
  if (!cachePath || !fs.existsSync(cachePath)) return null;
  try {
    const cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
    if (
      cache.schema_version !== 1
      || cache.deck !== deck
      || cache.deck_sha256 !== deckHash
      || !cache.fingerprints
      || !localFingerprintFilesUnchanged(cache.fingerprints.local_files)
    ) return null;
    return cache.fingerprints;
  } catch (_error) {
    return null;
  }
}

function writeFingerprintCache(cachePath, deck, fingerprints) {
  if (!cachePath) return;
  fs.mkdirSync(path.dirname(cachePath), { recursive: true });
  fs.writeFileSync(cachePath, `${JSON.stringify({
    schema_version: 1,
    deck,
    deck_sha256: sha256(fs.readFileSync(deck)),
    fingerprints,
  })}\n`);
}

function changedSlideNumbers(existingFingerprints, currentFingerprints) {
  const changed = new Set();
  for (let number = 1; number <= currentFingerprints.titles.length; number += 1) {
    if (existingFingerprints?.slides?.[String(number)] !== currentFingerprints.slides[String(number)]) {
      changed.add(number);
    }
  }
  return changed;
}

function reorderedTitles(before, after) {
  if (!Array.isArray(before) || !Array.isArray(after) || before.length !== after.length) return false;
  if (JSON.stringify(before) === JSON.stringify(after)) return false;
  return JSON.stringify([...before].sort()) === JSON.stringify([...after].sort());
}

function applyOrderImpact(details, orderChanged) {
  if (!orderChanged || details.impact === 'full') return details;
  return {
    detected: 'all',
    impact: 'neighbors',
    navigationChanged: details.navigationChanged,
    contentChanges: [...new Set([...details.contentChanges, 'structure'])],
  };
}

function detectedChangeDetails(existingFingerprints, currentFingerprints, changed, globalChanged) {
  if (globalChanged) {
    const before = existingFingerprints?.global_components;
    const after = currentFingerprints?.global_components;
    const navigationChanged = !before || !after || before.runtime_sha256 !== after.runtime_sha256;
    const contentChanges = [];
    if (!before || !after || before.styles_sha256 !== after.styles_sha256) contentChanges.push('style');
    if (!before || !after || before.structure_sha256 !== after.structure_sha256) contentChanges.push('structure');
    if (navigationChanged) contentChanges.push('runtime');
    if (changed.size) {
      const slideDetails = detectedChangeDetails(existingFingerprints, currentFingerprints, changed, false);
      contentChanges.push(...slideDetails.contentChanges);
    }
    return {
      detected: 'all',
      impact: 'full',
      navigationChanged,
      contentChanges: [...new Set(contentChanges)],
    };
  }
  if (!changed.size) {
    return { detected: 'none', impact: 'direct', navigationChanged: false, contentChanges: [] };
  }
  const previous = existingFingerprints?.components;
  const current = currentFingerprints.components;
  if (!previous || !current) {
    return {
      detected: 'all',
      impact: 'full',
      navigationChanged: true,
      contentChanges: ['text', 'image', 'structure', 'style', 'runtime'],
    };
  }
  const categories = new Set();
  let structureChanged = false;
  let stylesChanged = false;
  let transitionChanged = false;
  for (const number of changed) {
    const before = previous[String(number)];
    const after = current[String(number)];
    if (!before || !after) {
      return {
        detected: 'all',
        impact: 'full',
        navigationChanged: true,
        contentChanges: ['text', 'image', 'structure', 'style', 'runtime'],
      };
    }
    structureChanged ||= before.structure_sha256 !== after.structure_sha256;
    stylesChanged ||= before.styles_sha256 !== after.styles_sha256;
    transitionChanged ||= before.transition_sha256 !== after.transition_sha256;
    const textChanged = before.text_sha256 !== after.text_sha256;
    const imageChanged = before.media_sha256 !== after.media_sha256;
    if (textChanged) categories.add('text');
    if (imageChanged) categories.add('image');
    if (!textChanged && !imageChanged && !structureChanged && !stylesChanged
      && existingFingerprints.slides?.[String(number)] !== currentFingerprints.slides[String(number)]) {
      return {
        detected: 'all', impact: 'neighbors', navigationChanged: false, contentChanges: ['structure'],
      };
    }
  }
  const contentChanges = [...categories];
  if (structureChanged) contentChanges.push('structure');
  if (stylesChanged) contentChanges.push('style');
  if (structureChanged) {
    return { detected: 'all', impact: 'neighbors', navigationChanged: false, contentChanges };
  }
  if (transitionChanged) {
    return { detected: 'all', impact: 'neighbors', navigationChanged: false, contentChanges };
  }
  if (stylesChanged || categories.size > 1) {
    return { detected: 'all', impact: 'direct', navigationChanged: false, contentChanges };
  }
  if (categories.size === 1) {
    return {
      detected: [...categories][0], impact: 'direct', navigationChanged: false, contentChanges,
    };
  }
  return { detected: 'none', impact: 'direct', navigationChanged: false, contentChanges: [] };
}

function effectiveChangeType(requested, detected) {
  return detected === 'none' ? requested : detected;
}

function standardCrossReviewSlides(records, automationWarnings) {
  const required = new Set(records.filter(record => (
    record.visual_critical || record.identity_required
  )).map(record => record.slide));
  for (const warning of automationWarnings || []) {
    if (Number.isInteger(warning.slide)) required.add(warning.slide);
  }
  return required;
}

function requiredCrossReviewSlides(records, automationWarnings, reviewRisk) {
  return standardCrossReviewSlides(records, automationWarnings);
}

function emptyCrossReview(record, batchId) {
  return {
    slide: record.slide,
    reviewer: '',
    reviewer_ref: '',
    review_batch_id: batchId,
    review_method: 'vision-batched-full-size',
    inspected_profiles: [],
    observation: '',
    capture_sha256: Object.fromEntries(record.required_ai_profiles.map(profile => [
      profile,
      record.captures[profile]?.sha256 || '',
    ])),
    checks: Object.fromEntries(checksFor(record.review_scope, record.identity_required).map(name => [name, 'pending'])),
    identity_review: record.identity_required && ['all', 'image'].includes(record.review_scope)
      ? record.identity_targets.map(target => ({
        target_id: target.target_id,
        subject_name: target.subject_name,
        verdict: 'pending',
        observation: '',
      }))
      : [],
    status: 'pending',
  };
}

function reusableCrossReview(review, record, primaryRefs) {
  if (!review || review.status !== 'pass' || primaryRefs.has(review.reviewer_ref)) return false;
  const profiles = record.required_ai_profiles || [];
  const hashes = Object.fromEntries(profiles.map(profile => [profile, record.captures[profile]?.sha256 || '']));
  const expectedChecks = checksFor(record.review_scope, record.identity_required);
  return review.review_method === 'vision-batched-full-size'
    && review.inspected_profiles?.length === profiles.length
    && review.inspected_profiles.every((profile, index) => profile === profiles[index])
    && JSON.stringify(review.capture_sha256) === JSON.stringify(hashes)
    && review.checks
    && Object.keys(review.checks).join('|') === expectedChecks.join('|')
    && expectedChecks.every(check => review.checks[check] === 'pass');
}

function prepareCrossReviews(records, automationWarnings, reviewRisk, retained = []) {
  const required = [...requiredCrossReviewSlides(records, automationWarnings, reviewRisk)]
    .sort((left, right) => left - right);
  const reviews = [];
  const batches = [];
  const primaryRefs = new Set(records.map(record => record.reviewer_ref).filter(Boolean));
  const retainedBySlide = new Map(retained.filter(review => Number.isInteger(review?.slide)).map(review => [review.slide, review]));
  const completed = required.filter(number => reusableCrossReview(retainedBySlide.get(number), records[number - 1], primaryRefs));
  const pending = required.filter(number => !completed.includes(number));
  for (const [status, numbers] of [['complete', completed], ['pending', pending]]) {
    for (let offset = 0; offset < numbers.length; offset += REVIEW_BATCH_SIZE) {
      const slides = numbers.slice(offset, offset + REVIEW_BATCH_SIZE);
      const id = `cross-batch-${String(batches.length + 1).padStart(2, '0')}`;
      batches.push({
        id,
        slides,
        capture_profiles: Object.fromEntries(slides.map(number => [
          String(number),
          records[number - 1].required_ai_profiles,
        ])),
        status,
      });
      slides.forEach(number => {
        if (status === 'complete') {
          reviews.push({ ...JSON.parse(JSON.stringify(retainedBySlide.get(number))), review_batch_id: id });
        } else {
          reviews.push(emptyCrossReview(records[number - 1], id));
        }
      });
    }
  }
  return { reviews, batches, reused: completed.length, pending: pending.length };
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  if (args.workspaceStorage === 'agent-home') {
    fs.mkdirSync(path.join(args.workspace, 'drafts'), { recursive: true });
    fs.mkdirSync(path.join(args.workspace, 'tmp'), { recursive: true });
  }
  const playwright = loadPlaywright();
  const scriptPath = path.resolve(__filename);
  const measureSources = Object.fromEntries(Object.entries(MEASURE_SCRIPTS).map(([field, file]) => [
    field, fs.readFileSync(path.join(__dirname, file), 'utf8'),
  ]));
  const pageRuntimeSource = measureRuntimeSource(measureSources);
  const deckBytes = fs.readFileSync(args.deck);
  const deckHash = sha256(deckBytes);
  const runId = crypto.randomUUID();
  const requestedChangeType = args.changeType;
  const existing = args.slides || args.finalizeOnly ? loadExistingManifest(args.output) : null;
  if ((args.slides || args.finalizeOnly) && !existing) {
    usage('--slides/--finalize-prepare requires an existing review.json from an earlier full render');
  }
  if (args.finalizeOnly) {
    args.mode = existing.mode;
    args.responsive = existing.responsive === true;
    args.reviewRisk = existing.review_risk || 'standard';
  }
  const profiles = profileNames(args.responsive);

  const browser = await playwright.chromium.launch(CHROMIUM_LAUNCH_OPTIONS);
  const browserVersion = browser.version();
  const fileUrl = pathToFileURL(args.deck).href;
  let fingerprints;
  let renderTargets;
  let directlyChanged;
  let detectedChange = 'all';
  let changeDetails = {
    detected: 'all',
    impact: 'full',
    navigationChanged: true,
    contentChanges: ['text', 'image', 'structure', 'style', 'runtime'],
  };
  let strategy = 'full';
  let records;
  let previousDeckHash = existing?.deck_sha256 || null;

  try {
    fingerprints = loadFingerprintCache(args.fingerprintCache, args.deck, deckHash);
    if (!fingerprints) {
      const inspectionContext = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
      await blockFingerprintVisuals(inspectionContext);
      const inspectionPage = await inspectionContext.newPage();
      await prepareFingerprintPage(inspectionPage, `${fileUrl}#1`);
      fingerprints = await collectFingerprints(inspectionPage);
      await inspectionContext.close();
    }
    if (args.fingerprintCache) fs.rmSync(args.fingerprintCache, { force: true });
    const slideCount = fingerprints.titles.length;
    if (!slideCount || fingerprints.titles.some(title => !title.trim())) {
      throw new Error('every slide needs a non-empty data-title');
    }
    if (args.slides && [...args.slides].some(number => number > slideCount)) {
      usage(`--slides references a slide above the deck count ${slideCount}`);
    }

    const allSlides = new Set(Array.from({ length: slideCount }, (_value, index) => index + 1));
    const existingProfiles = existing ? Object.keys(existing.viewports || {}) : [];
    const existingTitles = existing?.slides?.map(record => record.title) || [];
    const compatible = existing
      && existing.schema_version === CONTRACT.schema_version
      && existing.mode === args.mode
      && existing.review_risk === args.reviewRisk
      && JSON.stringify(existingProfiles) === JSON.stringify(profiles)
      && existingTitles.length === fingerprints.titles.length;
    const globalChanged = compatible
      && existing.source_fingerprints?.global_sha256 !== fingerprints.global_sha256;
    directlyChanged = compatible
      ? changedSlideNumbers(existing.source_fingerprints, fingerprints)
      : new Set(allSlides);
    if (compatible && !globalChanged) {
      const unresolved = new Set([
        ...(existing.slides || [])
          .filter(record => String(record?.status).toLowerCase() === 'fail')
          .map(record => record.slide),
        ...(existing.cross_reviews || [])
          .filter(review => String(review?.status).toLowerCase() === 'fail')
          .map(review => review.slide),
      ].filter(Number.isInteger));
      const unchangedFailures = [...unresolved].filter(number => !directlyChanged.has(number));
      if (unchangedFailures.length) {
        throw new Error(
          `reviewer FAIL requires a source fix and new capture for slide(s) `
          + `${unchangedFailures.sort((left, right) => left - right).join(',')}`
        );
      }
    }
    changeDetails = compatible
      ? applyOrderImpact(
        detectedChangeDetails(existing.source_fingerprints, fingerprints, directlyChanged, globalChanged),
        reorderedTitles(existingTitles, fingerprints.titles)
      )
      : {
        detected: 'all',
        impact: 'full',
        navigationChanged: true,
        contentChanges: ['text', 'image', 'structure', 'style', 'runtime'],
      };
    detectedChange = changeDetails.detected;
    args.changeType = args.slides && compatible && !globalChanged
      ? effectiveChangeType(args.changeType, detectedChange)
      : 'all';
    if (args.changeType !== requestedChangeType) {
      process.stderr.write(
        `WARNING: requested change type ${requestedChangeType} resolved to ${args.changeType} `
        + `because the rendered source diff was ${detectedChange}\n`
      );
    }

    if (args.finalizeOnly) {
      if (!compatible || globalChanged || directlyChanged.size || existing.deck_sha256 !== deckHash) {
        throw new Error('deck changed after review; render the changed slides before --finalize-prepare');
      }
      if (existing.mode !== 'full') {
        throw new Error('Quick Draft finishes after verify; final scoring and cross-review are Full Validation only');
      }
      if (existing.phase === 'final') {
        throw new Error(
          'final review is already prepared; refusing to reset quality or cross-review evidence. '
          + 'Complete it and run finalize-verify, or rerun prepare after editing the deck.'
        );
      }
      existing.phase = 'final';
      existing.quality_score = {
        status: 'pending',
        reviewer: '',
        reviewer_ref: '',
        dimensions: Object.fromEntries(QUALITY_DIMENSIONS.map(name => [name, 0])),
        total: 0,
        weakest_slides: [],
        notes: '',
      };
      const finalReview = prepareCrossReviews(
        existing.slides,
        existing.automation_gate?.warnings || [],
        existing.review_risk || 'standard',
        existing.retained_cross_reviews || []
      );
      existing.cross_reviews = finalReview.reviews;
      existing.cross_review_batches = finalReview.batches;
      existing.retained_cross_reviews = [];
      existing.squint_review = await createSquintContactSheet(browser, existing, args.output, args.workspace);
      fs.writeFileSync(path.join(args.output, 'review.json'), `${JSON.stringify(existing, null, 2)}\n`);
      process.stdout.write(
        `OK: prepared final review without re-rendering; inspect the squint contact sheet, complete quality_score and `
        + `${finalReview.pending} pending cross-review slide(s) in ${finalReview.batches.length} batch(es); `
        + `${finalReview.reused} unchanged cross-review slide(s) reused, then run finalize-verify\n`
        + `${path.join(args.output, 'review.json')}\n`
      );
      return;
    }

    if (args.slides && compatible && changeDetails.impact !== 'full') {
      strategy = 'incremental';
      const selected = new Set([...args.slides, ...directlyChanged]);
      renderTargets = changeDetails.impact === 'neighbors'
        ? expandWithNeighbors(selected, slideCount)
        : selected;
      records = existing.slides.map(record => JSON.parse(JSON.stringify(record)));
      fs.mkdirSync(args.output, { recursive: true });
    } else {
      renderTargets = allSlides;
      directlyChanged = compatible ? directlyChanged : allSlides;
      records = fingerprints.titles.map((title, index) => refreshedRecord(
        index + 1, title, fingerprints.slides[String(index + 1)], 'all'
      ));
      fs.rmSync(args.output, { recursive: true, force: true });
      fs.mkdirSync(args.output, { recursive: true });
    }

    for (const number of renderTargets) {
      records[number - 1] = refreshedRecord(
        number,
        fingerprints.titles[number - 1],
        fingerprints.slides[String(number)],
        strategy === 'full' ? 'all' : args.changeType,
        existing?.slides?.[number - 1] || null
      );
    }
    for (let number = 1; number <= slideCount; number += 1) {
      records[number - 1].source_sha256 = fingerprints.slides[String(number)];
      records[number - 1].visual_critical = number === 1 || number === slideCount
        || fingerprints.critical_slides.includes(number);
    }

    const automationChecks = AUTOMATION_CHECKS_BY_CHANGE[strategy === 'full' ? 'all' : args.changeType];
    const measuredChecks = new Set(automationChecks);
    const firstProfile = PROFILES[profiles[0]];
    const context = await browser.newContext({
      viewport: { width: firstProfile.viewport[0], height: firstProfile.viewport[1] },
      deviceScaleFactor: 1,
    });
    if (strategy === 'incremental') {
      await restrictImagesTo(context, allowedImageUrls(fingerprints, renderTargets));
    }
    const page = await context.newPage();
    await preparePage(page, `${fileUrl}#1`);
    const cdp = await context.newCDPSession(page);
    await installPageRuntime(cdp, pageRuntimeSource);
    for (const profileName of profiles) {
      const profile = PROFILES[profileName];
      await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });
      await page.setViewportSize({ width: profile.viewport[0], height: profile.viewport[1] });
      await waitForFrames(page);
      if (profile.scaleMode === 'browser-page') {
        await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: profile.zoom });
        await waitForFrames(page);
      }
      await waitForMedia(page);
      const viewportEvidence = await page.evaluate(() => ({
        layout: [window.innerWidth, window.innerHeight],
        visual: [window.visualViewport?.width || 0, window.visualViewport?.height || 0],
        scale: window.visualViewport?.scale || 1,
        devicePixelRatio: window.devicePixelRatio,
      }));
      const roundedVisual = viewportEvidence.visual.map(value => Math.round(value));
      if (
        roundedVisual[0] !== profile.visualViewport[0]
        || roundedVisual[1] !== profile.visualViewport[1]
        || Math.abs(viewportEvidence.scale - profile.zoom) > 0.01
      ) {
        throw new Error(
          `${profileName} browser zoom mismatch: visualViewport `
          + `${roundedVisual.join('x')} scale ${viewportEvidence.scale}`
        );
      }
      const profileDir = path.join(args.output, profileName);
      fs.mkdirSync(profileDir, { recursive: true });
      for (const slideNumber of [...renderTargets].sort((left, right) => left - right)) {
        await page.evaluate(number => { window.location.hash = `#${number}`; }, slideNumber);
        await waitForFrames(page);
        const active = await page.evaluate(() => {
          const slides = [...document.querySelectorAll('section.slide')];
          const element = document.querySelector('section.slide.active');
          return element ? { slide: slides.indexOf(element) + 1, title: element.dataset.title || '' } : null;
        });
        if (!active || active.slide !== slideNumber || active.title !== fingerprints.titles[slideNumber - 1]) {
          throw new Error(`active slide mismatch for ${profileName} slide ${slideNumber}`);
        }
        const measurements = {};
        for (const check of ['text_bounds', 'contrast', 'container_density', 'controls', 'image_geometry']) {
          if (!measuredChecks.has(check)) continue;
          const field = MEASURE_FIELD_BY_CHECK[check];
          measurements[field] = await runMeasurement(page, field);
        }
        if (measuredChecks.has('font_integrity') && profileName === profiles[0]) {
          measurements.font_integrity = await measureFontIntegrity(page, cdp);
        }
        const filename = `slide-${String(slideNumber).padStart(2, '0')}.png`;
        const capturePath = path.join(profileDir, filename);
        await page.screenshot({ path: capturePath, fullPage: false });
        const captureBytes = fs.readFileSync(capturePath);
        // Any measured issue or warning earns a boundary overlay capture: the reviewer must never
        // have to guess which card owns an image or where the reserved nav zone is.
        const counts = measurementCounts(measurements);
        let debugOverlay = null;
        if (counts.issues || counts.warnings) {
          const debugFilename = `slide-${String(slideNumber).padStart(2, '0')}-debug.png`;
          const debugPath = path.join(profileDir, debugFilename);
          const caption = `slide ${slideNumber} · ${profileName} · `
            + `${counts.issues} issue(s), ${counts.warnings} warning(s)`;
          try {
            const summary = await captureDebugOverlay(page, {
              entries: overlayEntriesFrom(measurements),
              caption,
              path: debugPath,
            });
            debugOverlay = {
              path: `${profileName}/${debugFilename}`,
              sha256: sha256(fs.readFileSync(debugPath)),
              caption,
              measured_issues: counts.issues,
              measured_warnings: counts.warnings,
              drawn_regions: summary.entries,
              region_counts: summary.counts,
            };
            records[slideNumber - 1].debug_captures[profileName] = debugOverlay.path;
          } catch (error) {
            debugOverlay = { path: '', error: `debug overlay capture failed: ${error.message}` };
            records[slideNumber - 1].notes.push(debugOverlay.error);
          }
        }
        records[slideNumber - 1].captures[profileName] = {
          path: `${profileName}/${filename}`,
          sha256: sha256(captureBytes),
          active_slide: active.slide,
          active_title: active.title,
          viewport: `${profile.viewport[0]}x${profile.viewport[1]}`,
          visual_viewport: `${roundedVisual[0]}x${roundedVisual[1]}`,
          screenshot: `${profile.screenshot[0]}x${profile.screenshot[1]}`,
          zoom: profile.zoom,
          scale_mode: profile.scaleMode,
          device_pixel_ratio: viewportEvidence.devicePixelRatio,
          source_sha256: fingerprints.slides[String(slideNumber)],
          render_run_id: runId,
          motion_disabled: true,
          ...(debugOverlay ? { debug_overlay: debugOverlay } : {}),
          ...measurements,
        };
      }
    }
    await context.close();
  } finally {
    await browser.close();
  }

  const renderedSlides = [...renderTargets].sort((left, right) => left - right);
  const renderedSet = new Set(renderedSlides);
  const retainedCrossReviewBySlide = new Map();
  for (const review of [
    ...(existing?.retained_cross_reviews || []),
    ...(existing?.cross_reviews || []),
  ]) {
    if (review?.status === 'pass' && Number.isInteger(review.slide) && !renderedSet.has(review.slide)) {
      retainedCrossReviewBySlide.set(review.slide, JSON.parse(JSON.stringify(review)));
    }
  }
  const automationChecks = AUTOMATION_CHECKS_BY_CHANGE[strategy === 'full' ? 'all' : args.changeType];
  if (automationChecks.includes('image_geometry')) {
    for (const number of renderedSlides) {
      bindIdentityEvidence(records[number - 1], path.dirname(args.deck), profiles);
    }
  }
  const automationFailures = [];
  const automationWarnings = strategy === 'incremental'
    ? (existing?.automation_gate?.warnings || []).filter(warning => !renderedSet.has(warning?.slide))
    : [];
  const geometryField = MEASURE_FIELD_BY_CHECK;
  for (const number of renderedSlides) {
    const record = records[number - 1];
    for (const profile of profiles) {
      const capture = record.captures[profile];
      for (const check of automationChecks) {
        const result = capture[geometryField[check]];
        for (const issue of result?.issues || []) {
          automationFailures.push({ slide: number, profile, check, issue });
        }
        for (const warning of result?.warnings || []) {
          automationWarnings.push({ slide: number, profile, check, warning });
        }
      }
    }
  }

  for (const number of renderedSlides) {
    const record = records[number - 1];
    const slideWarnings = automationWarnings.filter(warning => warning.slide === number);
    // Every rendered slide is reviewed at full size. There is no automated-geometry-only escape
    // hatch: a rendered slide that carries no recorded review is exactly how a defective deck
    // shipped with 5 of 7 slides unreviewed.
    const required = new Set(['normal']);
    if (record.visual_critical) profiles.forEach(profile => required.add(profile));
    if (record.identity_required && ['all', 'image'].includes(record.review_scope)) required.add('normal');
    if (slideWarnings.length) {
      slideWarnings.forEach(warning => required.add(warning.profile));
    }
    record.required_ai_profiles = profiles.filter(profile => required.has(profile));
  }

  const reviewBatches = [];
  const aiReviewSlides = records
    .filter(record => record.required_ai_profiles.length && (
      renderedSet.has(record.slide) || String(record.status).toLowerCase() === 'pending'
    ))
    .map(record => record.slide);
  if (!automationFailures.length) {
    for (let offset = 0; offset < aiReviewSlides.length; offset += REVIEW_BATCH_SIZE) {
      const slides = aiReviewSlides.slice(offset, offset + REVIEW_BATCH_SIZE);
      const id = `batch-${String(reviewBatches.length + 1).padStart(2, '0')}`;
      const captureProfiles = {};
      for (const number of slides) {
        records[number - 1].review_batch_id = id;
        captureProfiles[String(number)] = records[number - 1].required_ai_profiles;
      }
      reviewBatches.push({ id, slides, capture_profiles: captureProfiles, status: 'pending' });
    }
  }
  const manifest = {
    schema_version: CONTRACT.schema_version,
    review_workspace: {
      storage: args.workspaceStorage,
      workspace: args.workspace,
      review_dir: args.output,
      retention: 'latest-per-deck',
    },
    mode: args.mode,
    review_risk: args.reviewRisk,
    phase: args.phase,
    responsive: args.responsive,
    change_type: strategy === 'full' ? 'all' : args.changeType,
    deck_sha256: deckHash,
    previous_deck_sha256: previousDeckHash,
    render_run: {
      id: runId,
      generator: 'render_slides.js',
      generator_sha256: sha256(fs.readFileSync(scriptPath)),
      contract_sha256: sha256(fs.readFileSync(CONTRACT_PATH)),
      browser: `chromium ${browserVersion}`,
      captured_at: new Date().toISOString(),
      strategy,
      requested_slides: args.slides ? [...args.slides].sort((left, right) => left - right) : renderedSlides,
      rendered_slides: renderedSlides,
      directly_changed_slides: [...directlyChanged].sort((left, right) => left - right),
      reused_slides: records.map(record => record.slide).filter(number => !renderedSet.has(number)),
      animations_disabled: true,
      requested_change_type: requestedChangeType,
      detected_change_type: strategy === 'full' ? 'all' : detectedChange,
      impact_scope: strategy === 'full' ? 'full' : changeDetails.impact,
      navigation_changed: changeDetails.navigationChanged,
      content_changes: changeDetails.contentChanges,
      review_slides: automationFailures.length ? [] : aiReviewSlides,
    },
    source_fingerprints: {
      global_sha256: fingerprints.global_sha256,
      previous_global_sha256: existing?.source_fingerprints?.global_sha256 || null,
      dependencies: fingerprints.dependencies,
      global_components: fingerprints.global_components,
      global_assets: fingerprints.global_assets,
      slide_assets: fingerprints.slide_assets,
      local_files: fingerprints.local_files,
      components: fingerprints.components,
      slides: fingerprints.slides,
    },
    viewports: Object.fromEntries(profiles.map(name => [name, {
      viewport: `${PROFILES[name].viewport[0]}x${PROFILES[name].viewport[1]}`,
      visual_viewport: `${PROFILES[name].visualViewport[0]}x${PROFILES[name].visualViewport[1]}`,
      screenshot: `${PROFILES[name].screenshot[0]}x${PROFILES[name].screenshot[1]}`,
      zoom: PROFILES[name].zoom,
      scale_mode: PROFILES[name].scaleMode,
      device_pixel_ratio: 1,
    }])),
    automation_gate: {
      status: automationFailures.length ? 'fail' : 'pass',
      checks: automationChecks,
      failures: automationFailures,
      warnings: automationWarnings,
    },
    review_batches: reviewBatches,
    quality_score: {
      status: 'pending',
      reviewer: '',
      reviewer_ref: '',
      dimensions: Object.fromEntries(QUALITY_DIMENSIONS.map(name => [name, 0])),
      total: 0,
      weakest_slides: [],
      notes: '',
    },
    cross_reviews: [],
    cross_review_batches: [],
    retained_cross_reviews: [...retainedCrossReviewBySlide.values()].sort((left, right) => left.slide - right.slide),
    squint_review: null,
    slides: records,
  };
  const manifestPath = path.join(args.output, 'review.json');
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  if (automationFailures.length) {
    process.stderr.write(
      `ERROR: automated geometry gate blocked AI review with ${automationFailures.length} failure(s); `
      + `fix the rendered defects and rerun before opening captures\n${manifestPath}\n`
    );
    process.exitCode = 1;
    return;
  }
  process.stdout.write(
    `OK: rendered ${renderedSlides.length}/${records.length} slides across ${profiles.length} profiles `
    + `(${strategy}, ${reviewBatches.length} AI review batch(es), motion disabled only in validation)\n${manifestPath}\n`
  );
}

async function checkTools() {
  const playwright = loadPlaywright();
  const browser = await playwright.chromium.launch(CHROMIUM_LAUNCH_OPTIONS);
  try {
    const page = await browser.newPage({ viewport: { width: 320, height: 180 } });
    await page.setContent('<!doctype html><html><body style="margin:0;background:#111;color:#fff"><h1>render check</h1></body></html>');
    const screenshot = await page.screenshot();
    if (!screenshot?.length) throw new Error('Chromium returned an empty screenshot');
    process.stdout.write(`OK: Node, Playwright, Chromium ${browser.version()}, and screenshot capture are available\n`);
  } finally {
    await browser.close();
  }
}

async function fingerprintCommand(deckArgument) {
  if (!deckArgument) usage('--fingerprints requires a deck path');
  const deck = path.resolve(deckArgument);
  if (!fs.existsSync(deck) || !fs.statSync(deck).isFile()) usage(`deck not found: ${deck}`);
  process.stdout.write(`${JSON.stringify(await fingerprintsForDeck(deck))}\n`);
}

async function classifyChangeCommand(
  deckArgument,
  reviewArgument,
  requested = 'all',
  mode,
  reviewRisk,
  responsiveValue,
  cacheArgument
) {
  const deck = requireDeck('--classify-change', deckArgument);
  if (!reviewArgument) usage('--classify-change requires a review directory');
  if (!CHECKS_BY_CHANGE[requested]) usage(`invalid change type: ${requested}`);
  if (!['quick', 'full'].includes(mode)) usage('--classify-change requires mode quick|full');
  if (!['standard', 'high'].includes(reviewRisk)) usage('--classify-change requires review risk standard|high');
  if (!['true', 'false'].includes(responsiveValue)) usage('--classify-change requires responsive true|false');
  const responsive = responsiveValue === 'true';
  const output = path.resolve(reviewArgument);
  const existing = loadExistingManifest(output);
  const compatible = existing
    && existing.schema_version === CONTRACT.schema_version
    && existing.mode === mode
    && existing.review_risk === reviewRisk
    && existing.responsive === responsive
    && JSON.stringify(Object.keys(existing.viewports || {})) === JSON.stringify(profileNames(responsive));
  if (!compatible) {
    process.stdout.write(`${JSON.stringify({
      requested, detected: 'all', effective: 'all', impact: 'full',
      navigation_changed: true,
      content_changes: ['text', 'image', 'structure', 'style', 'runtime'],
      changed_slides: [],
    })}\n`);
    return;
  }
  const current = await fingerprintsForDeck(deck);
  writeFingerprintCache(cacheArgument ? path.resolve(cacheArgument) : null, deck, current);
  const titles = existing.slides?.map(record => record.title) || [];
  if (titles.length !== current.titles.length) {
    process.stdout.write(`${JSON.stringify({
      requested, detected: 'all', effective: 'all', impact: 'full',
      navigation_changed: true,
      content_changes: ['text', 'image', 'structure', 'style', 'runtime'],
      changed_slides: [],
    })}\n`);
    return;
  }
  const globalChanged = existing.source_fingerprints?.global_sha256 !== current.global_sha256;
  const changed = changedSlideNumbers(existing.source_fingerprints, current);
  const details = applyOrderImpact(
    detectedChangeDetails(existing.source_fingerprints, current, changed, globalChanged),
    reorderedTitles(titles, current.titles)
  );
  if (!IMPACT_SCOPES.has(details.impact)
    || details.contentChanges.some(value => !CONTENT_CHANGE_CATEGORIES.has(value))) {
    throw new Error('internal change classifier produced an unsupported impact category');
  }
  process.stdout.write(`${JSON.stringify({
    requested,
    detected: details.detected,
    effective: effectiveChangeType(requested, details.detected),
    impact: details.impact,
    navigation_changed: details.navigationChanged,
    content_changes: details.contentChanges,
    changed_slides: [...changed].sort((left, right) => left - right),
  })}\n`);
}

function requireDeck(commandName, deckArgument) {
  if (!deckArgument) usage(`${commandName} requires a deck path`);
  const deck = path.resolve(deckArgument);
  if (!fs.existsSync(deck) || !fs.statSync(deck).isFile()) usage(`deck not found: ${deck}`);
  return deck;
}

function cleanWorkspaceCommand(deckArgument) {
  const deck = requireDeck('--clean-workspace', deckArgument);
  const workspace = defaultWorkspaceDirectory(deck);
  fs.rmSync(workspace, { recursive: true, force: true });
  process.stdout.write(`OK: removed ${workspace}\n`);
}

const command = process.argv.slice(2);
let operation;
if (command.length === 1 && command[0] === '--check') {
  operation = checkTools();
} else if (command[0] === '--fingerprints') {
  operation = fingerprintCommand(command[1]);
} else if (command[0] === '--classify-change') {
  operation = classifyChangeCommand(
    command[1], command[2], command[3], command[4], command[5], command[6], command[7]
  );
} else if (command[0] === '--workspace-dir') {
  process.stdout.write(`${defaultWorkspaceDirectory(requireDeck('--workspace-dir', command[1]))}\n`);
  operation = Promise.resolve();
} else if (command[0] === '--review-dir') {
  process.stdout.write(`${defaultReviewDirectory(requireDeck('--review-dir', command[1]))}\n`);
  operation = Promise.resolve();
} else if (command[0] === '--clean-workspace') {
  cleanWorkspaceCommand(command[1]);
  operation = Promise.resolve();
} else {
  operation = main();
}
operation.catch(error => {
  process.stderr.write(`ERROR: ${error.stack || error.message}\n`);
  process.exit(1);
});
