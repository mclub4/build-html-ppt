(() => {
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
  const complexVisuals = [...active.querySelectorAll('img, video, canvas, svg image')].filter(visible);
  const textElements = [...active.querySelectorAll('*')].filter(element => (
    element.namespaceURI === 'http://www.w3.org/1999/xhtml'
    && directText(element) && visible(element) && !element.closest('[data-contrast-ignore]')
  ));

  for (const element of textElements) {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const name = label(element);
    let owner = element;
    let background = null;
    let reason = '';
    while (owner && active.contains(owner)) {
      const ownerStyle = getComputedStyle(owner);
      if (ownerStyle.backgroundImage && ownerStyle.backgroundImage !== 'none') {
        reason = 'gradient or background image';
        break;
      }
      const candidate = parseColor(ownerStyle.backgroundColor);
      if (candidate && candidate.a >= 0.98) {
        background = candidate;
        break;
      }
      if (Number(ownerStyle.opacity) < 0.98 || ownerStyle.mixBlendMode !== 'normal') {
        reason = 'opacity or blend mode';
        break;
      }
      if (owner === active) break;
      owner = owner.parentElement;
    }
    if (!reason && (!background || owner === active) && complexVisuals.some(visual => (
      overlaps(rect, visual.getBoundingClientRect())
    ))) {
      reason = 'overlapping image or canvas';
    }
    if (!reason && style.textShadow && style.textShadow !== 'none') {
      reason = 'text shadow';
    }
    if (reason || !background) {
      warnings.push(`${name}: contrast requires full-size visual review because of ${reason || 'an unresolved background'}`);
      items.push({ name, status: 'deferred', reason: reason || 'unresolved background' });
      continue;
    }
    const foreground = parseColor(style.color);
    if (!foreground) {
      warnings.push(`${name}: contrast requires full-size visual review because the text color could not be parsed`);
      items.push({ name, status: 'deferred', reason: 'unparsed text color' });
      continue;
    }
    const effectiveForeground = foreground.a < 1 ? composite(foreground, background) : foreground;
    const ratio = contrast(effectiveForeground, background);
    const size = Number.parseFloat(style.fontSize) || 0;
    const weight = Number.parseInt(style.fontWeight, 10) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const required = large ? 3 : 4.5;
    const rounded = Math.round(ratio * 100) / 100;
    items.push({ name, status: ratio >= required ? 'pass' : 'fail', ratio: rounded, required, fontSize: size, fontWeight: weight });
    if (ratio < required) {
      issues.push(`${name}: text contrast ${rounded}:1 is below the required ${required}:1`);
    }
  }

  return {
    ok: issues.length === 0,
    checked: items.filter(item => item.status !== 'deferred').length,
    deferred: items.filter(item => item.status === 'deferred').length,
    issues: [...new Set(issues)],
    warnings: [...new Set(warnings)],
    items,
  };
})()
