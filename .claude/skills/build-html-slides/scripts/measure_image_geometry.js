(() => {
  // Thresholds are deterministic replacements for reviewer judgement. Rationale, one line each:
  // BOUNDS_TOLERANCE_PX  - subpixel layout rounding only; anything larger is a real escape.
  const BOUNDS_TOLERANCE_PX = 2;
  // CONTAINER_TOLERANCE_PX - same rounding budget for the card/panel padding box; a deliberate bleed must declare data-image-bleed-ok.
  const CONTAINER_TOLERANCE_PX = 2;
  // STAGE_WIDTH/STAGE_HEIGHT - the canonical 1280x720 authoring stage every ratio below is measured against.
  const STAGE_WIDTH = 1280;
  const STAGE_HEIGHT = 720;
  // HERO_MIN_STAGE_RATIO - a hero/cover subject carries the slide; below 15% of the stage (~440x315) it stops reading as the subject.
  const HERO_MIN_STAGE_RATIO = 0.15;
  // SUBJECT_MIN_STAGE_RATIO - an ordinary subject/evidence photo below 5% of the stage (~215x215) is hard to read from a projector row.
  const SUBJECT_MIN_STAGE_RATIO = 0.05;
  // SUBJECT_HARD_MIN_STAGE_RATIO - below 2% (~136x136) a declared subject is illegible at playback size; this is the shipped 100x100 defect.
  const SUBJECT_HARD_MIN_STAGE_RATIO = 0.02;
  // SUBJECT_MIN_EDGE_PX - a subject narrower or shorter than 96 stage px cannot show product/person detail regardless of area.
  const SUBJECT_MIN_EDGE_PX = 96;
  // SUBJECT_DOWNSCALE_WARN_RATIO - 2x retina sources are normal, so only under a quarter of intrinsic size (a 4x+ oversized asset) reads as "meant to be shown larger".
  const SUBJECT_DOWNSCALE_WARN_RATIO = 0.25;
  // TRANSPARENCY_SAMPLE_EDGE / TRANSPARENCY_ALPHA_FLOOR - 64px alpha probe that discounts empty padding so a small product on a big transparent canvas is judged on its body.
  const TRANSPARENCY_SAMPLE_EDGE = 64;
  const TRANSPARENCY_ALPHA_FLOOR = 12;
  // TRANSPARENCY_DISCOUNT_FLOOR - ignore probes claiming the body is under 4% of the canvas; that is noise, not a measurement.
  const TRANSPARENCY_DISCOUNT_FLOOR = 0.04;

  const tolerance = BOUNDS_TOLERANCE_PX;
  const active = document.querySelector('.slide.active');
  const issues = [];
  const warnings = [];
  if (!active) return { ok: false, checked: 0, issues: ['Missing active slide'], warnings: [] };

  const identityModes = new Set(['primary', 'contains']);
  // Documented data-media-purpose vocabulary. Declared purpose is authoritative; .slide-media membership never is.
  const decorativePurposes = new Set(['atmosphere', 'concept', 'scenario', 'decorative']);
  const meaningfulPurposes = new Set(['subject', 'evidence', 'identity']);
  const heroRoles = new Set(['hero', 'cover', 'key-visual', 'keyvisual', 'primary', 'lead']);
  // Shared vocabulary with measure_container_density.js line 7 so the two scripts agree on what a container is.
  const containerSelector = '.card, .panel, .tile, .box, [data-density-container]';

  const round = value => Math.round(value * 100) / 100;
  const percent = value => Math.round(value * 1000) / 10;
  const rendered = element => {
    const style = getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden'
      && Number(style.opacity) > 0;
  };
  const label = (element, index) => (
    element.getAttribute('alt') || element.getAttribute('aria-label') || element.id
    || element.getAttribute('src') || element.getAttribute('href') || `image-${index + 1}`
  ).slice(0, 80);
  const containerLabel = element => (
    element.getAttribute('data-title') || element.getAttribute('aria-label') || element.id
    || [...element.classList].join('.') || element.tagName.toLowerCase()
  ).slice(0, 60);
  const paddingBox = element => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const top = parseFloat(style.borderTopWidth) || 0;
    const right = parseFloat(style.borderRightWidth) || 0;
    const bottom = parseFloat(style.borderBottomWidth) || 0;
    const left = parseFloat(style.borderLeftWidth) || 0;
    return {
      left: rect.left + left,
      right: rect.right - right,
      top: rect.top + top,
      bottom: rect.bottom - bottom,
      width: Math.max(0, rect.width - left - right),
      height: Math.max(0, rect.height - top - bottom),
    };
  };
  const clipsAxis = value => ['hidden', 'clip', 'scroll', 'auto'].includes(value);
  const boundsAncestor = style => (
    style.position !== 'static'
    || style.transform !== 'none'
    || style.filter !== 'none'
    || style.perspective !== 'none'
    || clipsAxis(style.overflowX) || clipsAxis(style.overflowY)
    || /paint|layout|strict|content/.test(style.contain || '')
  );
  const visibleSurface = style => {
    const alpha = color => {
      const match = color.match(/rgba?\((?:[^,]+,){3}\s*([\d.]+)\s*\)/i);
      if (match) return Number(match[1]);
      return color === 'transparent' ? 0 : 1;
    };
    const borderWidth = ['Top', 'Right', 'Bottom', 'Left']
      .reduce((sum, side) => sum + (parseFloat(style[`border${side}Width`]) || 0), 0);
    return alpha(style.backgroundColor) > 0.04
      || style.backgroundImage !== 'none'
      || borderWidth > 0
      || style.boxShadow !== 'none';
  };
  // Owning container: explicit card vocabulary first, then the nearest ancestor that actually bounds or
  // paints a surface, and finally .slide-content itself. Returns null when the image lives outside content
  // (for example a full-bleed .slide-media layer) where only the slide-bounds test applies.
  const resolveContainer = element => {
    const content = element.closest('.slide-content');
    const explicit = element.parentElement && element.parentElement.closest(containerSelector);
    if (explicit && active.contains(explicit)) return { node: explicit, reason: 'explicit-container' };
    if (!content) return null;
    for (let node = element.parentElement; node && node !== content; node = node.parentElement) {
      if (!(node instanceof HTMLElement) && !(node instanceof SVGElement)) continue;
      const style = getComputedStyle(node);
      if (boundsAncestor(style)) return { node, reason: 'containing-block' };
      if (visibleSurface(style)) return { node, reason: 'rendered-surface' };
    }
    return { node: content, reason: 'slide-content' };
  };
  // Alpha probe: fraction of the source canvas covered by the opaque bounding box of real pixels.
  const bodyBoxFraction = element => {
    try {
      const width = Math.max(1, Math.min(TRANSPARENCY_SAMPLE_EDGE, element.naturalWidth));
      const height = Math.max(1, Math.min(TRANSPARENCY_SAMPLE_EDGE, element.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d', { willReadFrequently: true });
      if (!context) return null;
      context.clearRect(0, 0, width, height);
      context.drawImage(element, 0, 0, width, height);
      const { data } = context.getImageData(0, 0, width, height);
      let minX = width;
      let minY = height;
      let maxX = -1;
      let maxY = -1;
      for (let y = 0; y < height; y += 1) {
        for (let x = 0; x < width; x += 1) {
          if (data[(y * width + x) * 4 + 3] <= TRANSPARENCY_ALPHA_FLOOR) continue;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
      if (maxX < 0) return null;
      const fraction = ((maxX - minX + 1) / width) * ((maxY - minY + 1) / height);
      return fraction >= TRANSPARENCY_DISCOUNT_FLOOR ? Math.min(1, fraction) : null;
    } catch (_error) {
      return null;
    }
  };

  const slideRect = active.getBoundingClientRect();
  const stageArea = Math.max(
    (slideRect.width || STAGE_WIDTH) * (slideRect.height || STAGE_HEIGHT),
    1
  );
  const stageScale = (slideRect.width || STAGE_WIDTH) / STAGE_WIDTH;
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
    const mediaPurpose = (element.getAttribute('data-media-purpose') || '').trim().toLowerCase();
    const imageRole = (element.getAttribute('data-image-role') || '').trim().toLowerCase();
    const ariaHidden = element.closest('[aria-hidden="true"]') !== null;
    const emptyAlt = element.getAttribute('alt') === '';
    const heroRole = heroRoles.has(imageRole);
    // Declared purpose wins. Never infer decorative from .slide-media membership; when nothing is
    // declared, keep the image in scope so meaningful media cannot be skipped silently.
    let decorative;
    let decorativeReason;
    if (decorativePurposes.has(mediaPurpose)) {
      decorative = true;
      decorativeReason = 'declared-decorative-purpose';
    } else if (meaningfulPurposes.has(mediaPurpose)) {
      decorative = false;
      decorativeReason = 'declared-meaningful-purpose';
    } else if (heroRole) {
      decorative = false;
      decorativeReason = 'declared-hero-role';
    } else if (ariaHidden) {
      decorative = true;
      decorativeReason = 'aria-hidden';
    } else if (emptyAlt) {
      decorative = true;
      decorativeReason = 'empty-alt-without-purpose';
    } else {
      decorative = false;
      decorativeReason = 'undeclared-defaults-to-meaningful';
    }
    if (mediaPurpose && !decorativePurposes.has(mediaPurpose) && !meaningfulPurposes.has(mediaPurpose)) {
      warnings.push(`${name}: data-media-purpose "${mediaPurpose}" is not a documented value`);
    }
    if (!decorative && ariaHidden && meaningfulPurposes.has(mediaPurpose)) {
      warnings.push(`${name}: meaningful ${mediaPurpose} image sits inside an aria-hidden layer`);
    }
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
      decorativeReason,
      mediaPurpose,
      imageRole,
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

    // Containment: "did this leave its card", not merely "did this leave the slide".
    const owner = rect.width > 0 && rect.height > 0 ? resolveContainer(element) : null;
    if (owner) {
      const box = paddingBox(owner.node);
      const ownerStyle = getComputedStyle(owner.node);
      const overflow = {
        left: round(Math.max(0, box.left - rect.left)),
        right: round(Math.max(0, rect.right - box.right)),
        top: round(Math.max(0, box.top - rect.top)),
        bottom: round(Math.max(0, rect.bottom - box.bottom)),
      };
      const escaped = Object.values(overflow).some(value => value > CONTAINER_TOLERANCE_PX);
      const clipped = clipsAxis(ownerStyle.overflowX) && clipsAxis(ownerStyle.overflowY);
      const ownerName = containerLabel(owner.node);
      item.container = {
        name: ownerName,
        reason: owner.reason,
        width: round(box.width),
        height: round(box.height),
        clipped,
        overflow,
      };
      if (escaped && !element.hasAttribute('data-image-bleed-ok')) {
        const edges = Object.entries(overflow)
          .filter(([, value]) => value > CONTAINER_TOLERANCE_PX)
          .map(([edge, value]) => `${edge} ${value}px`)
          .join(', ');
        const geometry = `image ${round(rect.width)}x${round(rect.height)} at `
          + `${round(rect.left - slideRect.left)},${round(rect.top - slideRect.top)}; `
          + `container ${round(box.width)}x${round(box.height)} at `
          + `${round(box.left - slideRect.left)},${round(box.top - slideRect.top)}`;
        if (clipped) {
          if (!decorative) {
            warnings.push(
              `${name}: image is clipped by its container ${ownerName} (${edges}; ${geometry})`
            );
          }
        } else {
          issues.push(
            `${name}: image overflows its container ${ownerName} (${edges}; ${geometry})`
          );
        }
      }
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
      if (objectFit === 'cover' && !decorative) {
        warnings.push(`${name}: meaningful cover-cropped image requires full-size visual crop inspection`);
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

      // Prominence: how large the subject actually renders, not merely how many pixels it carries.
      const prominenceScope = !decorative
        && (meaningfulPurposes.has(mediaPurpose) || heroRole);
      if (prominenceScope) {
        const renderedArea = rect.width * rect.height;
        const stageRatio = renderedArea / stageArea;
        const discount = objectFit === 'cover' ? null : bodyBoxFraction(element);
        const bodyRatio = discount === null ? stageRatio : stageRatio * discount;
        const stageWidth = round(rect.width / Math.max(stageScale, 0.0001));
        const stageHeight = round(rect.height / Math.max(stageScale, 0.0001));
        const shortEdge = Math.min(stageWidth, stageHeight);
        item.stageAreaRatio = Math.round(stageRatio * 10000) / 10000;
        item.stageWidth = stageWidth;
        item.stageHeight = stageHeight;
        if (discount !== null) item.bodyBoxFraction = round(discount);
        item.subjectAreaRatio = Math.round(bodyRatio * 10000) / 10000;
        item.subjectTier = heroRole ? 'hero' : 'subject';
        const scope = heroRole ? 'hero subject' : `${mediaPurpose || 'subject'} image`;
        const measured = `${percent(bodyRatio)}% of the 1280x720 stage `
          + `(${stageWidth}x${stageHeight} stage px`
          + `${discount === null ? '' : `, ${percent(discount)}% opaque body`})`;
        if (element.hasAttribute('data-subject-scale-ok')) {
          // Explicit author waiver; still reported in items for the record.
        } else if (heroRole && bodyRatio < HERO_MIN_STAGE_RATIO) {
          issues.push(
            `${name}: ${scope} renders at only ${measured}, below the `
            + `${percent(HERO_MIN_STAGE_RATIO)}% hero prominence minimum`
          );
        } else if (!heroRole && bodyRatio < SUBJECT_HARD_MIN_STAGE_RATIO) {
          issues.push(
            `${name}: ${scope} renders at only ${measured}, below the `
            + `${percent(SUBJECT_HARD_MIN_STAGE_RATIO)}% subject prominence minimum`
          );
        } else if (!heroRole && bodyRatio < SUBJECT_MIN_STAGE_RATIO) {
          warnings.push(
            `${name}: ${scope} renders small at ${measured}, below the `
            + `${percent(SUBJECT_MIN_STAGE_RATIO)}% recommended subject prominence`
          );
        }
        if (!element.hasAttribute('data-subject-scale-ok') && shortEdge < SUBJECT_MIN_EDGE_PX) {
          issues.push(
            `${name}: ${scope} renders only ${shortEdge} stage px on its short edge, `
            + `below the ${SUBJECT_MIN_EDGE_PX}px legibility minimum`
          );
        }
        const renderScale = Math.max(
          rect.width / element.naturalWidth,
          rect.height / element.naturalHeight
        );
        item.renderScale = round(renderScale);
        if (
          !element.hasAttribute('data-subject-scale-ok')
          && renderScale < SUBJECT_DOWNSCALE_WARN_RATIO
          && objectFit !== 'cover'
        ) {
          warnings.push(
            `${name}: ${scope} renders at ${round(renderScale)}x its intrinsic size `
            + `(${round(rect.width)}x${round(rect.height)} from `
            + `${element.naturalWidth}x${element.naturalHeight}); the source was prepared for a larger box`
          );
        }
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
