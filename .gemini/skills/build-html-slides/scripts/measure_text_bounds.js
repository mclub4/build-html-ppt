(() => {
  const started = typeof performance === 'object' && performance ? performance.now() : Date.now();
  const tolerance = 2;
  // Deterministic thresholds, all expressed in logical (unscaled) stage pixels.
  const inkCollisionTolerance = 1;   // glyph ink of one line reaching into the next line
  const foregroundBiteTolerance = 1.5; // opaque foreground eating into glyph ink
  const columnSize = 6;              // width of the vertical ink-profile columns
  const active = document.querySelector('.slide.active');
  const issues = [];
  const warnings = [];
  const elapsed = () => Math.round(
    ((typeof performance === 'object' && performance ? performance.now() : Date.now()) - started) * 100
  ) / 100;
  if (!active) {
    return { ok: false, checked: 0, line_checks: 0, issues: ['Missing active slide'], warnings, elapsed_ms: elapsed() };
  }

  const styleCache = new WeakMap();
  const styleOf = element => {
    let style = styleCache.get(element);
    if (!style) {
      style = getComputedStyle(element);
      styleCache.set(element, style);
    }
    return style;
  };
  const visible = element => {
    const style = styleOf(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0
      && rect.width > 0 && rect.height > 0;
  };
  const label = element => {
    const explicit = element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id;
    const content = (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 56);
    return explicit || content || element.tagName.toLowerCase();
  };
  const outside = (inner, outer) => (
    inner.left < outer.left - tolerance || inner.right > outer.right + tolerance
    || inner.top < outer.top - tolerance || inner.bottom > outer.bottom + tolerance
  );
  const intersection = (left, right) => ({
    width: Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left)),
    height: Math.max(0, Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top)),
  });
  const overlaps = (left, right) => (
    left.left < right.right && right.left < left.right
    && left.top < right.bottom && right.top < left.bottom
  );
  const directText = element => [...element.childNodes].some(node => (
    node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()
  ));
  const normalizeFontFamily = value => value.trim().replace(/^['"]|['"]$/g, '').toLowerCase();
  const parseFontWeight = value => {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized === 'normal') return 400;
    if (normalized === 'bold') return 700;
    const parsed = Number.parseInt(normalized, 10);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const declaredFontWeights = new Map();
  const collectFontFaces = rules => {
    for (const rule of rules) {
      if (rule.type === CSSRule.FONT_FACE_RULE) {
        const family = normalizeFontFamily(rule.style.getPropertyValue('font-family'));
        const parts = rule.style.getPropertyValue('font-weight').trim().split(/\s+/).filter(Boolean);
        const start = parseFontWeight(parts[0] || 'normal');
        const end = parseFontWeight(parts[1] || parts[0] || 'normal');
        if (family && start !== null && end !== null) {
          const ranges = declaredFontWeights.get(family) || [];
          ranges.push([Math.min(start, end), Math.max(start, end)]);
          declaredFontWeights.set(family, ranges);
        }
      } else if (rule.cssRules) {
        collectFontFaces(rule.cssRules);
      }
    }
  };
  for (const sheet of document.styleSheets) {
    try {
      collectFontFaces(sheet.cssRules);
    } catch (_error) {
      warnings.push('A stylesheet could not be inspected for declared font weights');
    }
  }
  const declaredFamily = style => {
    const families = style.fontFamily.match(/(?:"[^"]*"|'[^']*'|[^,])+/g) || [];
    return families.map(normalizeFontFamily).find(family => declaredFontWeights.has(family));
  };
  const emphasisSignature = style => [
    style.fontFamily, style.fontSize, style.fontWeight, style.fontStyle,
    style.color, style.backgroundColor, style.textDecorationLine,
    style.textDecorationStyle, style.textDecorationColor, style.textShadow,
    style.letterSpacing,
  ].join('|');
  const inlineTextTags = new Set(['SPAN', 'BR', 'EM', 'STRONG', 'B', 'I', 'SMALL', 'MARK', 'S', 'U']);
  const inlineTextWrapper = element => {
    const display = styleOf(element).display;
    return element.childElementCount > 0
      && !display.includes('grid') && !display.includes('flex')
      && (element.textContent || '').trim()
      && [...element.children].every(child => inlineTextTags.has(child.tagName));
  };
  const textSelectors = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'dt', 'dd', 'td', 'th',
    'button', 'a', 'label', 'figcaption', 'blockquote', 'pre', 'code',
    '.display-type', '.headline', '.title', '.quote', '.eyebrow', '.kicker',
    '.caption', '.source', '.footnote', '.badge', '.chip',
    '[data-display-text]', '[data-text-box]', '[data-text-container]'
  ].join(',');
  const displaySelectors = [
    'h1', 'h2', 'h3', 'blockquote', '.display-type', '.headline', '.title', '.quote',
    '[data-display-text]'
  ].join(',');

  const slideRect = active.getBoundingClientRect();
  const logicalSlideWidth = active.offsetWidth || slideRect.width;
  const stageScale = logicalSlideWidth ? slideRect.width / logicalSlideWidth : 1;
  const scaled = value => value * (stageScale > 0 ? stageScale : 1);
  const logical = value => value / (stageScale > 0 ? stageScale : 1);
  const columnStep = Math.max(1, scaled(columnSize));
  const viewportWidth = document.documentElement.clientWidth;
  const viewportHeight = document.documentElement.clientHeight;
  if (
    slideRect.left < -tolerance || slideRect.top < -tolerance
    || slideRect.right > viewportWidth + tolerance || slideRect.bottom > viewportHeight + tolerance
  ) {
    issues.push(
      `Active slide crosses viewport bounds: ${Math.round(slideRect.left)},${Math.round(slideRect.top)} `
      + `${Math.round(slideRect.right)},${Math.round(slideRect.bottom)} vs ${viewportWidth}x${viewportHeight}`
    );
  }

  // Real glyph-ink metrics. Range.getClientRects() returns the font box (ascent+descent of the
  // active face), never the painted ink, so a comma tail or a Korean jamo descender is invisible to
  // pure rect math. Canvas TextMetrics supplies the ink extents; both are anchored on the shared
  // baseline, which the font box locates exactly.
  let measureContext = null;
  const context2d = () => {
    if (measureContext === null) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 8;
        canvas.height = 8;
        measureContext = canvas.getContext('2d') || false;
      } catch (_error) {
        measureContext = false;
      }
    }
    return measureContext || null;
  };
  const fontSignature = style => (
    `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
  );
  const fontBoxCache = new Map();
  const inkCache = new Map();
  const finite = value => (typeof value === 'number' && Number.isFinite(value) ? value : null);
  const fontBoxFor = signature => {
    if (fontBoxCache.has(signature)) return fontBoxCache.get(signature);
    let metrics = null;
    const context = context2d();
    if (context) {
      context.font = signature;
      if (context.font) {
        const measured = context.measureText('Hxg');
        const ascent = finite(measured.fontBoundingBoxAscent);
        const descent = finite(measured.fontBoundingBoxDescent);
        if (ascent !== null && descent !== null && ascent + descent > 0) metrics = { ascent, descent };
      }
    }
    fontBoxCache.set(signature, metrics);
    return metrics;
  };
  const inkFor = (signature, text) => {
    const key = `${signature}\u0000${text}`;
    if (inkCache.has(key)) return inkCache.get(key);
    let metrics = null;
    const context = context2d();
    if (context) {
      context.font = signature;
      if (context.font) {
        const measured = context.measureText(text);
        const ascent = finite(measured.actualBoundingBoxAscent);
        const descent = finite(measured.actualBoundingBoxDescent);
        const left = finite(measured.actualBoundingBoxLeft);
        const right = finite(measured.actualBoundingBoxRight);
        if (ascent !== null && descent !== null) metrics = { ascent, descent, left, right };
      }
    }
    inkCache.set(key, metrics);
    return metrics;
  };

  const semanticElements = [...active.querySelectorAll(textSelectors)];
  const allHtmlElements = [...active.querySelectorAll('*')].filter(element => (
    element.namespaceURI === 'http://www.w3.org/1999/xhtml'
  ));
  const directTextElements = allHtmlElements.filter(directText);
  const inlineTextWrapperCandidates = allHtmlElements.filter(inlineTextWrapper);
  const inlineTextWrappers = inlineTextWrapperCandidates.filter(element => (
    !element.parentElement?.closest(textSelectors)
    && !inlineTextWrapperCandidates.some(owner => owner !== element && owner.contains(element))
  ));
  const elements = [...new Set([...semanticElements, ...directTextElements, ...inlineTextWrappers])].filter(element => (
    visible(element) && (element.textContent || '').trim()
    && !element.closest('[data-text-bounds-ignore]')
  ));

  for (const emphasis of active.querySelectorAll('strong, b')) {
    if (!visible(emphasis) || !(emphasis.textContent || '').trim() || emphasis.closest('[data-text-bounds-ignore]')) continue;
    const parent = emphasis.parentElement;
    if (!parent) continue;
    const targets = directText(emphasis)
      ? [emphasis]
      : [...emphasis.querySelectorAll('*')].filter(element => directText(element) && visible(element));
    if (targets.length && targets.every(target => (
      emphasisSignature(styleOf(target)) === emphasisSignature(styleOf(parent))
    ))) {
      issues.push(`${label(emphasis)}: <${emphasis.tagName.toLowerCase()}> has no visible emphasis; use a supported weight or another deliberate cue`);
    }
  }

  for (const element of elements) {
    const elementRect = element.getBoundingClientRect();
    const selfBoxTags = new Set(['BUTTON', 'TD', 'TH', 'PRE', 'CODE']);
    const semanticContainer = element.closest('[data-text-container], .card, .panel, .tile, .badge, .chip');
    const container = semanticContainer || (selfBoxTags.has(element.tagName) ? element : active);
    const containerRect = container.getBoundingClientRect();
    const name = label(element);
    const style = styleOf(element);
    const localFamily = declaredFamily(style);
    const requestedWeight = parseFontWeight(style.fontWeight);
    if (localFamily && requestedWeight !== null) {
      const supported = declaredFontWeights.get(localFamily).some(([start, end]) => (
        requestedWeight >= start && requestedWeight <= end
      ));
      if (!supported) {
        issues.push(
          `${name}: font-family "${localFamily}" requests weight ${requestedWeight} outside its declared local faces; `
          + 'bundle that weight or choose a supported weight instead of browser-synthesized bold'
        );
      }
    }
    const clipsX = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX);
    const clipsY = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY);

    if (outside(elementRect, slideRect)) issues.push(`${name}: element crosses active slide bounds`);
    if (clipsX && element.scrollWidth > element.clientWidth + tolerance) {
      issues.push(`${name}: horizontal text overflow ${element.scrollWidth - element.clientWidth}px`);
    }
    if (clipsY && element.scrollHeight > element.clientHeight + tolerance) {
      issues.push(`${name}: vertical text overflow ${element.scrollHeight - element.clientHeight}px`);
    }

    const boundsRange = document.createRange();
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT
    });
    while (walker.nextNode()) {
      boundsRange.selectNodeContents(walker.currentNode);
      const rects = boundsRange.getClientRects();
      let crossed = false;
      for (let index = 0; index < rects.length && !crossed; index += 1) {
        const rect = rects[index];
        crossed = Boolean(rect.width && rect.height && outside(rect, containerRect));
      }
      if (crossed) {
        issues.push(`${name}: rendered glyph bounds cross the intended text container`);
        break;
      }
    }
  }

  const explicitLineOwners = elements.filter(element => (
    element.matches(textSelectors) || inlineTextWrapper(element)
  ));
  const lineOwners = [...new Set([...explicitLineOwners, ...elements.filter(element => (
    directText(element)
    && !explicitLineOwners.some(owner => owner !== element && owner.contains(element))
  ))])];
  const segmenter = typeof Intl.Segmenter === 'function'
    ? new Intl.Segmenter(undefined, { granularity: 'grapheme' })
    : null;
  const segments = value => {
    if (segmenter) return [...segmenter.segment(value)].map(item => ({ text: item.segment, index: item.index }));
    const result = [];
    let index = 0;
    for (const text of Array.from(value)) {
      result.push({ text, index });
      index += text.length;
    }
    return result;
  };

  const collectLines = element => {
    const glyphs = [];
    let order = 0;
    const leftToRight = styleOf(element).direction !== 'rtl';
    const range = document.createRange();
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: node => {
        if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent || !visible(parent) || parent.closest('[data-text-bounds-ignore]')) {
          return NodeFilter.FILTER_REJECT;
        }
        const nestedOwner = lineOwners.find(candidate => (
          candidate !== element && element.contains(candidate) && candidate.contains(parent)
        ));
        return nestedOwner ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const signature = fontSignature(styleOf(node.parentElement));
      const fontBox = fontBoxFor(signature);
      for (const part of segments(node.nodeValue)) {
        range.setStart(node, part.index);
        range.setEnd(node, part.index + part.text.length);
        const rects = range.getClientRects();
        let rect = null;
        for (let index = 0; index < rects.length; index += 1) {
          const candidate = rects[index];
          if (candidate.width > 0 && candidate.height > 0) {
            rect = candidate;
            break;
          }
        }
        if (!rect) continue;
        // Ink extents in client pixels. `unit` converts font-design pixels into the rendered scale
        // that Chromium actually used for this rect, so transforms and zoom stay correct.
        let inkTop = rect.top;
        let inkBottom = rect.bottom;
        let inkLeft = rect.left;
        let inkRight = rect.right;
        let hasInk = false;
        if (fontBox) {
          const ink = part.text.trim() ? inkFor(signature, part.text) : null;
          const unit = rect.height / (fontBox.ascent + fontBox.descent);
          const baseline = rect.top + fontBox.ascent * unit;
          if (ink && ink.ascent + ink.descent > 0) {
            inkTop = baseline - ink.ascent * unit;
            inkBottom = baseline + ink.descent * unit;
            if (ink.left !== null && ink.right !== null && ink.left + ink.right > 0) {
              inkLeft = Math.max(rect.left - ink.left * unit, rect.left - rect.width);
              inkRight = Math.min(rect.left + ink.right * unit, rect.right + rect.width);
            }
            hasInk = true;
          } else {
            inkTop = baseline;
            inkBottom = baseline;
          }
        } else if (part.text.trim()) {
          hasInk = true;
        }
        glyphs.push({ text: part.text, order, rect, inkTop, inkBottom, inkLeft, inkRight, hasInk });
        order += 1;
      }
    }

    const lines = [];
    for (const glyph of glyphs) {
      let target = null;
      let nearest = Number.POSITIVE_INFINITY;
      for (const line of lines) {
        const delta = Math.abs(glyph.rect.top - line.anchorTop);
        const limit = Math.max(2, Math.min(glyph.rect.height, line.height) * 0.18);
        const overlap = Math.max(0, Math.min(glyph.rect.bottom, line.bottom) - Math.max(glyph.rect.top, line.top));
        const overlapRatio = overlap / Math.max(1, Math.min(glyph.rect.height, line.height));
        const continuesInline = leftToRight && overlapRatio > 0.5 && glyph.rect.left >= line.right - 2;
        if ((delta <= limit || continuesInline) && delta < nearest) {
          target = line;
          nearest = delta;
        }
      }
      if (!target) {
        target = {
          anchorTop: glyph.rect.top,
          top: glyph.rect.top,
          right: glyph.rect.right,
          bottom: glyph.rect.bottom,
          left: glyph.rect.left,
          height: glyph.rect.height,
          inkTop: Number.POSITIVE_INFINITY,
          inkBottom: Number.NEGATIVE_INFINITY,
          inkLeft: Number.POSITIVE_INFINITY,
          inkRight: Number.NEGATIVE_INFINITY,
          glyphs: [],
        };
        lines.push(target);
      }
      target.glyphs.push(glyph);
      target.top = Math.min(target.top, glyph.rect.top);
      target.right = Math.max(target.right, glyph.rect.right);
      target.bottom = Math.max(target.bottom, glyph.rect.bottom);
      target.left = Math.min(target.left, glyph.rect.left);
      target.height = target.bottom - target.top;
      if (glyph.hasInk) {
        target.inkTop = Math.min(target.inkTop, glyph.inkTop);
        target.inkBottom = Math.max(target.inkBottom, glyph.inkBottom);
        target.inkLeft = Math.min(target.inkLeft, glyph.inkLeft);
        target.inkRight = Math.max(target.inkRight, glyph.inkRight);
      }
    }
    return lines
      .sort((left, right) => left.top - right.top)
      .map(line => {
        const inked = Number.isFinite(line.inkTop) && Number.isFinite(line.inkBottom);
        return {
          ...line,
          inkTop: inked ? line.inkTop : line.top,
          inkBottom: inked ? line.inkBottom : line.bottom,
          inkLeft: inked ? line.inkLeft : line.left,
          inkRight: inked ? line.inkRight : line.right,
          inked,
          text: line.glyphs.sort((left, right) => left.order - right.order).map(glyph => glyph.text).join(''),
          width: line.right - line.left,
        };
      });
  };

  // Per-line vertical ink profile, bucketed into fixed-width columns. Bucketing keeps every
  // comparison O(columns) instead of O(glyphs x glyphs) while preserving horizontal precision.
  const columnCache = new WeakMap();
  const columnsOf = line => {
    let columns = columnCache.get(line);
    if (columns) return columns;
    columns = new Map();
    for (const glyph of line.glyphs) {
      if (!glyph.hasInk) continue;
      const first = Math.floor(glyph.inkLeft / columnStep);
      const last = Math.floor((glyph.inkRight - 0.001) / columnStep);
      for (let index = first; index <= last; index += 1) {
        const bucket = columns.get(index);
        if (bucket) {
          bucket.top = Math.min(bucket.top, glyph.inkTop);
          bucket.bottom = Math.max(bucket.bottom, glyph.inkBottom);
        } else {
          columns.set(index, { top: glyph.inkTop, bottom: glyph.inkBottom });
        }
      }
    }
    columnCache.set(line, columns);
    return columns;
  };

  const lineRecords = [];
  for (const element of lineOwners) {
    const style = styleOf(element);
    if (!style.writingMode.startsWith('horizontal')) continue;
    const lines = collectLines(element);
    if (!lines.length) continue;
    lineRecords.push({ element, lines, rect: element.getBoundingClientRect() });
    if (lines.length < 2) continue;

    const name = label(element);
    const fullText = lines.map(line => line.text).join('');
    const core = value => Array.from(value.normalize('NFC').replace(/[\s\p{P}\p{S}]/gu, ''));
    const lastCore = core(lines.at(-1).text);
    const previousCore = core(lines.at(-2).text);
    const fullCore = core(fullText);
    const hasHangul = /[\uAC00-\uD7A3]/.test(fullText);
    const displayText = element.matches(displaySelectors) || Number.parseFloat(style.fontSize) >= 32;
    if (element.hasAttribute('data-line-break-ok')) {
      warnings.push(`${name}: intentional final-line exemption requires visual inspection`);
    } else {
      if (displayText && fullCore.length >= 8 && lastCore.length === 0) {
        issues.push(`${name}: punctuation is stranded on its own final line`);
      } else if (displayText && fullCore.length >= 8 && previousCore.length >= 4 && hasHangul && lastCore.length <= 2) {
        issues.push(`${name}: stranded Korean ending leaves only ${lastCore.length} readable character(s) on the final line`);
      }
    }

    const fontSize = Number.parseFloat(style.fontSize);
    const minimumAdvanceRatio = hasHangul ? 0.86 : 0.8;
    const axisAligned = style.transform === 'none';
    let collision = false;
    let inkCollision = 0;
    for (let index = 1; index < lines.length; index += 1) {
      const previous = lines[index - 1];
      const current = lines[index];
      const advance = current.top - previous.top;
      const advanceRatio = fontSize > 0 ? advance / (fontSize * stageScale) : 1;
      const overlap = Math.max(0, previous.bottom - current.top);
      const overlapRatio = overlap / Math.max(1, Math.min(previous.height, current.height));
      if (axisAligned && (advanceRatio < minimumAdvanceRatio || overlapRatio > 0.4)) collision = true;
      // True ink test: a descender, comma tail, or Korean jamo reaching the row below is caught
      // per column, so ascenders far away on the same line cannot mask or fake a collision.
      if (!axisAligned || advance <= 0 || !previous.inked || !current.inked) continue;
      const upper = columnsOf(previous);
      const lower = columnsOf(current);
      const [small, fromUpper] = upper.size <= lower.size ? [upper, true] : [lower, false];
      for (const [key, bucket] of small) {
        const other = (fromUpper ? lower : upper).get(key);
        if (!other) continue;
        const upperBottom = fromUpper ? bucket.bottom : other.bottom;
        const lowerTop = fromUpper ? other.top : bucket.top;
        const bite = logical(upperBottom - lowerTop);
        if (bite > inkCollision) inkCollision = bite;
      }
    }
    if (inkCollision >= inkCollisionTolerance) {
      issues.push(
        `${name}: rendered text lines collide by ${Math.round(inkCollision * 10) / 10}px of glyph ink; `
        + 'increase line-height or reduce/reflow the display type'
      );
    } else if (collision) {
      issues.push(`${name}: rendered text lines collide; increase line-height or reduce/reflow the display type`);
    }
  }

  const readableCount = record => Array.from(
    record.lines.map(line => line.text).join('').replace(/[\s\p{P}\p{S}]/gu, '')
  ).length;
  const opaqueStyle = (style, tag) => {
    const color = style.backgroundColor || '';
    const alphaMatch = color.match(/rgba?\([^)]*[,/]\s*([\d.]+)\s*\)$/i);
    const backgroundAlpha = color === 'transparent' ? 0 : (alphaMatch ? Number(alphaMatch[1]) : 1);
    return Number(style.opacity) > 0.05 && (
      backgroundAlpha > 0.08 || style.backgroundImage !== 'none'
      || ['IMG', 'SVG', 'CANVAS', 'VIDEO', 'IFRAME'].includes(tag)
    );
  };
  // Foreground inventory: real rects for every layer that can paint over text, including the
  // absolutely positioned pseudo-elements decks use for dots, rules, and badges.
  const pseudoLength = value => {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const pseudoBoxes = (element, hostRect, hostStyle) => {
    if (hostStyle.position === 'static' || hostStyle.transform !== 'none') return [];
    const boxes = [];
    for (const selector of ['::before', '::after']) {
      let pseudo = null;
      try {
        pseudo = getComputedStyle(element, selector);
      } catch (_error) {
        pseudo = null;
      }
      if (!pseudo) continue;
      const content = pseudo.content;
      if (!content || content === 'none' || content === 'normal') continue;
      if (pseudo.position !== 'absolute') continue;
      const borderWidth = Math.max(
        pseudoLength(pseudo.borderTopWidth) || 0, pseudoLength(pseudo.borderRightWidth) || 0,
        pseudoLength(pseudo.borderBottomWidth) || 0, pseudoLength(pseudo.borderLeftWidth) || 0
      );
      if (!opaqueStyle(pseudo, '') && borderWidth < 2) continue;
      const width = pseudoLength(pseudo.width);
      const height = pseudoLength(pseudo.height);
      if (width === null || height === null || width <= 0 || height <= 0) continue;
      const padLeft = hostRect.left + scaled(pseudoLength(hostStyle.borderLeftWidth) || 0);
      const padRight = hostRect.right - scaled(pseudoLength(hostStyle.borderRightWidth) || 0);
      const padTop = hostRect.top + scaled(pseudoLength(hostStyle.borderTopWidth) || 0);
      const padBottom = hostRect.bottom - scaled(pseudoLength(hostStyle.borderBottomWidth) || 0);
      const left = pseudoLength(pseudo.left);
      const right = pseudoLength(pseudo.right);
      const top = pseudoLength(pseudo.top);
      const bottom = pseudoLength(pseudo.bottom);
      const x = left !== null ? padLeft + scaled(left)
        : (right !== null ? padRight - scaled(right + width) : null);
      const y = top !== null ? padTop + scaled(top)
        : (bottom !== null ? padBottom - scaled(bottom + height) : null);
      if (x === null || y === null) continue;
      boxes.push({
        host: element,
        rect: { left: x, top: y, right: x + scaled(width), bottom: y + scaled(height) },
      });
    }
    return boxes;
  };

  // A hairline rule or a framed decoration paints only in its border bands; using the whole border
  // box would flag every text block that merely sits inside a frame. Emit the bands themselves.
  const borderBands = (element, rect, style) => {
    if (style.transform !== 'none') return [];
    const bands = [];
    const edges = [
      ['Top', () => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.top })],
      ['Bottom', () => ({ left: rect.left, right: rect.right, top: rect.bottom, bottom: rect.bottom })],
      ['Left', () => ({ left: rect.left, right: rect.left, top: rect.top, bottom: rect.bottom })],
      ['Right', () => ({ left: rect.right, right: rect.right, top: rect.top, bottom: rect.bottom })],
    ];
    for (const [edge, box] of edges) {
      const width = pseudoLength(style[`border${edge}Width`]) || 0;
      const styleName = style[`border${edge}Style`];
      const color = style[`border${edge}Color`] || '';
      const alphaMatch = color.match(/rgba?\([^)]*[,/]\s*([\d.]+)\s*\)$/i);
      const alpha = color === 'transparent' ? 0 : (alphaMatch ? Number(alphaMatch[1]) : 1);
      if (width < 1 || styleName === 'none' || styleName === 'hidden' || alpha <= 0.08) continue;
      const band = box();
      const thickness = scaled(width);
      if (edge === 'Top') band.bottom = band.top + thickness;
      if (edge === 'Bottom') band.top = band.bottom - thickness;
      if (edge === 'Left') band.right = band.left + thickness;
      if (edge === 'Right') band.left = band.right - thickness;
      bands.push({ host: element, rect: band });
    }
    return bands;
  };

  const foreground = [];
  for (const element of active.querySelectorAll('*')) {
    if (element.closest('[data-text-bounds-ignore]')) continue;
    const tag = element.tagName.toUpperCase();
    if (element.namespaceURI !== 'http://www.w3.org/1999/xhtml') {
      if (tag === 'SVG' && visible(element)) {
        foreground.push({ host: element, rect: element.getBoundingClientRect() });
      }
      continue;
    }
    if (!visible(element)) continue;
    const style = styleOf(element);
    const rect = element.getBoundingClientRect();
    if (opaqueStyle(style, tag)) foreground.push({ host: element, rect });
    else for (const band of borderBands(element, rect, style)) foreground.push(band);
    for (const box of pseudoBoxes(element, rect, style)) foreground.push(box);
  }

  const stackCache = new Map();
  const stackAt = (x, y) => {
    const key = `${Math.round(x * 4)}:${Math.round(y * 4)}`;
    let stack = stackCache.get(key);
    if (!stack) {
      stack = document.elementsFromPoint(x, y);
      stackCache.set(key, stack);
    }
    return stack;
  };
  // Rect math decides WHETHER two layers share pixels; a hit test inside the shared pixels decides
  // WHICH one paints on top. Point sampling is only used for the z-order question it can answer.
  const paintsAbove = (candidate, record, region) => {
    const points = [
      [(region.left + region.right) / 2, (region.top + region.bottom) / 2],
      [region.left + (region.right - region.left) * 0.2, (region.top + region.bottom) / 2],
      [region.left + (region.right - region.left) * 0.8, (region.top + region.bottom) / 2],
    ];
    for (const [x, y] of points) {
      if (!(x >= 0 && y >= 0 && x < viewportWidth && y < viewportHeight)) continue;
      const stack = stackAt(x, y);
      const ownerIndex = stack.findIndex(node => (
        node === record.element || node.contains(record.element) || record.element.contains(node)
      ));
      if (ownerIndex <= 0) continue;
      const candidateIndex = stack.findIndex(node => node === candidate || candidate.contains(node));
      if (candidateIndex >= 0 && candidateIndex < ownerIndex) return true;
    }
    return false;
  };

  for (const record of lineRecords) {
    const exempt = record.element.closest('[data-occlusion-ok]');
    let occluded = false;
    let worst = 0;
    for (const line of record.lines) {
      if (occluded) break;
      if (!line.inked) continue;
      const inkRect = { left: line.inkLeft, right: line.inkRight, top: line.inkTop, bottom: line.inkBottom };
      for (const layer of foreground) {
        if (occluded) break;
        const host = layer.host;
        if (host === record.element || host.contains(record.element) || record.element.contains(host)) continue;
        // Cheap line-level bounding-box reject before any per-glyph work.
        if (!overlaps(inkRect, layer.rect)) continue;
        let bite = 0;
        let region = null;
        for (const glyph of line.glyphs) {
          if (!glyph.hasInk) continue;
          const glyphRect = {
            left: glyph.inkLeft, right: glyph.inkRight, top: glyph.inkTop, bottom: glyph.inkBottom,
          };
          if (!overlaps(glyphRect, layer.rect)) continue;
          const area = intersection(glyphRect, layer.rect);
          // Depth of the intrusion, not its area: a vertical image edge cutting 2px into a glyph is
          // as much a defect as a panel covering the whole line.
          const depth = logical(Math.min(area.width, area.height));
          if (depth > bite) {
            bite = depth;
            region = {
              left: Math.max(glyphRect.left, layer.rect.left),
              right: Math.min(glyphRect.right, layer.rect.right),
              top: Math.max(glyphRect.top, layer.rect.top),
              bottom: Math.min(glyphRect.bottom, layer.rect.bottom),
            };
          }
        }
        if (bite < foregroundBiteTolerance || !region) continue;
        if (!paintsAbove(host, record, region)) continue;
        occluded = true;
        worst = Math.max(worst, bite);
      }
    }
    if (!occluded) continue;
    if (exempt) warnings.push(`${label(record.element)}: intentional occlusion exemption requires visual inspection`);
    else {
      issues.push(
        `${label(record.element)}: rendered text is covered by an opaque visual layer `
        + `(${Math.round(worst * 10) / 10}px of glyph ink)`
      );
    }
  }
  for (const record of lineRecords) {
    if (record.element.closest('[data-text-overlap-ok]')) {
      warnings.push(`${label(record.element)}: intentional text-overlap exemption requires visual inspection`);
    }
  }
  for (let leftIndex = 0; leftIndex < lineRecords.length; leftIndex += 1) {
    const leftRecord = lineRecords[leftIndex];
    for (let rightIndex = leftIndex + 1; rightIndex < lineRecords.length; rightIndex += 1) {
      const rightRecord = lineRecords[rightIndex];
      const leftElement = leftRecord.element;
      const rightElement = rightRecord.element;
      if (leftElement.contains(rightElement) || rightElement.contains(leftElement)) continue;
      if (leftElement.closest('[data-text-overlap-ok]') || rightElement.closest('[data-text-overlap-ok]')) continue;
      if (readableCount(leftRecord) <= 1 || readableCount(rightRecord) <= 1) continue;
      if (!overlaps(leftRecord.rect, rightRecord.rect)) continue;
      const collides = leftRecord.lines.some(leftLine => rightRecord.lines.some(rightLine => {
        const area = intersection(leftLine, rightLine);
        const verticalRatio = area.height / Math.max(1, Math.min(leftLine.height, rightLine.height));
        const horizontalRatio = area.width / Math.max(1, Math.min(leftLine.width, rightLine.width));
        if (area.width > 4 && area.height > 4 && verticalRatio > 0.35 && horizontalRatio > 0.12) return true;
        if (!leftLine.inked || !rightLine.inked) return false;
        // Ink-level check for the near-miss case the ratio test cannot see: two blocks whose
        // glyphs actually touch even though their line boxes barely overlap.
        const upper = leftLine.inkTop <= rightLine.inkTop ? leftLine : rightLine;
        const lower = upper === leftLine ? rightLine : leftLine;
        const upperColumns = columnsOf(upper);
        const lowerColumns = columnsOf(lower);
        const [small, fromUpper] = upperColumns.size <= lowerColumns.size
          ? [upperColumns, true] : [lowerColumns, false];
        for (const [key, bucket] of small) {
          const other = (fromUpper ? lowerColumns : upperColumns).get(key);
          if (!other) continue;
          const upperBottom = fromUpper ? bucket.bottom : other.bottom;
          const lowerTop = fromUpper ? other.top : bucket.top;
          if (logical(upperBottom - lowerTop) >= inkCollisionTolerance) return true;
        }
        return false;
      }));
      if (collides) {
        issues.push(`${label(leftElement)} / ${label(rightElement)}: rendered text regions overlap`);
      }
    }
  }

  const nav = document.querySelector('.nav');
  if (nav && visible(nav)) {
    const navRect = nav.getBoundingClientRect();
    for (const record of lineRecords) {
      const covered = record.lines.some(line => {
        const area = intersection(line, navRect);
        return area.width > 4 && area.height > 4
          && area.height / Math.max(1, line.height) > 0.15;
      });
      if (covered) issues.push(`${label(record.element)}: rendered text is covered by navigation controls`);
    }
  }

  return {
    ok: issues.length === 0,
    checked: elements.length,
    line_checks: lineRecords.length,
    ink_metrics: fontBoxCache.size > 0 && [...fontBoxCache.values()].some(Boolean),
    foreground_layers: foreground.length,
    issues: [...new Set(issues)],
    warnings: [...new Set(warnings)],
    elapsed_ms: elapsed(),
  };
})()
