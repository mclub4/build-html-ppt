(() => {
  const NAV_EXCLUSION_FALLBACK_WIDTH = 280;
  const NAV_EXCLUSION_FALLBACK_HEIGHT = 84;
  const NAV_EXCLUSION_OVERLAP_TOLERANCE_PX = 1;
  const NAV_EXCLUSION_MARGIN_PX = 8;
  const FULL_BLEED_AREA_RATIO = 0.7;
  const CONTENT_SURFACE_AREA_RATIO = 0.06;
  const NAV_EXCLUSION_MAX_REPORTED = 5;
  const round = value => Math.round(value * 100) / 100;
  const issues = [];
  const viewport = window.visualViewport || {
    width: document.documentElement.clientWidth,
    height: document.documentElement.clientHeight
  };
  const ctas = [...document.querySelectorAll('.cta')].map((cta, index) => {
    const inner = cta.querySelector('.cta-inner');
    if (!inner) {
      issues.push(`CTA ${index + 1}: missing .cta-inner`);
      return { index: index + 1, missingInner: true };
    }
    const outer = cta.getBoundingClientRect();
    const content = inner.getBoundingClientRect();
    const dx = (content.left + content.width / 2) - (outer.left + outer.width / 2);
    const dy = (content.top + content.height / 2) - (outer.top + outer.height / 2);
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
      issues.push(`CTA ${index + 1}: combined content is off-center by ${round(dx)}px, ${round(dy)}px`);
    }
    return { index: index + 1, dx: round(dx), dy: round(dy), width: round(outer.width), height: round(outer.height) };
  });
  const nav = document.querySelector('.controls, .nav');
  const navRect = nav?.getBoundingClientRect();
  const visibleNavTitle = nav?.querySelector('.nav-title, .controls-title, [data-nav-title]');
  if (visibleNavTitle && !nav.hasAttribute('data-nav-title-ok') && visibleNavTitle.getClientRects().length) {
    issues.push('Persistent controls include visible slide title/subtitle text; remove it or mark an explicit data-nav-title-ok exception');
  }
  const counter = nav?.querySelector('.count, .pager');
  const counterRect = counter?.getBoundingClientRect();
  const counterParts = counter ? [
    ['current', counter.querySelector('#pageInput, .page-input')],
    ['separator', counter.querySelector('.page-separator, .pager-separator')],
    ['total', counter.querySelector('#total, .page-total')],
  ] : [];
  const counterMetrics = counterRect ? counterParts.map(([name, element]) => {
    if (!element) {
      issues.push(`Page counter is missing ${name} cell`);
      return { name, missing: true };
    }
    const rect = element.getBoundingClientRect();
    const dy = (rect.top + rect.height / 2) - (counterRect.top + counterRect.height / 2);
    if (Math.abs(dy) > 1.5) issues.push(`Page counter ${name} cell is off-center by ${round(dy)}px`);
    return { name, dy: round(dy), width: round(rect.width), height: round(rect.height) };
  }) : [];
  if (!counterRect) issues.push('Missing .count or .pager page counter');
  const navMetrics = navRect ? {
    width: round(navRect.width),
    height: round(navRect.height),
    right: round(viewport.width - navRect.right),
    bottom: round(viewport.height - navRect.bottom),
  } : null;
  if (!navRect) issues.push('Missing persistent .controls or .nav');
  if (navRect && (navRect.width < 180 || navRect.width > 260 || navRect.height < 44 || navRect.height > 56)) {
    issues.push(`Persistent controls are not compact: ${round(navRect.width)}×${round(navRect.height)}px; expected 180–260×44–56px`);
  }
  if (navRect && (viewport.width - navRect.right < 8 || viewport.width - navRect.right > 32 || viewport.height - navRect.bottom < 8 || viewport.height - navRect.bottom > 32)) {
    issues.push('Persistent controls are not placed within the 8–32px bottom-right inset');
  }

  // Deterministic navigation exclusion gate. The reserved area is the lower-right
  // --nav-exclusion-width x --nav-exclusion-height rectangle of the stage, mapped into
  // viewport coordinates through the stage transform, unioned with the real controls
  // rectangle plus an 8px breathing margin. Any rendered ink outside the controls
  // subtree that lands inside that rectangle is a blocking intrusion.
  const stage = document.querySelector('.stage');
  const stageRect = stage?.getBoundingClientRect();
  const rootStyle = getComputedStyle(document.documentElement);
  const customPx = (name, fallback) => {
    const value = Number.parseFloat(rootStyle.getPropertyValue(name));
    return Number.isFinite(value) && value > 0 ? value : fallback;
  };
  const exclusionWidth = customPx('--nav-exclusion-width', NAV_EXCLUSION_FALLBACK_WIDTH);
  const exclusionHeight = customPx('--nav-exclusion-height', NAV_EXCLUSION_FALLBACK_HEIGHT);
  const stageScale = stageRect && stageRect.width > 0
    ? stageRect.width / Math.max(customPx('--stage-width', 1280), 1)
    : 1;
  const zone = stageRect ? {
    left: stageRect.right - exclusionWidth * stageScale,
    top: stageRect.bottom - exclusionHeight * stageScale,
    right: stageRect.right,
    bottom: stageRect.bottom,
  } : {
    left: viewport.width - exclusionWidth,
    top: viewport.height - exclusionHeight,
    right: viewport.width,
    bottom: viewport.height,
  };
  if (navRect) {
    zone.left = Math.min(zone.left, navRect.left - NAV_EXCLUSION_MARGIN_PX);
    zone.top = Math.min(zone.top, navRect.top - NAV_EXCLUSION_MARGIN_PX);
    zone.right = Math.max(zone.right, navRect.right);
    zone.bottom = Math.max(zone.bottom, navRect.bottom);
  }

  const activeSlide = document.querySelector('.slide.active');
  const controlSelector = '.nav, .controls, [data-runtime-control], .edge, .progress, .slide-media';
  const optOutSelector = '[data-nav-exclusion-ok]';
  const inkVisible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0.05 && rect.width > 0 && rect.height > 0;
  };
  const inkExcluded = element => (
    !(element instanceof Element)
    || element.closest(controlSelector) !== null
    || element.closest(optOutSelector) !== null
  );
  const inkAlpha = color => {
    const match = String(color).match(/rgba?\((?:[^,]+,){3}\s*([\d.]+)\s*\)/i);
    if (match) return Number(match[1]);
    return color === 'transparent' ? 0 : 1;
  };
  const paintedSurface = element => {
    const style = getComputedStyle(element);
    const borderWidth = ['Top', 'Right', 'Bottom', 'Left']
      .reduce((sum, side) => sum + (Number.parseFloat(style[`border${side}Width`]) || 0), 0);
    return inkAlpha(style.backgroundColor) > 0.04
      || style.backgroundImage !== 'none'
      || borderWidth > 0
      || style.boxShadow !== 'none';
  };
  const inkLabel = element => (
    element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id
    || (element.className && typeof element.className === 'string'
      ? `.${element.className.trim().split(/\s+/).slice(0, 2).join('.')}` : '')
    || (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    || element.tagName.toLowerCase()
  );
  const inkRects = [];
  if (activeSlide) {
    const areaRect = stageRect || activeSlide.getBoundingClientRect();
    const slideArea = Math.max(areaRect.width * areaRect.height, 1);
    const walker = document.createTreeWalker(activeSlide, NodeFilter.SHOW_TEXT, {
      acceptNode: node => (node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
    });
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (!parent || inkExcluded(parent) || !inkVisible(parent)) continue;
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      for (const rect of range.getClientRects()) {
        if (rect.width > 0 && rect.height > 0) inkRects.push({ owner: parent, rect, kind: 'text' });
      }
      range.detach();
    }
    for (const element of activeSlide.querySelectorAll('img, video, canvas, svg, table, pre')) {
      if (inkExcluded(element) || !inkVisible(element)) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width * rect.height >= slideArea * FULL_BLEED_AREA_RATIO) continue;
      inkRects.push({ owner: element, rect, kind: 'media' });
    }
    // A large painted block is layout background: the floating controls are meant to sit on
    // top of it. Only content-scale surfaces — badges, chips, rules, logo plates — are ink.
    for (const element of activeSlide.querySelectorAll('*')) {
      if (inkExcluded(element) || !inkVisible(element) || !paintedSurface(element)) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width * rect.height > slideArea * CONTENT_SURFACE_AREA_RATIO) continue;
      inkRects.push({ owner: element, rect, kind: 'surface' });
    }
  }
  const intrusionsByOwner = new Map();
  for (const entry of inkRects) {
    const overlapWidth = Math.min(entry.rect.right, zone.right) - Math.max(entry.rect.left, zone.left);
    const overlapHeight = Math.min(entry.rect.bottom, zone.bottom) - Math.max(entry.rect.top, zone.top);
    if (overlapWidth <= NAV_EXCLUSION_OVERLAP_TOLERANCE_PX || overlapHeight <= NAV_EXCLUSION_OVERLAP_TOLERANCE_PX) continue;
    const name = inkLabel(entry.owner);
    const previous = intrusionsByOwner.get(name);
    const candidate = {
      name,
      kind: entry.kind,
      overlapWidth: round(overlapWidth),
      overlapHeight: round(overlapHeight),
      overlapArea: round(overlapWidth * overlapHeight),
    };
    if (!previous || candidate.overlapArea > previous.overlapArea) intrusionsByOwner.set(name, candidate);
  }
  const intrusions = [...intrusionsByOwner.values()]
    .sort((left, right) => right.overlapArea - left.overlapArea);
  for (const intrusion of intrusions.slice(0, NAV_EXCLUSION_MAX_REPORTED)) {
    issues.push(
      `${intrusion.name}: ${intrusion.kind} intrudes ${intrusion.overlapWidth}×${intrusion.overlapHeight}px `
      + `into the reserved lower-right navigation exclusion zone `
      + `(${round(exclusionWidth)}×${round(exclusionHeight)}px stage area); `
      + `move it out or mark an explicit data-nav-exclusion-ok exception`
    );
  }
  const navExclusion = {
    width: round(exclusionWidth),
    height: round(exclusionHeight),
    source: Number.isFinite(Number.parseFloat(rootStyle.getPropertyValue('--nav-exclusion-width')))
      ? 'css-variable' : 'documented-fallback',
    zone: {
      left: round(zone.left), top: round(zone.top), right: round(zone.right), bottom: round(zone.bottom),
    },
    inspected: inkRects.length,
    intrusions,
  };

  return { ok: issues.length === 0, issues, ctas, nav: navMetrics, counter: counterMetrics, navExclusion };
})()
