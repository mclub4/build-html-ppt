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
const MEDIA_WAIT_TIMEOUT_MS = 15000;
const QUALITY_DIMENSIONS = [
  'story', 'art_direction', 'layout_rhythm', 'typography',
  'imagery', 'composition', 'evidence', 'presentation_utility',
];
const MOTION_OVERRIDE = `
  *, *::before, *::after {
    animation: none !important;
    caret-color: transparent !important;
    scroll-behavior: auto !important;
    transition: none !important;
  }
`;

function usage(message) {
  if (message) process.stderr.write(`ERROR: ${message}\n`);
  process.stderr.write(
    'usage: node render_slides.js DECK.html [REVIEW_DIR] --mode quick|full '
    + '[--review-risk standard|high] [--slides 3,5-7] '
    + '[--change-type all|text|image|navigation] [--responsive]\n'
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
  } else {
    const scriptParts = fs.realpathSync.native(__filename).split(path.sep);
    const runsFromClaude = scriptParts.includes('.claude');
    agentHome = runsFromClaude
      ? path.join(os.homedir(), '.claude')
      : (process.env.CODEX_HOME || path.join(os.homedir(), '.codex'));
  }
  return path.join(path.resolve(agentHome), 'build-html-slides', 'workspaces');
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

async function waitForFrames(page) {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function preparePage(page, url) {
  await page.goto(url, { waitUntil: 'load' });
  await page.addStyleTag({ content: MOTION_OVERRIDE, attributes: { 'data-slide-validation-motion': 'off' } });
  await waitForMedia(page);
}

function hashLocalAsset(url) {
  if (!url || !url.startsWith('file:')) return url || '';
  try {
    const filePath = fileURLToPath(url);
    return fs.statSync(filePath).isFile() ? `${url}:${sha256(fs.readFileSync(filePath))}` : url;
  } catch (_error) {
    return `${url}:missing`;
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
    const dependencies = new Set();

    const collectCssDependencies = (cssText, baseUrl) => {
      for (const match of cssText.matchAll(/url\(\s*(?:"([^"]+)"|'([^']+)'|([^)'"\s]+))\s*\)/gi)) {
        const value = match[1] || match[2] || match[3] || '';
        if (!value || value.startsWith('#') || value.startsWith('data:')) continue;
        try {
          dependencies.add(new URL(value, baseUrl || document.baseURI).href);
        } catch (_error) {
          dependencies.add(value);
        }
      }
    };

    const selectorTargets = selectorText => {
      if (/\.active\b|:target\b|\[aria-hidden(?:[\]=])/i.test(selectorText)) return null;
      const query = selectorText
        .replace(/::[a-z-]+(?:\([^)]*\))?/gi, '')
        .replace(/:(?:hover|active|focus|focus-visible|focus-within|visited|target)(?![\w-])/gi, '');
      try {
        const targets = slides.flatMap((slide, index) => (
          slide.matches(query) || slide.querySelector(query) ? [index] : []
        ));
        const outside = [...document.querySelectorAll(query)].some(element => !element.closest('section.slide'));
        return outside ? null : targets;
      } catch (_error) {
        return null;
      }
    };
    const classifyRules = (rules, context = '', baseUrl = document.baseURI) => {
      for (const rule of [...rules]) {
        if (rule.type === CSSRule.STYLE_RULE) {
          const material = `${context}${rule.cssText}`;
          collectCssDependencies(material, baseUrl);
          const targets = selectorTargets(rule.selectorText || '');
          if (targets?.length === 1) slideStyles[targets[0]].push(material);
          else if (targets === null || targets.length > 1) globalStyles.push(material);
          continue;
        }
        if (rule.cssRules && typeof rule.conditionText === 'string') {
          classifyRules(rule.cssRules, `${context}@${rule.constructor.name} ${rule.conditionText}{`, baseUrl);
          continue;
        }
        const material = `${context}${rule.cssText}`;
        collectCssDependencies(material, baseUrl);
        globalStyles.push(material);
      }
    };
    for (const sheet of [...document.styleSheets]) {
      const owner = sheet.ownerNode;
      if (owner?.hasAttribute?.('data-slide-validation-motion')) continue;
      if (sheet.href) dependencies.add(sheet.href);
      const explicit = (owner?.dataset?.slideScope || '').split(',')
        .map(value => Number.parseInt(value.trim(), 10))
        .filter(number => number >= 1 && number <= slides.length);
      if (explicit.length) {
        explicit.forEach(number => slideStyles[number - 1].push(owner?.textContent || ''));
        collectCssDependencies(owner?.textContent || '', sheet.href || document.baseURI);
        continue;
      }
      try {
        classifyRules(sheet.cssRules, '', sheet.href || document.baseURI);
      } catch (_error) {
        globalStyles.push(`unreadable-stylesheet:${sheet.href || owner?.outerHTML || ''}`);
      }
    }
    document.querySelectorAll('script[src], link[href]').forEach(element => {
      const value = element.src || element.href;
      if (value) dependencies.add(value);
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
        mediaAssets(element).forEach(value => dependencies.add(value));
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
        assets: mediaElements.flatMap(mediaAssets),
      };
    };
    return {
      titles: slides.map(slide => slide.dataset.title || ''),
      criticalSlides: slides.map((slide, index) => (
        slide.dataset.visualCritical === 'true' ? index + 1 : null
      )).filter(Boolean),
      global: `${head.innerHTML}\n${body.innerHTML}\n${globalStyles.join('\n')}`,
      dependencies: [...dependencies],
      slides: slides.map(slideMaterial),
    };
  });
  const dependencyHashes = materials.dependencies.map(hashLocalAsset).sort();
  const components = {};
  const slides = {};
  materials.slides.forEach((slide, index) => {
    const assetHashes = slide.assets.map(hashLocalAsset).sort();
    const number = String(index + 1);
    components[number] = {
      text_sha256: sha256(slide.text.join('\n')),
      media_sha256: sha256(`${slide.media.join('\n')}\n${assetHashes.join('\n')}`),
      structure_sha256: sha256(slide.structure),
      styles_sha256: sha256(slide.styles.join('\n')),
    };
    slides[number] = sha256(
      `${slide.html}\n${slide.styles.join('\n')}\n${assetHashes.join('\n')}`
    );
  });
  return {
    titles: materials.titles,
    critical_slides: materials.criticalSlides,
    global_sha256: sha256(`${materials.global}\n${dependencyHashes.join('\n')}`),
    dependencies: dependencyHashes,
    components,
    slides,
  };
}

