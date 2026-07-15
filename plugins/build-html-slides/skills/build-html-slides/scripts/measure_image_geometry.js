(() => {
  const tolerance = 2;
  const active = document.querySelector('.slide.active');
  const issues = [];
  const warnings = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings: [] };

  const identityModes = new Set(['primary', 'contains']);

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
  const identitySetting = (active.dataset.identityReview || '').trim();
  const hasIdentityMetadata = elements.some(element => [
    element.dataset.subjectId,
    element.dataset.subjectName,
    element.dataset.identityReference,
    element.dataset.identityCues,
  ].some(value => (value || '').trim()));
  const identityKinds = new Set(['character', 'person', 'cast', 'member', 'portrait', 'named-subject']);
  const declaredIdentity = [active, ...active.querySelectorAll('[data-slide-kind],[data-content-kind]')]
    .some(element => identityKinds.has(
      (element.dataset.slideKind || element.dataset.contentKind || '').trim().toLowerCase()
    ));
  const semanticClass = [active, ...active.querySelectorAll('[class]')].some(element => (
    [...element.classList].some(token => (
      /(?:^|-)(?:character|person|cast|member|portrait)(?:-|$)/i.test(token)
      || /^(?:profile-wrap|profile-gallery|profile-grid)$/i.test(token)
    ))
  ));
  const semanticIdentity = declaredIdentity || semanticClass;
  const identityRequired = identitySetting === 'required' || hasIdentityMetadata
    || (identitySetting !== 'not-applicable' && semanticIdentity);
  const identityDetection = identitySetting === 'required'
    ? 'explicit'
    : (hasIdentityMetadata ? 'subject-metadata' : (semanticIdentity ? 'semantic-markup' : 'none'));
  if (identitySetting === 'not-applicable' && hasIdentityMetadata) {
    issues.push('data-identity-review="not-applicable" conflicts with subject identity metadata');
  }
  const items = [];

  for (const [index, element] of elements.entries()) {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const name = label(element, index);
    const decorative = element.closest('[aria-hidden="true"], .slide-media') !== null
      || element.getAttribute('alt') === '';
    const sourceUrl = element.currentSrc || element.src || element.getAttribute('href') || '';
    const subjectId = (element.dataset.subjectId || '').trim();
    const subjectName = (element.dataset.subjectName || '').trim();
    const identityReference = (element.dataset.identityReference || '').trim();
    const identityCues = (element.dataset.identityCues || '')
      .split(';').map(value => value.trim()).filter(Boolean);
    const identityMode = (element.dataset.identityMode || 'primary').trim();
    const item = {
      name,
      width: round(rect.width),
      height: round(rect.height),
      decorative,
      objectFit: style.objectFit || 'fill',
      sourceUrl,
      identity: {
        subjectId,
        subjectName,
        referenceUrl: identityReference ? new URL(identityReference, document.baseURI).href : '',
        cues: identityCues,
        mode: identityMode,
      },
    };

    if (identityRequired && !decorative) {
      if (!subjectId) issues.push(`${name}: identity review requires data-subject-id`);
      if (!subjectName) issues.push(`${name}: identity review requires data-subject-name`);
      if (!identityReference) issues.push(`${name}: identity review requires data-identity-reference`);
      if (identityCues.length < 2) issues.push(`${name}: identity review requires at least two semicolon-separated identity cues`);
      if (!identityModes.has(identityMode)) issues.push(`${name}: data-identity-mode must be primary or contains`);
    }

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
      const browserScale = window.visualViewport?.scale || 1;
      const density = 1 / Math.max(cssScale * window.devicePixelRatio * browserScale, 0.0001);
      item.pixelDensity = round(density);
      if (!element.hasAttribute('data-low-res-ok') && density < 1) {
        issues.push(`${name}: effective raster resolution is only ${round(density)}x device pixels`);
      } else if (!element.hasAttribute('data-low-res-ok') && density < 1.25) {
        warnings.push(`${name}: effective raster resolution is borderline at ${round(density)}x device pixels`);
      }
    }
    items.push(item);
  }

  if (identityRequired && !items.some(item => !item.decorative && item.identity.subjectId)) {
    issues.push('Identity review requires at least one annotated non-decorative image');
  }

  return {
    ok: issues.length === 0,
    checked: elements.length,
    identityRequired,
    identityDetection,
    issues: [...new Set(issues)],
    warnings: [...new Set(warnings)],
    items,
  };
})()
