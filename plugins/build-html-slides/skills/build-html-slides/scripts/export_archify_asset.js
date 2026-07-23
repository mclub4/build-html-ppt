#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { loadPlaywright } = require('./playwright_loader');

const ALIAS_KEYS = new Set([
  'background', 'surface', 'text', 'muted', 'line', 'accent', 'accent_2',
  'positive', 'warning', 'danger', 'external', 'font_family',
]);

function fail(message) {
  process.stderr.write(`ERROR: ${message}\n`);
  process.exit(1);
}

function usage(message = '') {
  if (message) process.stderr.write(`ERROR: ${message}\n`);
  process.stderr.write(
    'Usage: node export_archify_asset.js ARCHIFY.html OUTPUT.svg|OUTPUT.webp|OUTPUT_BASE '
    + '[--format svg|webp|both] [--width PX] [--height PX] [--theme light|dark] '
    + '[--tokens theme.json] [--deck-theme DECK.html] [--slide N] [--json]\n'
  );
  process.exit(2);
}

function parsePositiveInteger(value, label) {
  const number = Number(value);
  if (!Number.isInteger(number) || number < 1 || number > 16384) {
    usage(`${label} must be an integer from 1 to 16384`);
  }
  return number;
}

function parseArguments(argv) {
  const positional = [];
  const args = {
    format: null,
    width: 1600,
    height: null,
    theme: 'light',
    tokens: null,
    deckTheme: null,
    slide: 1,
    json: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith('--')) {
      positional.push(argument);
      continue;
    }
    const next = () => {
      if (!argv[index + 1]) usage(`${argument} requires a value`);
      return argv[++index];
    };
    if (argument === '--format') args.format = next();
    else if (argument === '--width') args.width = parsePositiveInteger(next(), '--width');
    else if (argument === '--height') args.height = parsePositiveInteger(next(), '--height');
    else if (argument === '--theme') args.theme = next();
    else if (argument === '--tokens') args.tokens = path.resolve(next());
    else if (argument === '--deck-theme') args.deckTheme = path.resolve(next());
    else if (argument === '--slide') args.slide = parsePositiveInteger(next(), '--slide');
    else if (argument === '--json') args.json = true;
    else usage(`unknown option: ${argument}`);
  }
  if (positional.length !== 2) usage();
  if (!['light', 'dark'].includes(args.theme)) usage('--theme must be light or dark');
  if (args.tokens && args.deckTheme) usage('use either --tokens or --deck-theme, not both');

  const input = path.resolve(positional[0]);
  const requestedOutput = path.resolve(positional[1]);
  const extension = path.extname(requestedOutput).toLowerCase();
  const inferred = extension === '.svg' ? 'svg' : (extension === '.webp' ? 'webp' : 'both');
  args.format = args.format || inferred;
  if (!['svg', 'webp', 'both'].includes(args.format)) usage('--format must be svg, webp, or both');

  const base = ['.svg', '.webp'].includes(extension)
    ? requestedOutput.slice(0, -extension.length)
    : requestedOutput;
  return {
    ...args,
    input,
    outputSvg: args.format === 'webp' ? null : (args.format === 'svg' && extension === '.svg' ? requestedOutput : `${base}.svg`),
    outputWebp: args.format === 'svg' ? null : (args.format === 'webp' && extension === '.webp' ? requestedOutput : `${base}.webp`),
  };
}

function readTokenFile(file) {
  if (!file) return {};
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) fail(`theme token file not found: ${file}`);
  let value;
  try {
    value = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    fail(`theme token file is not valid JSON: ${error.message}`);
  }
  if (!value || Array.isArray(value) || typeof value !== 'object') {
    fail('theme token file root must be an object');
  }
  const unknown = Object.keys(value).filter(key => key !== 'css_variables' && !ALIAS_KEYS.has(key));
  if (unknown.length) fail(`unknown theme token key(s): ${unknown.join(', ')}`);
  if (value.css_variables !== undefined && (
    !value.css_variables || Array.isArray(value.css_variables) || typeof value.css_variables !== 'object'
  )) {
    fail('css_variables must be an object');
  }
  return value;
}