async function fingerprintsForDeck(deck) {
  const playwright = loadPlaywright();
  const browser = await playwright.chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await preparePage(page, `${pathToFileURL(deck).href}#1`);
    return await collectFingerprints(page);
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

function loadExistingManifest(output) {
  const manifestPath = path.join(output, 'review.json');
  if (!fs.existsSync(manifestPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    throw new Error(`existing review manifest is invalid: ${error.message}`);
  }
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

function detectedChangeType(existingFingerprints, currentFingerprints, changed, globalChanged) {
  if (globalChanged) return 'all';
  if (!changed.size) return 'none';
  const previous = existingFingerprints?.components;
  const current = currentFingerprints.components;
  if (!previous || !current) return 'all';
  const categories = new Set();
  for (const number of changed) {
    const before = previous[String(number)];
    const after = current[String(number)];
    if (!before || !after) return 'all';
    if (
      before.structure_sha256 !== after.structure_sha256
      || before.styles_sha256 !== after.styles_sha256
    ) return 'all';
    const textChanged = before.text_sha256 !== after.text_sha256;
    const imageChanged = before.media_sha256 !== after.media_sha256;
    if (textChanged) categories.add('text');
    if (imageChanged) categories.add('image');
    if (!textChanged && !imageChanged && existingFingerprints.slides?.[String(number)] !== currentFingerprints.slides[String(number)]) {
      return 'all';
    }
  }
  if (categories.size !== 1) return categories.size ? 'all' : 'none';
  return [...categories][0];
}

function effectiveChangeType(requested, detected) {
  if (requested === 'all' || detected === 'none' || requested === detected) return requested;
  return 'all';
}

function standardCrossReviewSlides(records, automationWarnings) {
  const required = new Set(records.filter(record => record.visual_critical).map(record => record.slide));
  for (const warning of automationWarnings || []) {
    if (Number.isInteger(warning.slide)) required.add(warning.slide);
  }
  const ordinary = records.map(record => record.slide).filter(number => !required.has(number));
  if (!ordinary.length) return required;
  const policy = CONTRACT.standard_cross_review;
  const count = Math.min(
    policy.maximum_sample,
    Math.max(policy.minimum_sample, Math.ceil(ordinary.length * policy.sample_ratio))
  );
  for (let index = 1; index <= count; index += 1) {
    const position = Math.min(
      ordinary.length - 1,
      Math.max(0, Math.round((index * (ordinary.length + 1)) / (count + 1)) - 1)
    );
    required.add(ordinary[position]);
  }
  return required;
}

function requiredCrossReviewSlides(records, automationWarnings, reviewRisk) {
  return reviewRisk === 'high'
    ? new Set(records.map(record => record.slide))
    : standardCrossReviewSlides(records, automationWarnings);
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

function prepareCrossReviews(records, automationWarnings, reviewRisk) {
  const required = [...requiredCrossReviewSlides(records, automationWarnings, reviewRisk)]
    .sort((left, right) => left - right);
  const reviews = [];
  const batches = [];
  for (let offset = 0; offset < required.length; offset += REVIEW_BATCH_SIZE) {
    const slides = required.slice(offset, offset + REVIEW_BATCH_SIZE);
    const id = `cross-batch-${String(batches.length + 1).padStart(2, '0')}`;
    batches.push({
      id,
      slides,
      capture_profiles: Object.fromEntries(slides.map(number => [
        String(number),
        records[number - 1].required_ai_profiles,
      ])),
      status: 'pending',
    });
    slides.forEach(number => reviews.push(emptyCrossReview(records[number - 1], id)));
  }
  return { reviews, batches };
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  if (args.workspaceStorage === 'agent-home') {
    fs.mkdirSync(path.join(args.workspace, 'drafts'), { recursive: true });
    fs.mkdirSync(path.join(args.workspace, 'tmp'), { recursive: true });
  }
  const playwright = loadPlaywright();
  const scriptPath = path.resolve(__filename);
  const textBoundsScript = fs.readFileSync(path.join(__dirname, 'measure_text_bounds.js'), 'utf8');
  const controlGeometryScript = fs.readFileSync(path.join(__dirname, 'measure_geometry.js'), 'utf8');
  const imageGeometryScript = fs.readFileSync(path.join(__dirname, 'measure_image_geometry.js'), 'utf8');
  const containerDensityScript = fs.readFileSync(path.join(__dirname, 'measure_container_density.js'), 'utf8');
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

  const browser = await playwright.chromium.launch({ headless: true });
  const browserVersion = browser.version();
  const fileUrl = pathToFileURL(args.deck).href;
  let fingerprints;
  let renderTargets;
  let directlyChanged;
  let detectedChange = 'all';
  let strategy = 'full';
  let records;
  let previousDeckHash = existing?.deck_sha256 || null;

  try {
    const inspectionPage = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await preparePage(inspectionPage, `${fileUrl}#1`);
    fingerprints = await collectFingerprints(inspectionPage);
    await inspectionPage.close();
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
      && JSON.stringify(existingTitles) === JSON.stringify(fingerprints.titles);
    const globalChanged = compatible
      && existing.source_fingerprints?.global_sha256 !== fingerprints.global_sha256;
    directlyChanged = compatible
      ? changedSlideNumbers(existing.source_fingerprints, fingerprints)
      : new Set(allSlides);
    detectedChange = compatible
      ? detectedChangeType(existing.source_fingerprints, fingerprints, directlyChanged, globalChanged)
      : 'all';
    args.changeType = args.slides && compatible && !globalChanged
      ? effectiveChangeType(args.changeType, detectedChange)
      : 'all';
    if (args.changeType !== requestedChangeType) {
      process.stderr.write(
        `WARNING: requested change type ${requestedChangeType} widened to ${args.changeType} `
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
        existing.review_risk || 'standard'
      );
      existing.cross_reviews = finalReview.reviews;
      existing.cross_review_batches = finalReview.batches;
      fs.writeFileSync(path.join(args.output, 'review.json'), `${JSON.stringify(existing, null, 2)}\n`);
      process.stdout.write(
        `OK: prepared final review without re-rendering; complete quality_score and `
        + `${finalReview.batches.length} cross-review batch(es), then run finalize-verify\n`
        + `${path.join(args.output, 'review.json')}\n`
      );
      return;
    }

    if (args.slides && compatible && !globalChanged) {
      strategy = 'incremental';
      renderTargets = expandWithNeighbors(new Set([...args.slides, ...directlyChanged]), slideCount);
      records = existing.slides.map(record => JSON.parse(JSON.stringify(record)));
      fs.mkdirSync(args.output, { recursive: true });
    } else {
      renderTargets = allSlides;
      directlyChanged = compatible ? directlyChanged : allSlides;
      records = fingerprints.titles.map((title, index) => emptyRecord(
        index + 1, title, fingerprints.slides[String(index + 1)], 'all'
      ));
      fs.rmSync(args.output, { recursive: true, force: true });
      fs.mkdirSync(args.output, { recursive: true });
    }

    for (const number of renderTargets) {
      records[number - 1] = emptyRecord(
        number,
        fingerprints.titles[number - 1],
        fingerprints.slides[String(number)],
        strategy === 'full' ? 'all' : args.changeType
      );
    }
    for (let number = 1; number <= slideCount; number += 1) {
      records[number - 1].source_sha256 = fingerprints.slides[String(number)];
      records[number - 1].visual_critical = number === 1 || number === slideCount
        || fingerprints.critical_slides.includes(number);
    }

    for (const profileName of profiles) {
      const profile = PROFILES[profileName];
      const context = await browser.newContext({
        viewport: { width: profile.viewport[0], height: profile.viewport[1] },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();
      await preparePage(page, `${fileUrl}#1`);
      if (profile.scaleMode === 'browser-page') {
        const cdp = await context.newCDPSession(page);
        await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: profile.zoom });
        await waitForFrames(page);
      }
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
        const textGeometry = await page.evaluate(source => (0, eval)(source), textBoundsScript);
        const containerDensity = await page.evaluate(source => (0, eval)(source), containerDensityScript);
        const controlGeometry = await page.evaluate(source => (0, eval)(source), controlGeometryScript);
        const imageGeometry = await page.evaluate(source => (0, eval)(source), imageGeometryScript);
        await waitForFrames(page);
        const filename = `slide-${String(slideNumber).padStart(2, '0')}.png`;
        const capturePath = path.join(profileDir, filename);
        await page.screenshot({ path: capturePath, fullPage: false });
        const captureBytes = fs.readFileSync(capturePath);
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
          text_geometry: textGeometry,
          container_density: containerDensity,
          control_geometry: controlGeometry,
          image_geometry: imageGeometry,
        };
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }

  const renderedSlides = [...renderTargets].sort((left, right) => left - right);
  const renderedSet = new Set(renderedSlides);
  for (const number of renderedSlides) {
    bindIdentityEvidence(records[number - 1], path.dirname(args.deck), profiles);
  }
  const automationChecks = AUTOMATION_CHECKS_BY_CHANGE[strategy === 'full' ? 'all' : args.changeType];
  const automationFailures = [];
  const automationWarnings = [];
  const geometryField = {
    text_bounds: 'text_geometry',
    container_density: 'container_density',
    controls: 'control_geometry',
    image_geometry: 'image_geometry',
  };
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

  const responsiveVisionProfiles = args.responsive ? RESPONSIVE_PROFILES : [];
  for (const number of renderedSlides) {
    const record = records[number - 1];
    const slideWarnings = automationWarnings.filter(warning => warning.slide === number);
    const required = new Set();
    if (args.mode === 'full') {
      required.add('normal');
      responsiveVisionProfiles.forEach(profile => required.add(profile));
    }
    if (record.visual_critical) profiles.forEach(profile => required.add(profile));
    if (record.identity_required && ['all', 'image'].includes(record.review_scope)) required.add('normal');
    if (slideWarnings.length) {
      required.add('normal');
      slideWarnings.forEach(warning => required.add(warning.profile));
    }
    record.required_ai_profiles = profiles.filter(profile => required.has(profile));
    if (args.mode === 'quick' && !record.required_ai_profiles.length) {
      record.review_method = 'automated-geometry-only';
      record.checks = {};
      record.status = 'automation-pass';
    }
  }

  const reviewBatches = [];
  const aiReviewSlides = renderedSlides.filter(number => records[number - 1].required_ai_profiles.length);
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
    },
    source_fingerprints: {
      global_sha256: fingerprints.global_sha256,
      previous_global_sha256: existing?.source_fingerprints?.global_sha256 || null,
      dependencies: fingerprints.dependencies,
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
  const browser = await playwright.chromium.launch({ headless: true });
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
  responsiveValue
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
    process.stdout.write(`${JSON.stringify({ requested, detected: 'all', effective: 'all', changed_slides: [] })}\n`);
    return;
  }
  const current = await fingerprintsForDeck(deck);
  const titles = existing.slides?.map(record => record.title) || [];
  if (JSON.stringify(titles) !== JSON.stringify(current.titles)) {
    process.stdout.write(`${JSON.stringify({ requested, detected: 'all', effective: 'all', changed_slides: [] })}\n`);
    return;
  }
  const globalChanged = existing.source_fingerprints?.global_sha256 !== current.global_sha256;
  const changed = changedSlideNumbers(existing.source_fingerprints, current);
  const detected = detectedChangeType(existing.source_fingerprints, current, changed, globalChanged);
  process.stdout.write(`${JSON.stringify({
    requested,
    detected,
    effective: effectiveChangeType(requested, detected),
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
  operation = classifyChangeCommand(command[1], command[2], command[3], command[4], command[5], command[6]);
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
