(() => {
  const active = document.querySelector('.slide.active');
  const warnings = [];
  const items = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings, items };

  // Surface-independent region discovery. Framed cards are only one of the shapes an
  // author may use, so a region is any allocated layout area: an explicit container, a
  // painted surface, a grid/flex item, or a .slide-content subdivision. Thresholds below
  // are expressed in stage pixels (1280x720) and slide-area ratios so they survive the
  // stage transform.
  const MIN_REGION_SLIDE_RATIO = 0.07;
  const MIN_REGION_WIDTH_PX = 200;
  const MIN_REGION_HEIGHT_PX = 110;
  const INK_GRID_COLUMNS = 96;
  const INK_GRID_ROWS = 54;
  const DISPLAY_TYPE_PX = 40;
  const STATEMENT_DISPLAY_COVERAGE = 0.02;
  const EMPTY_VISUAL_COVERAGE = 0.06;
  const LOW_INK_COVERAGE = 0.1;
  const LOW_INK_CHARACTERS = 240;
  const BAND_INK_COVERAGE = 0.18;
  const BAND_EXTENT_RATIO = 0.5;
  const BAND_CHARACTERS = 400;
  const CARRIES_VISUAL_COVERAGE = 0.12;
  const SUBDIVISION_MAX_SLIDE_RATIO = 0.92;

  const explicitSelector = '.card, .panel, .tile, .box, [data-density-container]';
  const excludedSelector = [
    '.slide-media',
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
  const stageScale = (() => {
    const raw = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--stage-width'));
    const stage = document.querySelector('.stage');
    if (!stage || !Number.isFinite(raw) || raw <= 0) return 1;
    const width = stage.getBoundingClientRect().width;
    return width > 0 ? width / raw : 1;
  })();
  const isLayoutContainer = element => {
    if (!(element instanceof HTMLElement)) return false;
    const display = getComputedStyle(element).display;
    return display === 'flex' || display === 'grid'
      || display === 'inline-flex' || display === 'inline-grid';
  };
  const inFlow = element => {
    const position = getComputedStyle(element).position;
    return position !== 'absolute' && position !== 'fixed';
  };
  const candidateReason = element => {
    if (element.matches(explicitSelector)) return 'explicit-container';
    if (element.matches('.slide-content')) return 'content-region';
    if (hasVisibleSurface(element)) return 'rendered-surface';
    const parent = element.parentElement;
    if (parent && isLayoutContainer(parent) && inFlow(element)) return 'layout-item';
    if (parent && parent.matches('.slide-content, .slide')) return 'content-subdivision';
    return null;
  };

  const candidates = [];
  for (const element of active.querySelectorAll('*')) {
    if (!(element instanceof HTMLElement) || !visible(element)) continue;
    if (element.matches(excludedSelector)) continue;
    if (element.closest('.nav, .controls, [data-runtime-control], .slide-media')) continue;
    if (element.hasAttribute('data-density-ignore') || element.closest('[data-density-ignore]')) continue;
    const reason = candidateReason(element);
    if (!reason) continue;
    const rect = element.getBoundingClientRect();
    const slideAreaRatio = (rect.width * rect.height) / Math.max(slideArea, 1);
    if (slideAreaRatio < MIN_REGION_SLIDE_RATIO) continue;
    if (rect.width / stageScale < MIN_REGION_WIDTH_PX) continue;
    if (rect.height / stageScale < MIN_REGION_HEIGHT_PX) continue;
    candidates.push({ element, reason, rect, slideAreaRatio });
  }
  // Nested regions are never measured twice: only the innermost qualifying region for a
  // given area is measured, and every enclosing region is reported as an unmeasured group.
  for (const candidate of candidates) {
    candidate.leaf = !candidates.some(other => (
      other.element !== candidate.element && candidate.element.contains(other.element)
    ));
  }

  for (const [index, candidate] of candidates.entries()) {
    const { element, rect, slideAreaRatio } = candidate;
    if (!candidate.leaf) {
      items.push({
        name: label(element, index),
        candidateReason: candidate.reason,
        role: 'group',
        measured: false,
        slideAreaRatio: round(slideAreaRatio),
        warning: false,
      });
      continue;
    }

    // Union coverage on a fixed grid, so overlapping line boxes and images never inflate ink.
    const columns = INK_GRID_COLUMNS;
    const rows = INK_GRID_ROWS;
    const cellWidth = rect.width / columns;
    const cellHeight = rect.height / rows;
    const inkCells = new Uint8Array(columns * rows);
    const visualCells = new Uint8Array(columns * rows);
    const displayCells = new Uint8Array(columns * rows);
    const mark = (target, clipped) => {
      const startColumn = Math.max(0, Math.floor((clipped.left - rect.left) / Math.max(cellWidth, 0.001)));
      const endColumn = Math.min(columns - 1, Math.ceil((clipped.right - rect.left) / Math.max(cellWidth, 0.001)) - 1);
      const startRow = Math.max(0, Math.floor((clipped.top - rect.top) / Math.max(cellHeight, 0.001)));
      const endRow = Math.min(rows - 1, Math.ceil((clipped.bottom - rect.top) / Math.max(cellHeight, 0.001)) - 1);
      for (let row = startRow; row <= endRow; row += 1) {
        for (let column = startColumn; column <= endColumn; column += 1) target[row * columns + column] = 1;
      }
    };
    const coverage = target => {
      let filled = 0;
      for (let cell = 0; cell < target.length; cell += 1) filled += target[cell];
      return filled / target.length;
    };

    const contentRects = [];
    let maxTypePx = 0;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
    });
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (!parent || !visible(parent)) continue;
      const fontSize = Number.parseFloat(getComputedStyle(parent).fontSize) || 0;
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      for (const rawRect of range.getClientRects()) {
        const clipped = intersect(rawRect, rect);
        if (!clipped) continue;
        contentRects.push(clipped);
        mark(inkCells, clipped);
        if (fontSize >= DISPLAY_TYPE_PX) mark(displayCells, clipped);
      }
      range.detach();
      if (fontSize > maxTypePx) maxTypePx = fontSize;
    }

    for (const visual of element.querySelectorAll('img, video, canvas, table, pre, .chart, .diagram, .key-visual, .ui-screenshot')) {
      if (!visible(visual)) continue;
      const clipped = intersect(visual.getBoundingClientRect(), rect);
      if (!clipped) continue;
      contentRects.push(clipped);
      mark(inkCells, clipped);
      mark(visualCells, clipped);
    }

    const inkCoverage = coverage(inkCells);
    const visualCoverage = coverage(visualCells);
    const displayCoverage = coverage(displayCells);
    const contentTop = contentRects.length ? Math.min(...contentRects.map(item => item.top)) : rect.top;
    const contentBottom = contentRects.length ? Math.max(...contentRects.map(item => item.bottom)) : rect.top;
    const contentExtentRatio = (contentBottom - contentTop) / Math.max(rect.height, 1);
    const text = (element.textContent || '').trim().replace(/\s+/g, ' ');
    const characterCount = [...text].length;

    // Deliberate negative space is distinguished from an underfilled region by two
    // measurements, never by reviewer judgement: a statement composition carries
    // display-scale type that itself covers real area, and a media region carries a visual.
    const statementComposition = maxTypePx >= DISPLAY_TYPE_PX && displayCoverage >= STATEMENT_DISPLAY_COVERAGE;
    const carriesVisual = visualCoverage >= CARRIES_VISUAL_COVERAGE;
    // A region that is the whole slide has no oversized allocation to be judged against:
    // an empty or thin slide is a completion and story problem, reported by other gates.
    // Only a subdivision can be an oversized low-information container.
    const subdivision = slideAreaRatio <= SUBDIVISION_MAX_SLIDE_RATIO;
    const empty = characterCount === 0 && visualCoverage < EMPTY_VISUAL_COVERAGE;
    const lowInk = inkCoverage < LOW_INK_COVERAGE && characterCount <= LOW_INK_CHARACTERS;
    const thinBand = inkCoverage < BAND_INK_COVERAGE
      && contentExtentRatio < BAND_EXTENT_RATIO
      && characterCount <= BAND_CHARACTERS;
    const underfilled = !empty && !statementComposition && !carriesVisual && (lowInk || thinBand);

    const item = {
      name: label(element, index),
      candidateReason: candidate.reason,
      role: 'region',
      measured: true,
      slideAreaRatio: round(slideAreaRatio),
      characterCount,
      inkCoverage: round(inkCoverage),
      visualAreaRatio: round(visualCoverage),
      displayCoverage: round(displayCoverage),
      maxTypePx: round(maxTypePx),
      contentHeightRatio: round(contentExtentRatio),
      statementComposition,
      subdivision,
      warning: subdivision && (empty || underfilled),
    };
    items.push(item);
    if (item.warning) {
      warnings.push(
        `${item.name}: oversized low-information region `
        + `(slide ${Math.round(slideAreaRatio * 100)}%, ink ${Math.round(inkCoverage * 100)}%, `
        + `chars ${characterCount}, largest type ${Math.round(maxTypePx)}px, `
        + `content height ${Math.round(contentExtentRatio * 100)}%)`
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

  return {
    ok: true,
    checked: items.filter(item => item.measured).length,
    regions: items.filter(item => item.measured).length,
    groups: items.filter(item => item.measured === false).length,
    issues: [],
    warnings: [...new Set(warnings)],
    items,
  };
})()