function validateCssValue(value, label) {
  if (typeof value !== 'string' || !value.trim() || /[;{}<>]/.test(value)) {
    fail(`${label} must be one safe CSS value without semicolons or braces`);
  }
  return value.trim();
}

function expandThemeTokens(tokens) {
  const css = {};
  const put = (name, value) => {
    if (value !== undefined && value !== null && value !== '') css[name] = validateCssValue(value, name);
  };
  put('--bg', tokens.background);
  put('--mask', tokens.surface || tokens.background);
  put('--panel', tokens.surface);
  put('--lane-fill', tokens.surface);
  put('--text', tokens.text);
  put('--text-muted', tokens.muted);
  put('--text-dim', tokens.muted);
  put('--text-faint', tokens.muted);
  put('--arrow', tokens.muted);
  put('--grid', tokens.line);
  put('--panel-border', tokens.line);
  put('--lane-stroke', tokens.line);
  put('--arrow-emphasis', tokens.accent);
  put('--frontend-stroke', tokens.accent);
  put('--backend-stroke', tokens.positive || tokens.accent);
  put('--database-stroke', tokens.accent_2 || tokens.accent);
  put('--cloud-stroke', tokens.warning || tokens.accent_2 || tokens.accent);
  put('--security-stroke', tokens.danger || tokens.accent);
  put('--messagebus-stroke', tokens.warning || tokens.accent_2 || tokens.accent);
  put('--external-stroke', tokens.external || tokens.muted);

  const fill = (name, color) => {
    if (color) put(name, `color-mix(in srgb, ${validateCssValue(color, name)} 16%, ${validateCssValue(tokens.background || '#ffffff', 'background')})`);
  };
  fill('--frontend-fill', tokens.accent);
  fill('--backend-fill', tokens.positive || tokens.accent);
  fill('--database-fill', tokens.accent_2 || tokens.accent);
  fill('--cloud-fill', tokens.warning || tokens.accent_2 || tokens.accent);
  fill('--security-fill', tokens.danger || tokens.accent);
  fill('--messagebus-fill', tokens.warning || tokens.accent_2 || tokens.accent);
  fill('--external-fill', tokens.external || tokens.muted);

  for (const [name, value] of Object.entries(tokens.css_variables || {})) {
    if (!/^--[a-z0-9-]+$/i.test(name)) fail(`invalid CSS variable name: ${name}`);
    put(name, value);
  }
  return {
    cssVariables: css,
    fontFamily: tokens.font_family ? validateCssValue(tokens.font_family, 'font_family') : '',
  };
}

