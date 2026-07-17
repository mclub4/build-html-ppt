(() => {
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
  return { ok: issues.length === 0, issues, ctas, nav: navMetrics, counter: counterMetrics };
})()
