(() => {
  const active = document.querySelector('.slide.active');
  const warnings = [];
  const items = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings, items };

  const selector = '.card, .panel, .tile, .box, [data-density-container]';
  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
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
  const candidates = [...active.querySelectorAll(selector)].filter(element => (
    visible(element)
    && !element.hasAttribute('data-density-ignore')
    && !element.closest('[data-density-ignore]')
  ));

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
    const underfilled = characterCount <= 160
      && textAreaRatio < 0.14
      && contentHeightRatio < 0.58
      && visualAreaRatio < 0.1;

    const item = {
      name: label(element, index),
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

  return { ok: true, checked: items.length, issues: [], warnings: [...new Set(warnings)], items };
})()
