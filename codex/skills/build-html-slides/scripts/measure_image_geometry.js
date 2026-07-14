(() => {
  const tolerance = 2;
  const active = document.querySelector('.slide.active');
  const issues = [];
  const warnings = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings: [] };

  const round = value => Math.round(value * 100) / 100;
  const rendered = element => {
    const style = getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0;
  };
  const label = (element, index) => (
    element.getAttribute('alt') || element.getAttribute('aria-label') || element.id
    || element.getAttribute('src') || element.getAttribute('href') || `image-${index + 1}`
  ).slice(0, 80);
  const slideRect = active.getBoundingClientRect();
  const elements = [...active.querySelectorAll('img, svg image')].filter(element => (
    rendered(element) && !element.hasAttribute('data-image-geometry-ignore')
  ));
  const items = [];

  for (const [index, element] of elements.entries()) {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const name = label(element, index);
    const decorative = element.closest('[aria-hidden="true"], .slide-media') !== null
      || element.getAttribute('alt') === '';
    const item = {
      name,
      width: round(rect.width),
      height: round(rect.height),
      decorative,
      objectFit: style.objectFit || 'fill',
    };

    if (rect.width <= 0 || rect.height <= 0) {
      issues.push(`${name}: image has no rendered size`);
    }

    if (
      rect.left < slideRect.left - tolerance || rect.right > slideRect.right + tolerance
      || rect.top < slideRect.top - tolerance || rect.bottom > slideRect.bottom + tolerance
    ) {
      issues.push(`${name}: image element crosses active slide bounds`);
    }

    if (element instanceof HTMLImageElement) {
      item.naturalWidth = element.naturalWidth;
      item.naturalHeight = element.naturalHeight;
      if (!element.complete || element.naturalWidth < 1 || element.naturalHeight < 1) {
        issues.push(`${name}: image did not load with valid intrinsic dimensions`);
        items.push(item);
        continue;
      }
      const intrinsicRatio = element.naturalWidth / element.naturalHeight;
      const boxRatio = rect.width / rect.height;
      const objectFit = style.objectFit || 'fill';
      if (objectFit === 'fill' && Math.abs(intrinsicRatio / boxRatio - 1) > 0.03) {
        issues.push(`${name}: image is stretched because object-fit is fill`);
      }

      let cssScale;
      if (objectFit === 'contain' || objectFit === 'scale-down') {
        cssScale = Math.min(rect.width / element.naturalWidth, rect.height / element.naturalHeight);
      } else if (objectFit === 'cover') {
        cssScale = Math.max(rect.width / element.naturalWidth, rect.height / element.naturalHeight);
      } else if (objectFit === 'none') {
        cssScale = 1;
      } else {
        cssScale = Math.max(rect.width / element.naturalWidth, rect.height / element.naturalHeight);
      }
      const density = 1 / Math.max(cssScale * window.devicePixelRatio, 0.0001);
      item.pixelDensity = round(density);
      if (!decorative && !element.hasAttribute('data-low-res-ok') && density < 0.85) {
        issues.push(`${name}: effective raster resolution is only ${round(density)}x device pixels`);
      } else if (!decorative && density < 1.1) {
        warnings.push(`${name}: effective raster resolution is borderline at ${round(density)}x device pixels`);
      }
    }
    items.push(item);
  }

  return {
    ok: issues.length === 0,
    checked: elements.length,
    issues: [...new Set(issues)],
    warnings: [...new Set(warnings)],
    items,
  };
})()