async function extractDeckTheme(browser, deck, slideNumber) {
  if (!fs.existsSync(deck) || !fs.statSync(deck).isFile()) fail(`deck theme source not found: ${deck}`);
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  try {
    await page.goto(`${pathToFileURL(deck).href}#${slideNumber}`, { waitUntil: 'load' });
    await page.evaluate(async () => {
      if (document.fonts?.ready) await document.fonts.ready;
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    return await page.evaluate(number => {
      const slides = [...document.querySelectorAll('section.slide')];
      const slide = slides[number - 1] || document.querySelector('section.slide.active');
      if (!slide) throw new Error(`deck has no slide ${number}`);
      const root = getComputedStyle(document.documentElement);
      const rendered = getComputedStyle(slide);
      const token = (name, fallback = '') => root.getPropertyValue(name).trim() || fallback;
      return {
        background: token('--slide-bg', rendered.backgroundColor),
        surface: token('--surface', token('--slide-bg', rendered.backgroundColor)),
        text: token('--ink', rendered.color),
        muted: token('--muted', rendered.color),
        line: token('--line', token('--muted', rendered.color)),
        accent: token('--accent', token('--ink', rendered.color)),
        accent_2: token('--accent-2', token('--accent', token('--ink', rendered.color))),
        positive: token('--positive', token('--accent', token('--ink', rendered.color))),
        warning: token('--warning', token('--accent-2', token('--accent', rendered.color))),
        danger: token('--danger', token('--accent', rendered.color)),
        external: token('--muted', rendered.color),
        font_family: token('--font-body', rendered.fontFamily),
      };
    }, slideNumber);
  } finally {
    await page.close();
  }
}

async function exportCanonicalSvg(page, args, theme) {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(pathToFileURL(args.input).href, { waitUntil: 'load' });
  await page.evaluate(async selectedTheme => {
    document.documentElement.setAttribute('data-theme', selectedTheme);
    if (document.fonts?.ready) await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }, args.theme);
  const exportButton = page.locator('#btn-export');
  const svgMenuItem = page.locator('#export-menu [data-format="svg"]');
  if (await exportButton.count() !== 1 || await svgMenuItem.count() !== 1) {
    fail('Archify HTML does not expose the expected SVG export controls');
  }
  await exportButton.click();
  const downloadPromise = page.waitForEvent('download');
  await svgMenuItem.click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  const canonicalSvg = Buffer.concat(chunks).toString('utf8');
  const exported = await page.evaluate(({ source, selectedTheme, cssVariables, fontFamily }) => {
    const documentSvg = new DOMParser().parseFromString(source, 'image/svg+xml');
    const svg = documentSvg.documentElement;
    if (!svg || svg.localName !== 'svg') throw new Error('Archify export did not produce one SVG root');
    svg.setAttribute('data-theme', selectedTheme);
    svg.setAttribute('data-slide-asset', 'true');
    svg.querySelectorAll('script, foreignObject, button, input, select, textarea').forEach(node => node.remove());
    svg.querySelectorAll('[tabindex], [aria-pressed], [role="button"]').forEach(node => {
      node.removeAttribute('tabindex');
      node.removeAttribute('aria-pressed');
      if (node.getAttribute('role') === 'button') node.removeAttribute('role');
    });
    const override = documentSvg.createElementNS('http://www.w3.org/2000/svg', 'style');
    override.setAttribute('data-slide-theme-override', 'true');
    const declarations = Object.entries(cssVariables)
      .map(([name, value]) => `${name}: ${value} !important;`)
      .join(' ');
    override.textContent = `:root, svg { ${declarations} }\n`
      + (fontFamily ? `svg, svg text, svg tspan { font-family: ${fontFamily} !important; }\n` : '');
    svg.appendChild(override);
    const forbidden = svg.querySelector(
      'script, foreignObject, button, input, select, textarea, [id*="toolbar" i], [class*="toolbar" i], '
      + '[id*="export-menu" i], [class*="export-menu" i]'
    );
    if (forbidden) throw new Error(`non-diagram control leaked into SVG: ${forbidden.tagName}`);
    return {
      svgString: new XMLSerializer().serializeToString(svg),
      viewBox: svg.getAttribute('viewBox'),
    };
  }, { source: canonicalSvg, selectedTheme: args.theme, ...theme });
  if (!exported.viewBox) fail('exported SVG has no viewBox');
  const values = exported.viewBox.trim().split(/[\s,]+/).map(Number);
  if (values.length !== 4 || values.some(value => !Number.isFinite(value)) || values[2] <= 0 || values[3] <= 0) {
    fail(`exported SVG has invalid viewBox: ${exported.viewBox}`);
  }
  return { ...exported, viewBoxValues: values };
}

function outputDimensions(args, viewBox) {
  const ratio = viewBox[2] / viewBox[3];
  const width = args.width;
  const derivedHeight = Math.max(1, Math.round(width / ratio));
  const height = args.height || derivedHeight;
  if (Math.abs((width / height) / ratio - 1) > 0.01) {
    fail(`requested ${width}x${height} distorts the SVG viewBox; use ${width}x${derivedHeight}`);
  }
  return { width, height };
}

async function rasterizeWebp(page, svgString, dimensions) {
  return page.evaluate(async ({ source, width, height }) => {
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
      const image = new Image();
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error('clean SVG could not be decoded for WebP export'));
        image.src = url;
      });
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');
      context.imageSmoothingEnabled = true;
      context.imageSmoothingQuality = 'high';
      context.drawImage(image, 0, 0, width, height);
      const dataUrl = canvas.toDataURL('image/webp', 0.96);
      if (!dataUrl.startsWith('data:image/webp;base64,')) throw new Error('browser did not produce WebP');
      return dataUrl.slice(dataUrl.indexOf(',') + 1);
    } finally {
      URL.revokeObjectURL(url);
    }
  }, { source: svgString, ...dimensions });
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

