(() => {
  // Contrast is measured, never delegated on a hunch. When the ancestor chain resolves an
  // opaque background the ratio is exact. When it does not, the real paint stack under each
  // text line is walked: image pixels are sampled, gradient stops are bounded componentwise,
  // and anything still unknown is bounded by pure black and pure white. That yields a
  // provable [worst, best] contrast interval. Only an interval that straddles the required
  // ratio is handed to a reviewer, and that hand-off demands a CONFIRM/REFUTE observation.
  const SAMPLE_LINES = 4;
  const SAMPLE_COLUMNS = [0.15, 0.5, 0.85];
  const OPAQUE_ALPHA = 0.999;
  const IMAGE_SAMPLE_MAX_EDGE = 512;
  const active = document.querySelector('.slide.active');
  const issues = [];
  const warnings = [];
  const items = [];
  if (!active) return { ok: false, checked: 0, deferred: 0, issues: ['Missing active slide'], warnings, items };

  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
  };
  const directText = element => [...element.childNodes].some(node => (
    node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()
  ));
  const label = element => (
    element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id
    || (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 56)
    || element.tagName.toLowerCase()
  );
  const parseColor = value => {
    const match = String(value).match(/rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+))?\s*\)/i);
    if (!match) return null;
    return {
      r: Number(match[1]), g: Number(match[2]), b: Number(match[3]),
      a: match[4] === undefined ? 1 : Number(match[4]),
    };
  };
  const composite = (foreground, background) => {
    const alpha = foreground.a + background.a * (1 - foreground.a);
    if (!alpha) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: (foreground.r * foreground.a + background.r * background.a * (1 - foreground.a)) / alpha,
      g: (foreground.g * foreground.a + background.g * background.a * (1 - foreground.a)) / alpha,
      b: (foreground.b * foreground.a + background.b * background.a * (1 - foreground.a)) / alpha,
      a: alpha,
    };
  };
  const luminance = color => {
    const channel = value => {
      const normalized = value / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
  };
  const contrast = (left, right) => {
    const first = luminance(left);
    const second = luminance(right);
    return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
  };
  const overlaps = (left, right) => (
    Math.min(left.right, right.right) > Math.max(left.left, right.left)
    && Math.min(left.bottom, right.bottom) > Math.max(left.top, right.top)
  );
  const round = value => Math.round(value * 100) / 100;
  const BLACK = { r: 0, g: 0, b: 0, a: 1 };
  const WHITE = { r: 255, g: 255, b: 255, a: 1 };
  const EXTREMES = [BLACK, WHITE];
  // A per-channel blend of solid stops stays between the componentwise minimum and maximum
  // stop, and relative luminance is monotone in every channel, so those two corners bound
  // the luminance of every pixel the gradient can paint.
  const gradientBounds = value => {
    if (/url\(/i.test(value)) return null;
    const stops = [...String(value).matchAll(/rgba?\([^)]*\)/gi)]
      .map(match => parseColor(match[0]))
      .filter(color => color && color.a >= OPAQUE_ALPHA);
    if (!stops.length) return null;
    const corner = pick => ({
      r: pick(stops.map(stop => stop.r)),
      g: pick(stops.map(stop => stop.g)),
      b: pick(stops.map(stop => stop.b)),
      a: 1,
    });
    return [corner(values => Math.min(...values)), corner(values => Math.max(...values))];
  };

  const canvasCache = new WeakMap();
  const imageCanvas = image => {
    if (canvasCache.has(image)) return canvasCache.get(image);
    let entry = null;
    try {
      const naturalWidth = image.naturalWidth;
      const naturalHeight = image.naturalHeight;
      if (image.complete && naturalWidth > 0 && naturalHeight > 0) {
        const scale = Math.min(1, IMAGE_SAMPLE_MAX_EDGE / Math.max(naturalWidth, naturalHeight));
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(naturalHeight * scale));
        const context = canvas.getContext('2d', { willReadFrequently: true });
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        context.getImageData(0, 0, 1, 1);
        entry = { canvas, context, naturalWidth, naturalHeight };
      }
    } catch (error) {
      entry = null;
    }
    canvasCache.set(image, entry);
    return entry;
  };
  const samplePixel = (image, x, y) => {
    const style = getComputedStyle(image);
    if (style.filter !== 'none' || Number(style.opacity) < OPAQUE_ALPHA || style.mixBlendMode !== 'normal') return null;
    const entry = imageCanvas(image);
    if (!entry) return null;
    const rect = image.getBoundingClientRect();
    const { naturalWidth, naturalHeight } = entry;
    const fit = style.objectFit;
    let drawnWidth = rect.width;
    let drawnHeight = rect.height;
    if (fit === 'contain' || fit === 'scale-down') {
      const limit = fit === 'scale-down' ? 1 : Number.POSITIVE_INFINITY;
      const scale = Math.min(rect.width / naturalWidth, rect.height / naturalHeight, limit);
      drawnWidth = naturalWidth * scale;
      drawnHeight = naturalHeight * scale;
    } else if (fit === 'cover') {
      const scale = Math.max(rect.width / naturalWidth, rect.height / naturalHeight);
      drawnWidth = naturalWidth * scale;
      drawnHeight = naturalHeight * scale;
    } else if (fit === 'none') {
      drawnWidth = naturalWidth;
      drawnHeight = naturalHeight;
    }
    const [rawX, rawY] = String(style.objectPosition).trim().split(/\s+/);
    const offset = (raw, free) => {
      if (raw === undefined) return free / 2;
      const value = Number.parseFloat(raw);
      if (!Number.isFinite(value)) return free / 2;
      return raw.endsWith('%') ? (value / 100) * free : value;
    };
    const originX = rect.left + offset(rawX, rect.width - drawnWidth);
    const originY = rect.top + offset(rawY, rect.height - drawnHeight);
    const imageX = ((x - originX) / Math.max(drawnWidth, 0.001)) * naturalWidth;
    const imageY = ((y - originY) / Math.max(drawnHeight, 0.001)) * naturalHeight;
    if (imageX < 0 || imageY < 0 || imageX >= naturalWidth || imageY >= naturalHeight) return null;
    const canvasX = Math.min(entry.canvas.width - 1, Math.floor((imageX / naturalWidth) * entry.canvas.width));
    const canvasY = Math.min(entry.canvas.height - 1, Math.floor((imageY / naturalHeight) * entry.canvas.height));
    try {
      const data = entry.context.getImageData(canvasX, canvasY, 1, 1).data;
      if (data[3] < 250) return null;
      return { r: data[0], g: data[1], b: data[2], a: 1 };
    } catch (error) {
      return null;
    }
  };

  let hitTestStyle = null;
  const enableHitTesting = () => {
    if (hitTestStyle) return;
    hitTestStyle = document.createElement('style');
    hitTestStyle.textContent = '*, *::before, *::after { pointer-events: auto !important; }';
    document.head.appendChild(hitTestStyle);
  };
  const disableHitTesting = () => {
    if (hitTestStyle && hitTestStyle.parentNode) hitTestStyle.parentNode.removeChild(hitTestStyle);
    hitTestStyle = null;
  };

  // Walks the real paint stack below one point and returns the semi-transparent layers plus
  // the one or two base colours that bound whatever sits underneath them.
  const backdropAt = (x, y, textElement) => {
    const stack = document.elementsFromPoint(x, y);
    const start = stack.indexOf(textElement);
    if (start < 0) {
      return { layers: [], bases: EXTREMES, cause: 'a paint stack that does not expose the text box' };
    }
    const layers = [];
    for (let index = start; index < stack.length; index += 1) {
      const element = stack[index];
      if (!(element instanceof Element)) continue;
      const style = getComputedStyle(element);
      if (index !== start && (
        Number(style.opacity) < OPAQUE_ALPHA
        || style.mixBlendMode !== 'normal'
        || style.filter !== 'none'
      )) {
        return { layers, bases: EXTREMES, cause: 'a translucent, filtered, or blended layer behind the text' };
      }
      const tag = element.tagName.toLowerCase();
      if (tag === 'img' || tag === 'canvas' || tag === 'video' || tag === 'svg') {
        const sampled = tag === 'img' ? samplePixel(element, x, y) : null;
        if (sampled) return { layers, bases: [sampled], cause: 'sampled image pixels' };
        return { layers, bases: EXTREMES, cause: `an overlapping <${tag}> whose pixels cannot be sampled` };
      }
      if (style.backgroundImage !== 'none') {
        const bounds = gradientBounds(style.backgroundImage);
        if (bounds) return { layers, bases: bounds, cause: 'gradient stop bounds' };
        return { layers, bases: EXTREMES, cause: 'a background image that cannot be sampled' };
      }
      const color = parseColor(style.backgroundColor);
      if (color && color.a > 0) {
        layers.push(color);
        if (color.a >= OPAQUE_ALPHA) return { layers, bases: [color], cause: 'an opaque painted background' };
      }
    }
    return { layers, bases: EXTREMES, cause: 'no opaque backdrop below the text' };
  };

  const flatten = (layers, base) => {
    let result = { ...base, a: 1 };
    for (let index = layers.length - 1; index >= 0; index -= 1) result = composite(layers[index], result);
    return result;
  };
  const lineRects = element => {
    const rects = [];
    for (const node of element.childNodes) {
      if (node.nodeType !== Node.TEXT_NODE || !node.nodeValue.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width > 1 && rect.height > 1) rects.push(rect);
      }
      range.detach();
    }
    return rects;
  };
  const samplePoints = rects => {
    if (!rects.length) return [];
    const step = Math.max(1, Math.ceil(rects.length / SAMPLE_LINES));
    const points = [];
    for (let index = 0; index < rects.length; index += step) {
      const rect = rects[index];
      for (const fraction of SAMPLE_COLUMNS) {
        points.push({ x: rect.left + rect.width * fraction, y: rect.top + rect.height * 0.5 });
      }
    }
    return points;
  };

  const complexVisuals = [...active.querySelectorAll('img, video, canvas, svg image')].filter(visible);
  const textElements = [...active.querySelectorAll('*')].filter(element => (
    element.namespaceURI === 'http://www.w3.org/1999/xhtml'
    && directText(element) && visible(element) && !element.closest('[data-contrast-ignore]')
  ));

  try {
    for (const element of textElements) {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const name = label(element);
      const foreground = parseColor(style.color);
      const size = Number.parseFloat(style.fontSize) || 0;
      const weight = Number.parseInt(style.fontWeight, 10) || 400;
      const large = size >= 24 || (size >= 18.66 && weight >= 700);
      const required = large ? 3 : 4.5;
      if (!foreground) {
        warnings.push(
          `${name}: UNDECIDABLE contrast — the text colour "${style.color}" could not be parsed, so no ratio exists. `
          + `Reviewer MUST open the full-size capture and either CONFIRM or REFUTE a legibility problem for this text `
          + `with a location-specific observation naming the text and what sits behind it; `
          + `"looks fine", "intentional", or a restatement of this warning is not an accepted answer.`
        );
        items.push({ name, status: 'undecidable', reason: 'unparsed text color', required });
        continue;
      }

      let owner = element;
      let background = null;
      let chainReason = '';
      while (owner && active.contains(owner)) {
        const ownerStyle = getComputedStyle(owner);
        if (ownerStyle.backgroundImage && ownerStyle.backgroundImage !== 'none') {
          chainReason = 'gradient or background image';
          break;
        }
        const candidate = parseColor(ownerStyle.backgroundColor);
        if (candidate && candidate.a >= 0.98) {
          background = candidate;
          break;
        }
        if (Number(ownerStyle.opacity) < 0.98 || ownerStyle.mixBlendMode !== 'normal') {
          chainReason = 'opacity or blend mode';
          break;
        }
        if (owner === active) break;
        owner = owner.parentElement;
      }
      const overlappingVisual = complexVisuals.some(visual => overlaps(rect, visual.getBoundingClientRect()));
      const chainResolved = !chainReason && background && !(owner === active && overlappingVisual);

      if (chainResolved) {
        const effectiveForeground = foreground.a < 1 ? composite(foreground, background) : foreground;
        const ratio = contrast(effectiveForeground, background);
        const rounded = round(ratio);
        const passed = ratio >= required;
        items.push({
          name,
          status: passed ? 'pass' : 'fail',
          method: 'resolved-background',
          ratio: rounded,
          required,
          fontSize: size,
          fontWeight: weight,
          textShadow: style.textShadow !== 'none',
        });
        if (!passed) {
          issues.push(`${name}: text contrast ${rounded}:1 is below the required ${required}:1`);
        }
        continue;
      }

      enableHitTesting();
      const rects = lineRects(element);
      const points = samplePoints(rects);
      let worst = Number.POSITIVE_INFINITY;
      let best = 0;
      const causes = new Set();
      let worstPoint = null;
      for (const point of points) {
        const backdrop = backdropAt(point.x, point.y, element);
        causes.add(backdrop.cause);
        for (const base of backdrop.bases) {
          const backgroundColor = flatten(backdrop.layers, base);
          const effectiveForeground = foreground.a < 1 ? composite(foreground, backgroundColor) : foreground;
          const ratio = contrast(effectiveForeground, backgroundColor);
          if (ratio < worst) {
            worst = ratio;
            worstPoint = point;
          }
          if (ratio > best) best = ratio;
        }
      }
      const cause = [...causes].join(', ') || (chainReason || 'an unresolved background');
      const location = `x ${Math.round(rect.left)}, y ${Math.round(rect.top)} `
        + `(${Math.round(rect.width)}×${Math.round(rect.height)}px)`;

      if (!points.length) {
        warnings.push(
          `${name}: UNDECIDABLE contrast over ${cause} — the text produced no measurable line box at ${location}. `
          + `Reviewer MUST open the full-size capture and either CONFIRM or REFUTE this overlap with a `
          + `location-specific observation naming what sits behind the text at that position; `
          + `"looks fine", "intentional", or a restatement of this warning is not an accepted answer.`
        );
        items.push({ name, status: 'undecidable', reason: cause, required, location });
        continue;
      }

      const roundedWorst = round(worst);
      const roundedBest = round(best);
      if (worst >= required) {
        items.push({
          name,
          status: 'pass',
          method: 'measured-backdrop',
          ratio: roundedWorst,
          worstRatio: roundedWorst,
          bestRatio: roundedBest,
          required,
          fontSize: size,
          fontWeight: weight,
          reason: cause,
          samples: points.length,
        });
        continue;
      }
      if (best < required) {
        items.push({
          name,
          status: 'fail',
          method: 'measured-backdrop',
          ratio: roundedBest,
          worstRatio: roundedWorst,
          bestRatio: roundedBest,
          required,
          fontSize: size,
          fontWeight: weight,
          reason: cause,
          samples: points.length,
        });
        issues.push(
          `${name}: text contrast is at most ${roundedBest}:1 against every backdrop this text can sit on `
          + `(${cause}) at ${location}, below the required ${required}:1`
        );
        continue;
      }
      const worstLocation = worstPoint
        ? `x ${Math.round(worstPoint.x)}, y ${Math.round(worstPoint.y)}`
        : location;
      warnings.push(
        `${name}: UNDECIDABLE contrast over ${cause} — measured range ${roundedWorst}:1 to ${roundedBest}:1 `
        + `across ${points.length} sampled points, required ${required}:1, worst point at ${worstLocation}. `
        + `Reviewer MUST open the full-size capture and either CONFIRM or REFUTE this overlap with a `
        + `location-specific observation naming what sits behind the text at that position; `
        + `"looks fine", "intentional", or a restatement of this warning is not an accepted answer.`
      );
      items.push({
        name,
        status: 'undecidable',
        method: 'measured-backdrop',
        worstRatio: roundedWorst,
        bestRatio: roundedBest,
        required,
        fontSize: size,
        fontWeight: weight,
        reason: cause,
        location: worstLocation,
        samples: points.length,
      });
    }
  } finally {
    disableHitTesting();
  }

  const undecidable = items.filter(item => item.status === 'undecidable');
  return {
    ok: issues.length === 0,
    checked: items.filter(item => item.status !== 'undecidable').length,
    deferred: undecidable.length,
    undecidable: undecidable.length,
    issues: [...new Set(issues)],
    warnings: [...new Set(warnings)],
    items,
  };
})()
