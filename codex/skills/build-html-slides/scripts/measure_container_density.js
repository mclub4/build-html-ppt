(() => {
  const active = document.querySelector('.slide.active');
  const warnings = [];
  const items = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings, items };

  const explicitSelector = '.card, .panel, .tile, .box, [data-density-container]';
  const excludedSelector = [
    '.slide-media',
    '.slide-content',
    '.nav',
    '.controls',
    '[data-runtime-control]',
    'img',
    'video',
    'canvas',
    'svg',
    'table',
    'pre',
    'script',
    'style',
  ].join(', ');
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
  };
  const alpha = color => {
    const match = color.match(/rgba?\((?:[^,]+,){3}\s*([\d.]+)\s*\)/i);
    if (match) return Number(match[1]);
    return color === 'transparent' ? 0 : 1;
  };
  const hasVisibleSurface = element => {
    const style = getComputedStyle(element);
    const borderWidth = ['Top', 'Right', 'Bottom', 'Left']
      .reduce((sum, side) => sum + (parseFloat(style[`border${side}Width`]) || 0), 0);
    return alpha(style.backgroundColor) > 0.04
      || style.backgroundImage !== 'none'
      || borderWidth > 0
      || style.boxShadow !== 'none'
      || (style.outlineStyle !== 'none' && (parseFloat(style.outlineWidth) || 0) > 0);
  };
  const intersect = (rect, outer) => {
    const left = Math.max(rect.left, outer.left);
    const right = Math.min(rect.right, outer.right);
    const top = Math.max(rect.top, outer.top);
    const bottom = Math.min(rect.bottom, outer.bottom);
    return right > left && bottom > top ? { left, right, top, bottom, width: right - left, height: bottom - top } : null;
  };
  const round = value => Math.round(value * 1000) / 1000;
  const label = (element, index) => (
    element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id
    || (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 48)
    || `container-${index + 1}`
  );

  const slideRect = active.getBoundingClientRect();
  const slideArea = slideRect.width * slideRect.height;
  const candidates = [...active.querySelectorAll('*')].filter(element => {
    if (!(element instanceof HTMLElement) || !visible(element)) return false;
    if (element.matches(excludedSelector) || element.closest('.nav, .controls, [data-runtime-control]')) return false;
    if (element.hasAttribute('data-density-ignore') || element.closest('[data-density-ignore]')) return false;
    return element.matches(explicitSelector) || hasVisibleSurface(element);
  });

  for (const [index, element] of candidates.entries()) {
    const rect = element.getBoundingClientRect();
    const area = rect.width * rect.height;
    const slideAreaRatio = area / Math.max(slideArea, 1);
    if (slideAreaRatio < 0.08 || rect.width < 220 || rect.height < 120) continue;

    const textRects = [];
    let textArea = 0;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
    });
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (!parent || !visible(parent)) continue;
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      for (const rawRect of range.getClientRects()) {
        const clipped = intersect(rawRect, rect);
        if (!clipped) continue;
        textRects.push(clipped);
        textArea += clipped.width * clipped.height;
      }
      range.detach();
    }

    let visualArea = 0;
    const visualRects = [];
    for (const visual of element.querySelectorAll('img, video, canvas, table, pre, .chart, .diagram, .key-visual, .ui-screenshot')) {
      if (!visible(visual)) continue;
      const clipped = intersect(visual.getBoundingClientRect(), rect);
      if (!clipped) continue;
      visualRects.push(clipped);
      visualArea += clipped.width * clipped.height;
    }

    const contentRects = [...textRects, ...visualRects];
    const contentTop = contentRects.length ? Math.min(...contentRects.map(item => item.top)) : rect.top;
    const contentBottom = contentRects.length ? Math.max(...contentRects.map(item => item.bottom)) : rect.top;
    const contentHeightRatio = (contentBottom - contentTop) / Math.max(rect.height, 1);
    const textAreaRatio = textArea / Math.max(area, 1);
    const visualAreaRatio = Math.min(1, visualArea / Math.max(area, 1));
    const text = (element.textContent || '').trim().replace(/\s+/g, ' ');
    const characterCount = [...text].length;
    const empty = characterCount === 0 && visualAreaRatio < 0.1;
    const sparseContent = characterCount <= 160
      && textAreaRatio < 0.14
      && visualAreaRatio < 0.1;
    const verySparseSurface = slideAreaRatio >= 0.12
      && characterCount <= 120
      && textAreaRatio < 0.1
      && visualAreaRatio < 0.1;
    const underfilled = sparseContent && (contentHeightRatio < 0.58 || verySparseSurface);

    const item = {
      name: label(element, index),
      candidateReason: element.matches(explicitSelector) ? 'explicit-container' : 'rendered-surface',
      slideAreaRatio: round(slideAreaRatio),
      characterCount,
      textAreaRatio: round(textAreaRatio),
      visualAreaRatio: round(visualAreaRatio),
      contentHeightRatio: round(contentHeightRatio),
      warning: empty || underfilled,
    };
    items.push(item);
    if (item.warning) {
      warnings.push(
        `${item.name}: oversized low-information container `
        + `(slide ${Math.round(slideAreaRatio * 100)}%, chars ${characterCount}, `
        + `content height ${Math.round(contentHeightRatio * 100)}%)`
      );
    }
  }

  const termNotes = [...active.querySelectorAll('[data-term-note]')].filter(visible);
  const citations = [...active.querySelectorAll(
    '[data-source-citation], .source-citation, .citation, .source'
  )].filter(element => visible(element) && !element.hasAttribute('data-term-note'));
  const runtimeControls = [...document.querySelectorAll('.nav, .controls, [data-runtime-control]')].filter(visible);
  const horizontalOverlap = (left, right) => Math.min(left.right, right.right) > Math.max(left.left, right.left);
  const verticalGap = (left, right) => Math.max(
    0,
    Math.max(left.top, right.top) - Math.min(left.bottom, right.bottom)
  );

  for (const [index, note] of termNotes.entries()) {
    const rect = note.getBoundingClientRect();
    const style = getComputedStyle(note);
    const noteAreaRatio = (rect.width * rect.height) / Math.max(slideArea, 1);
    const widthRatio = rect.width / Math.max(slideRect.width, 1);
    const heightRatio = rect.height / Math.max(slideRect.height, 1);
    const fontSize = parseFloat(style.fontSize) || 0;
    const padding = ['Top', 'Right', 'Bottom', 'Left']
      .reduce((sum, side) => sum + (parseFloat(style[`padding${side}`]) || 0), 0);
    const largeOpaqueSurface = alpha(style.backgroundColor) > 0.55
      && noteAreaRatio > 0.035
      && widthRatio > 0.25;
    const oversized = fontSize > 12.5
      || widthRatio > 0.42
      || heightRatio > 0.105
      || noteAreaRatio > 0.055
      || padding > 56
      || largeOpaqueSurface;
    if (oversized) {
      warnings.push(
        `${label(note, index)}: term note must remain a compact caption `
        + `(font ${round(fontSize)}px, width ${Math.round(widthRatio * 100)}%, `
        + `height ${Math.round(heightRatio * 100)}%)`
      );
    }

    for (const other of [...citations, ...runtimeControls]) {
      const otherRect = other.getBoundingClientRect();
      const overlap = intersect(rect, otherRect);
      const crowded = horizontalOverlap(rect, otherRect) && verticalGap(rect, otherRect) < 8;
      if (overlap || crowded) {
        warnings.push(
          `${label(note, index)}: term note overlaps or crowds a source citation or runtime control`
        );
        break;
      }
    }
  }

  return { ok: true, checked: items.length, issues: [], warnings: [...new Set(warnings)], items };
})()
