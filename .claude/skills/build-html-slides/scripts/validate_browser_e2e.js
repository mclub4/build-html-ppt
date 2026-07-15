#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { pathToFileURL } = require('url');

function loadPlaywright() {
  for (const candidate of [
    'playwright',
    path.join(os.homedir(), '.local/lib/node_modules/playwright'),
    '/usr/local/lib/node_modules/playwright',
    '/usr/lib/node_modules/playwright',
  ]) {
    try {
      return require(candidate);
    } catch (error) {
      if (error.code !== 'MODULE_NOT_FOUND') throw error;
    }
  }
  throw new Error('Playwright is not installed');
}

function fail(message) {
  process.stderr.write(`ERROR: ${message}\n`);
  process.exit(1);
}

async function main() {
  const deck = process.argv[2] ? path.resolve(process.argv[2]) : '';
  if (!deck || !fs.existsSync(deck) || !fs.statSync(deck).isFile()) {
    fail('usage: validate_browser_e2e.js DECK.html');
  }

  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const page = await context.newPage();
    await page.addInitScript(() => {
      window.__slideValidationFullscreenRequests = 0;
      Object.defineProperty(Element.prototype, 'requestFullscreen', {
        configurable: true,
        value: async function requestFullscreen() {
          window.__slideValidationFullscreenRequests += 1;
        },
      });
      Object.defineProperty(Document.prototype, 'exitFullscreen', {
        configurable: true,
        value: async function exitFullscreen() {
          window.__slideValidationFullscreenRequests += 1;
        },
      });
    });
    await page.goto(`${pathToFileURL(deck).href}#1`, { waitUntil: 'load' });
    await page.addStyleTag({ content: '*,*::before,*::after{animation:none!important;transition:none!important}' });
    await page.evaluate(async () => {
      if (document.fonts?.ready) await document.fonts.ready;
      await Promise.all([...document.images].map(image => image.complete ? null : new Promise(resolve => {
        image.addEventListener('load', resolve, { once: true });
        image.addEventListener('error', resolve, { once: true });
      })));
    });

    const count = await page.locator('section.slide').count();
    if (count < 2) throw new Error('browser E2E requires at least two slides');

    const assertState = async (expected, label) => {
      const state = await page.evaluate(() => {
        const slides = [...document.querySelectorAll('section.slide')];
        const active = slides.filter(slide => slide.classList.contains('active'));
        return {
          active: active.length === 1 ? slides.indexOf(active[0]) + 1 : 0,
          activeCount: active.length,
          hash: window.location.hash,
          input: document.getElementById('pageInput')?.value || '',
          total: document.getElementById('total')?.textContent || '',
          prevDisabled: document.getElementById('prev')?.disabled,
          nextDisabled: document.getElementById('next')?.disabled,
        };
      });
      if (
        state.activeCount !== 1 || state.active !== expected || state.hash !== `#${expected}`
        || state.input !== String(expected) || state.total !== String(count)
        || state.prevDisabled !== (expected === 1) || state.nextDisabled !== (expected === count)
      ) {
        const message = `${label} produced inconsistent navigation state: ${JSON.stringify(state)}`;
        errors.push(message);
        throw new Error(message);
      }
    };

    await assertState(1, 'initial load');
    await page.locator('#next').click();
    await assertState(2, 'next button');
    await page.locator('#prev').click();
    await assertState(1, 'previous button');
    await page.locator('#edgeRight').click({ position: { x: 2, y: 200 } });
    await assertState(2, 'right edge');
    await page.locator('#edgeLeft').click({ position: { x: 2, y: 200 } });
    await assertState(1, 'left edge');

    await page.locator('#pageInput').fill(String(count));
    await page.locator('#pageInput').press('Enter');
    await assertState(count, 'direct page input');
    await page.keyboard.press('Home');
    await assertState(1, 'Home key');
    await page.keyboard.press('End');
    await assertState(count, 'End key');
    await page.keyboard.press('ArrowLeft');
    await assertState(Math.max(1, count - 1), 'ArrowLeft key');
    await page.keyboard.press('ArrowRight');
    await assertState(count, 'ArrowRight key');
    await page.keyboard.press('f');
    const fullscreenRequests = await page.evaluate(() => window.__slideValidationFullscreenRequests);
    if (fullscreenRequests !== 1) errors.push('fullscreen shortcut did not invoke the browser API exactly once');

    await page.emulateMedia({ media: 'print' });
    const print = await page.evaluate(() => {
      const slides = [...document.querySelectorAll('section.slide')];
      const stage = document.getElementById('stage');
      const hiddenControls = ['.nav', '.edge.left', '.edge.right', '.progress'].every(selector => {
        const element = document.querySelector(selector);
        return element && getComputedStyle(element).display === 'none';
      });
      const records = slides.map(slide => {
        const style = getComputedStyle(slide);
        const rect = slide.getBoundingClientRect();
        return {
          position: style.position,
          visibility: style.visibility,
          opacity: Number(style.opacity),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          top: Math.round(rect.top),
          breakAfter: style.breakAfter,
          pageBreakAfter: style.pageBreakAfter,
        };
      });
      return {
        hiddenControls,
        stageTransform: getComputedStyle(stage).transform,
        stagePosition: getComputedStyle(stage).position,
        records,
      };
    });
    if (!print.hiddenControls) errors.push('print media must hide navigation, edges, and progress');
    if (print.stageTransform !== 'none' || print.stagePosition !== 'relative') {
      errors.push(`print stage must be unscaled and relative: ${print.stagePosition}/${print.stageTransform}`);
    }
    print.records.forEach((record, index) => {
      if (
        record.position !== 'relative' || record.visibility !== 'visible' || record.opacity !== 1
        || record.width !== 1280 || record.height !== 720
      ) {
        errors.push(`print slide ${index + 1} is not a visible 1280x720 page: ${JSON.stringify(record)}`);
      }
      if (index > 0 && record.top < print.records[index - 1].top + 720) {
        errors.push(`print slide ${index + 1} overlaps the previous page`);
      }
      if (!['always', 'page'].includes(record.pageBreakAfter) && record.breakAfter !== 'page') {
        errors.push(`print slide ${index + 1} has no page break`);
      }
    });
    await context.close();
  } finally {
    await browser.close();
  }

  if (errors.length) {
    errors.forEach(error => process.stderr.write(`ERROR: ${error}\n`));
    process.exit(1);
  }
  process.stdout.write(`OK: ${deck} - browser navigation, fullscreen binding, and print layout passed E2E\n`);
}

main().catch(error => fail(error.stack || error.message));