async function verifyOutputs(browser, outputs, dimensions) {
  const page = await browser.newPage();
  try {
    const receipt = {};
    if (outputs.svg) {
      await page.goto(pathToFileURL(outputs.svg).href, { waitUntil: 'load' });
      const result = await page.evaluate(() => {
        const svg = document.querySelector('svg');
        const forbidden = document.querySelector(
          'script, foreignObject, button, input, select, textarea, [id*="toolbar" i], [class*="toolbar" i], '
          + '[id*="export-menu" i], [class*="export-menu" i]'
        );
        return {
          svgCount: document.querySelectorAll('svg').length,
          forbidden: forbidden?.tagName || '',
          themed: svg?.hasAttribute('data-slide-asset') && !!svg.querySelector('style[data-slide-theme-override]'),
          viewBox: svg?.getAttribute('viewBox') || '',
        };
      });
      if (result.svgCount !== 1 || result.forbidden || !result.themed || !result.viewBox) {
        fail(`SVG verification failed: ${JSON.stringify(result)}`);
      }
      const body = fs.readFileSync(outputs.svg);
      receipt.svg = { path: outputs.svg, bytes: body.length, sha256: sha256(body), ...result };
    }
    if (outputs.webp) {
      await page.goto(pathToFileURL(outputs.webp).href, { waitUntil: 'load' });
      const result = await page.evaluate(() => {
        const image = document.querySelector('img');
        return { width: image?.naturalWidth || 0, height: image?.naturalHeight || 0, complete: image?.complete || false };
      });
      if (!result.complete || result.width !== dimensions.width || result.height !== dimensions.height) {
        fail(`WebP verification failed: expected ${dimensions.width}x${dimensions.height}, got ${result.width}x${result.height}`);
      }
      const body = fs.readFileSync(outputs.webp);
      receipt.webp = { path: outputs.webp, bytes: body.length, sha256: sha256(body), ...result };
    }
    return receipt;
  } finally {
    await page.close();
  }
}

async function main() {
  const args = parseArguments(process.argv.slice(2));
  if (!fs.existsSync(args.input) || !fs.statSync(args.input).isFile()) fail(`Archify HTML not found: ${args.input}`);
  const source = fs.readFileSync(args.input, 'utf8');
  if (!source.includes('class="diagram-container"') || !source.includes('function serializeSvg(')) {
    fail('input is not a compatible Archify HTML artifact');
  }
  const tokenInput = readTokenFile(args.tokens);
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  try {
    const deckTokens = args.deckTheme ? await extractDeckTheme(browser, args.deckTheme, args.slide) : {};
    const theme = expandThemeTokens({ ...deckTokens, ...tokenInput });
    const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });
    const exported = await exportCanonicalSvg(page, args, theme);
    const dimensions = outputDimensions(args, exported.viewBoxValues);
    const outputs = { svg: args.outputSvg, webp: args.outputWebp };
    for (const output of Object.values(outputs).filter(Boolean)) fs.mkdirSync(path.dirname(output), { recursive: true });
    if (outputs.svg) fs.writeFileSync(outputs.svg, `${exported.svgString}\n`, 'utf8');
    if (outputs.webp) {
      const base64 = await rasterizeWebp(page, exported.svgString, dimensions);
      fs.writeFileSync(outputs.webp, Buffer.from(base64, 'base64'));
    }
    await page.close();
    const artifacts = await verifyOutputs(browser, outputs, dimensions);
    const receipt = {
      schema_version: 1,
      source: args.input,
      source_sha256: sha256(Buffer.from(source)),
      theme: args.theme,
      theme_source: args.deckTheme || args.tokens || 'archify-light-default',
      slide: args.deckTheme ? args.slide : null,
      view_box: exported.viewBox,
      dimensions,
      controls_removed: true,
      artifacts,
    };
    if (args.json) process.stdout.write(`${JSON.stringify(receipt, null, 2)}\n`);
    else process.stdout.write(
      `OK: exported clean Archify asset at ${dimensions.width}x${dimensions.height} `
      + `(${Object.keys(artifacts).join(' + ')}, ${args.theme} theme, no viewer controls)\n`
    );
  } finally {
    await browser.close();
  }
}

main().catch(error => fail(error.stack || error.message));
