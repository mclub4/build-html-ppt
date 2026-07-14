# Slide-by-Slide Render Review

Review settled Chromium output, not HTML source. Keep the process proportional: retain three default profiles, block AI review on deterministic geometry failures, batch up to four slides per vision call, route stress profiles adaptively, rerender incrementally after edits, and score quality once after the deck is settled.

## Tool preflight

For Full Validation, run this before substantial work:

```bash
node scripts/render_slides.js --check
```

If it fails, report the exact missing component and ask before installing Node.js, Playwright, Chromium, or browser dependencies. Re-run the check after an approved installation.

## Capture profiles

The default evidence set is always three profiles:

| Profile | CSS viewport | PNG | Purpose |
|---|---:|---:|---|
| `normal` | 1920x1080 | 1920x1080 | primary desktop composition |
| `short` | 1366x650 | 1366x650 | browser chrome and short-height stress |
| `zoom150` | 1280x720 | 1920x1080 | 150% zoom/display-scaling stress |

Only add `--responsive` when the user requests mobile/tablet support. It appends `tablet` 1024x768 and `mobile` 390x844. Do not run responsive profiles for an ordinary presentation.

The renderer disables transitions and animations only inside the Playwright validation page, waits two animation frames, and captures the settled state. The final HTML keeps its authored animations.

All three default PNGs remain evidence. AI inspects `normal` for every slide. It also inspects `short` and `zoom150` for the cover, closing, a slide explicitly marked `data-visual-critical="true"`, or a profile with an automated warning. Requested `tablet` and `mobile` profiles are always included in AI review. Use the marker only for genuinely high-risk crops, diagrams, dense data, or layout dependencies; do not mark every slide critical.

## Initial and incremental rendering

Create the initial evidence set:

```bash
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --mode quick
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --mode full
```

After an edit, render only the changed slide and its immediate neighbors:

```bash
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --mode full --slides 5 --change-type text
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --mode full --slides 5,9 --change-type image
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --mode full --slides 2 --change-type navigation
```

`--slides 5` refreshes slides 4, 5, and 6. The renderer also compares current source fingerprints with the previous manifest and automatically includes changed slides omitted from the command. A global CSS, shell, or runtime change forces a full rerender because it can affect every slide. Unchanged slide captures retain their prior PNGs and review records.

Use the narrowest truthful change type:

- `text`: `text`, `text_bounds`
- `image`: `crop`, `aspect_ratio`, `resolution`
- `navigation`: `controls`
- `all`: every visual check; use for initial builds, layout/theme changes, or mixed changes

## Automated gate before vision

The renderer checks the scoped geometry before creating `review_batches`:

- `text_bounds`: rendered glyphs remain inside their slide and intended containers;
- `controls`: navigation and counters exist, fit, and remain centered;
- `image_geometry`: raster files load, meaningful image boxes stay in bounds, aspect ratios are not stretched, and effective pixel density is acceptable.

A gate failure exits nonzero and leaves details in `automation_gate.failures`. Fix those issues and rerender before opening any PNG. Warnings do not block review; they add the affected profile to that slide's `required_ai_profiles`.

## Batched AI review with per-slide verdicts

Use the generated `review_batches`; each contains at most four slides. A single vision call may open the listed full-size capture sets for all slides in that batch. For every slide listed in `render_run.rendered_slides`:

1. Open exactly the PNGs listed in its `required_ai_profiles`.
2. Write one concrete `observation` for that slide, even when several slides share the call.
3. Copy `required_ai_profiles` to `inspected_profiles` after actual inspection.
4. Pass only the checks required by that slide's `review_scope`.
5. Set the slide `status` to `pass` only when the group is acceptable.

Do not reuse one observation across slides or write one observation per profile. Geometry can reject a slide but cannot visually approve image crops, occlusion, contrast, or readability.

## Evidence integrity

Schema version 4 binds each capture and adaptive review route to:

- its PNG SHA-256;
- active slide number and exact `data-title`;
- canonical viewport metadata;
- the renderer run ID;
- the slide source and local-asset fingerprint;
- deterministic text/control/image geometry when required by `review_scope`;
- a passing pre-vision automation gate;
- a review batch ID and exact required AI profile set.

`validate_visual_review.py` decodes PNGs and quickly launches Chromium only to recompute source fingerprints. It does not rerender and compare every slide. Unchanged evidence is accepted only when the slide fingerprint is unchanged and no global style/runtime fingerprint changed.

## Manifest shape

The renderer creates `REVIEW_DIR/review.json`. Complete the pending review fields; do not hand-create capture metadata.

```json
{
  "schema_version": 4,
  "mode": "full",
  "phase": "iteration",
  "responsive": false,
  "change_type": "text",
  "render_run": {
    "strategy": "incremental",
    "requested_slides": [5],
    "rendered_slides": [4, 5, 6],
    "directly_changed_slides": [5],
    "reused_slides": [1, 2, 3, 7, 8],
    "animations_disabled": true
  },
  "automation_gate": {
    "status": "pass",
    "checks": ["text_bounds"],
    "failures": [],
    "warnings": []
  },
  "review_batches": [{
    "id": "batch-01",
    "slides": [4, 5, 6],
    "capture_profiles": {"4": ["normal"], "5": ["normal"], "6": ["normal"]}
  }],
  "slides": [{
    "slide": 5,
    "title": "Exact data-title",
    "review_scope": "text",
    "reviewer": "visual-a",
    "reviewer_ref": "agent-run-visual-a",
    "review_batch_id": "batch-01",
    "review_method": "vision-batched-full-size",
    "captures": {
      "normal": {"path": "normal/slide-05.png", "sha256": "generated hash"},
      "short": {"path": "short/slide-05.png", "sha256": "generated hash"},
      "zoom150": {"path": "zoom150/slide-05.png", "sha256": "generated hash"}
    },
    "required_ai_profiles": ["normal"],
    "inspected_profiles": ["normal"],
    "observation": "Opened the normal render in batch-01; the revised title remains inside its intended column with clear hierarchy.",
    "checks": {"text": "pass", "text_bounds": "pass"},
    "status": "pass",
    "notes": []
  }],
  "quality_score": {"status": "pending"}
}
```

Validate each iteration:

```bash
python3 scripts/validate_visual_review.py OUTPUT.html REVIEW_DIR/review.json
```

## Final quality pass

After all fixes and slide-level reviews pass, switch the manifest to final phase without rendering again:

```bash
node scripts/render_slides.js OUTPUT.html REVIEW_DIR --finalize
```

Then calculate the quality rubric once, fill `quality_score`, add required Full Validation cross-reviews for the cover, closing, and marked critical slides, and run the validator once more. `--finalize` refuses to proceed if the HTML, a slide, a local asset, or global runtime changed after review.

## Fix loop

1. Fix a failed or suspicious slide.
2. Run `--slides` with the matching `--change-type`; immediate neighbors are included automatically.
3. Review the refreshed slides once each and update only their records.
4. Validate the iteration.
5. Calculate the 24-point score only once, after `--finalize`.
