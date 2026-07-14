(() => {
  const tolerance = 2;
  const active = document.querySelector('.slide.active');
  const issues = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'] };

  const visible = element => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
  };
  const label = element => {
    const explicit = element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id;
    const text = (element.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 56);
    return explicit || text || element.tagName.toLowerCase();
  };
  const outside = (inner, outer) => (
    inner.left < outer.left - tolerance || inner.right > outer.right + tolerance ||
    inner.top < outer.top - tolerance || inner.bottom > outer.bottom + tolerance
  );
  const selectors = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'dt', 'dd', 'td', 'th',
    'button', 'a', 'label', 'figcaption', 'blockquote', 'pre', 'code',
    '.eyebrow', '.kicker', '.caption', '.source', '.footnote', '.badge', '.chip',
    '[data-text-box]', '[data-text-container]'
  ].join(',');
  const slideRect = active.getBoundingClientRect();
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
  const elements = [...new Set(active.querySelectorAll(selectors))].filter(element => (
    visible(element) && (element.textContent || '').trim() && !element.hasAttribute('data-text-bounds-ignore')
  ));

  for (const element of elements) {
    const elementRect = element.getBoundingClientRect();
    const selfBoxTags = new Set(['BUTTON', 'TD', 'TH', 'PRE', 'CODE']);
    const semanticContainer = element.closest('[data-text-container], .card, .panel, .tile, .badge, .chip');
    const container = semanticContainer || (selfBoxTags.has(element.tagName) ? element : active);
    const containerRect = container.getBoundingClientRect();
    const name = label(element);
    const style = getComputedStyle(element);
    const clipsX = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX);
    const clipsY = ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY);

    if (outside(elementRect, slideRect)) issues.push(`${name}: element crosses active slide bounds`);
    if (clipsX && element.scrollWidth > element.clientWidth + tolerance) {
      issues.push(`${name}: horizontal text overflow ${element.scrollWidth - element.clientWidth}px`);
    }
    if (clipsY && element.scrollHeight > element.clientHeight + tolerance) {
      issues.push(`${name}: vertical text overflow ${element.scrollHeight - element.clientHeight}px`);
    }

    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: node => node.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT
    });
    while (walker.nextNode()) {
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      for (const rect of range.getClientRects()) {
        if (rect.width && rect.height && outside(rect, containerRect)) {
          issues.push(`${name}: rendered glyph bounds cross the intended text container`);
          break;
        }
      }
      range.detach();
    }
  }

  return { ok: issues.length === 0, checked: elements.length, issues: [...new Set(issues)] };
})()
