#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const { loadPlaywright } = require('./playwright_loader');

const DEFAULT_BATCH_SIZE = 12;
const MAX_BATCH_SIZE = 12;
const VIEWPORT_WIDTH = 1440;

function fail(message) {
  process.stderr.write(`ERROR: ${message}\n`);
  process.exit(1);
}

function usage() {
  process.stderr.write(
    'usage: node build_media_contact_sheet.js MANIFEST.json [OUTPUT_DIR] '
    + '[--batch-size 8-12] [--title TITLE]\n'
  );
  process.exit(2);
}

function htmlEscape(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function sha256(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function sourceHost(value) {
  if (!value) return '';
  try {
    return new URL(value).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function parseArgs(argv) {
  if (!argv.length || argv.includes('--help') || argv.includes('-h')) usage();
  const manifest = path.resolve(argv[0]);
  let output = null;
  let batchSize = DEFAULT_BATCH_SIZE;
  let title = '';
  let position = 1;
  if (argv[position] && !argv[position].startsWith('--')) {
    output = path.resolve(argv[position]);
    position += 1;
  }
  while (position < argv.length) {
    const option = argv[position];
    if (option === '--batch-size') {
      batchSize = Number.parseInt(argv[position + 1], 10);
      position += 2;
    } else if (option === '--title') {
      title = argv[position + 1] || '';
      position += 2;
    } else {
      fail(`unknown option: ${option}`);
    }
  }
  if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > MAX_BATCH_SIZE) {
    fail(`--batch-size must be between 1 and ${MAX_BATCH_SIZE}`);
  }
  return {
    manifest,
    output: output || path.join(path.dirname(manifest), `${path.basename(manifest, path.extname(manifest))}-contact-sheets`),
    batchSize,
    title,
  };
}

function loadManifest(manifestPath) {
  if (!fs.existsSync(manifestPath)) fail(`manifest not found: ${manifestPath}`);
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  } catch (error) {
    fail(`invalid manifest JSON: ${error.message}`);
  }
  if (!payload || !Array.isArray(payload.items) || !payload.items.length) {
    fail('manifest must contain a non-empty items array');
  }
  const root = path.dirname(manifestPath);
  const ids = new Set();
  const items = payload.items.map((item, index) => {
    const id = String(item.id || index + 1).trim();
    const label = String(item.label || '').trim();
    const rawPath = String(item.path || '').trim();
    if (!id || ids.has(id)) fail(`item ${index + 1} needs a unique id`);
    if (!label) fail(`item ${index + 1} needs a label`);
    if (!rawPath) fail(`item ${index + 1} needs a local path`);
    const filePath = path.resolve(root, rawPath);
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
      fail(`item ${id} image not found: ${filePath}`);
    }
    ids.add(id);
    return {
      id,
      label,
      filePath,
      relativePath: path.relative(root, filePath).split(path.sep).join('/'),
      kind: String(item.kind || 'subject').trim(),
      cue: String(item.cue || '').trim(),
      sourceUrl: String(item.source_url || '').trim(),
      sourceHost: sourceHost(item.source_url),
      plannedUse: String(item.planned_use || '').trim(),
      minWidth: Number.isFinite(item.min_width) ? Number(item.min_width) : 0,
      minHeight: Number.isFinite(item.min_height) ? Number(item.min_height) : 0,
      sha256: sha256(filePath),
    };
  });
  return { title: String(payload.title || '').trim(), items };
}

function cardMarkup(item, position) {
  const cue = item.cue || 'Confirm the exact subject and reject a wrong variant, work, person, place, or package.';
  const meta = [item.kind, item.sourceHost, item.plannedUse].filter(Boolean).join(' · ');
  return `<article class="card" data-item-id="${htmlEscape(item.id)}">
    <div class="media"><img src="${htmlEscape(pathToFileURL(item.filePath).href)}" alt=""></div>
    <div class="copy">
      <div class="index">${String(position).padStart(2, '0')}</div>
      <h2>${htmlEscape(item.label)}</h2>
      <p class="cue">${htmlEscape(cue)}</p>
      <p class="meta">${htmlEscape(meta || item.relativePath)}</p>
      <p class="dimensions" aria-live="polite">checking pixels…</p>
    </div>
  </article>`;
}

function sheetHtml(title, items, offset) {
  const cards = items.map((item, index) => cardMarkup(item, offset + index + 1)).join('');
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}html,body{margin:0;background:#e9e8e3;color:#151513;font-family:Arial,"Noto Sans KR",sans-serif}
    main{width:${VIEWPORT_WIDTH}px;padding:34px 38px 42px}.heading{display:flex;align-items:end;justify-content:space-between;margin-bottom:22px;border-bottom:2px solid #1b1b18;padding-bottom:13px}
    h1{margin:0;font-size:28px;line-height:1.1}.legend{font-size:13px;color:#5b5a54}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}
    .card{min-width:0;background:#fff;border:1px solid #c9c7bf;display:grid;grid-template-rows:205px auto;box-shadow:0 2px 0 rgba(0,0,0,.05)}
    .media{position:relative;display:grid;place-items:center;overflow:hidden;background:
      linear-gradient(45deg,#ecebe6 25%,transparent 25%),linear-gradient(-45deg,#ecebe6 25%,transparent 25%),
      linear-gradient(45deg,transparent 75%,#ecebe6 75%),linear-gradient(-45deg,transparent 75%,#ecebe6 75%);background-size:24px 24px;background-position:0 0,0 12px,12px -12px,-12px 0}
    img{display:block;width:100%;height:100%;object-fit:contain}.copy{position:relative;min-height:150px;padding:14px 15px 15px 50px}
    .index{position:absolute;left:15px;top:15px;color:#d44d36;font:700 15px/1 monospace}
    h2{margin:0 0 7px;font-size:17px;line-height:1.25;overflow-wrap:anywhere}.cue{margin:0 0 9px;font-size:12px;line-height:1.42;color:#373732}
    .meta,.dimensions{margin:0;font-size:10px;line-height:1.4;color:#77746c;overflow-wrap:anywhere}.dimensions{margin-top:4px;font-family:monospace}
    .card.warning{outline:4px solid #d44d36;outline-offset:-4px}.card.warning .dimensions{color:#b33220;font-weight:700}
  </style></head><body><main>
    <div class="heading"><h1>${htmlEscape(title)}</h1><div class="legend">Check identity · variant · attribution · sharpness · watermark · crop potential</div></div>
    <section class="grid">${cards}</section>
  </main><script>
    const requirements=${JSON.stringify(items.map(item => ({ id: item.id, minWidth: item.minWidth, minHeight: item.minHeight })))};
    for(const card of document.querySelectorAll('.card')){
      const image=card.querySelector('img');const output=card.querySelector('.dimensions');
      const requirement=requirements.find(item=>item.id===card.dataset.itemId);
      const update=()=>{const width=image.naturalWidth||0;const height=image.naturalHeight||0;const warnings=[];
        if(!width||!height)warnings.push('unreadable');
        if(requirement.minWidth&&width<requirement.minWidth)warnings.push('below min width');
        if(requirement.minHeight&&height<requirement.minHeight)warnings.push('below min height');
        output.textContent=width+' × '+height+(warnings.length?' · '+warnings.join(', '):'');
        card.classList.toggle('warning',warnings.length>0);
      };
      image.addEventListener('load',update,{once:true});image.addEventListener('error',update,{once:true});if(image.complete)update();
    }
  </script></body></html>`;
}

async function waitForImages(page) {
  await page.waitForFunction(() => [...document.images].every(image => image.complete));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifest = loadManifest(args.manifest);
  const title = args.title || manifest.title || 'Sourced media audit';
  fs.mkdirSync(args.output, { recursive: true });

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true, args: ['--allow-file-access-from-files'] });
  const sheets = [];
  try {
    for (let offset = 0; offset < manifest.items.length; offset += args.batchSize) {
      const batch = manifest.items.slice(offset, offset + args.batchSize);
      const number = sheets.length + 1;
      const htmlPath = path.join(args.output, `media-contact-sheet-${String(number).padStart(2, '0')}.html`);
      const pngPath = path.join(args.output, `media-contact-sheet-${String(number).padStart(2, '0')}.png`);
      fs.writeFileSync(htmlPath, sheetHtml(title, batch, offset));
      const page = await browser.newPage({ viewport: { width: VIEWPORT_WIDTH, height: 980 }, deviceScaleFactor: 1 });
      try {
        await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'domcontentloaded' });
        await waitForImages(page);
        const metrics = await page.evaluate(() => [...document.querySelectorAll('.card')].map(card => {
          const image = card.querySelector('img');
          return {
            id: card.dataset.itemId,
            width: image.naturalWidth || 0,
            height: image.naturalHeight || 0,
            warning: card.classList.contains('warning'),
          };
        }));
        await page.screenshot({ path: pngPath, fullPage: true });
        sheets.push({
          sheet: number,
          path: path.basename(pngPath),
          sha256: sha256(pngPath),
          items: batch.map(item => item.id),
          metrics,
        });
      } finally {
        await page.close();
        fs.rmSync(htmlPath, { force: true });
      }
    }
  } finally {
    await browser.close();
  }

  const duplicateHashes = Object.entries(
    manifest.items.reduce((groups, item) => {
      groups[item.sha256] ||= [];
      groups[item.sha256].push(item.id);
      return groups;
    }, {})
  ).filter(([, ids]) => ids.length > 1).map(([hash, ids]) => ({ sha256: hash, items: ids }));
  const index = {
    schema_version: 1,
    title,
    manifest: args.manifest,
    batch_size: args.batchSize,
    review_instruction: 'Open each PNG once. Compare the visible subject to its label and cue; flag only mismatches, wrong variants/works/people/places, soft or unusable sources, watermarks, and crop risks. Deep-research only flagged items.',
    items: manifest.items.map(item => ({
      id: item.id,
      label: item.label,
      kind: item.kind,
      cue: item.cue,
      path: item.relativePath,
      source_url: item.sourceUrl,
      sha256: item.sha256,
    })),
    duplicate_hashes: duplicateHashes,
    sheets,
  };
  const indexPath = path.join(args.output, 'media-contact-sheet-index.json');
  fs.writeFileSync(indexPath, `${JSON.stringify(index, null, 2)}\n`);
  process.stdout.write(
    `OK: ${manifest.items.length} media item(s) in ${sheets.length} contact sheet(s); `
    + `${duplicateHashes.length} duplicate hash group(s)\n${indexPath}\n`
  );
}

main().catch(error => fail(error.stack || error.message));
