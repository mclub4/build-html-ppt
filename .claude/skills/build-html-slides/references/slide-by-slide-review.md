# Slide-By-Slide Review

Read `validation-contract.md` first. That file decides which slides and profiles require AI inspection. This file explains how to inspect them and fill `review.json` without overstating evidence.

## Before Vision

Run the renderer for the selected mode. Do not open captures while `automation_gate.status` is failing. Fix text bounds, control geometry, image load/aspect/resolution, or other deterministic failures first.

Every slide still retains all canonical captures. Only slides listed in `review_batches` require AI review. In Quick Draft, ordinary slides without warnings remain `automated-geometry-only`; do not add reviewer labels or observations to them.

## Batch Procedure

For each generated batch of at most four slides. Keep the batch intact in one vision call; do not open one call per slide or per image:

1. Open exactly the full-size PNGs listed in each slide's `required_ai_profiles`. When `identity_required` is true, also open every local `identity_targets[].reference_path`.
2. Inspect the images, not only HTML source, a contact sheet, or DOM metrics.
3. Keep one concrete observation and one verdict per slide, even when several profiles were opened.
4. Copy `required_ai_profiles` to `inspected_profiles` only after actual inspection.
5. Fill only the checks required by `review_scope`. Complete each `identity_review` entry from pixel comparison, never from labels or filenames.
6. Record a readable reviewer label and stable run-specific `reviewer_ref`.

Use contact sheets only to notice deck-wide rhythm, repetition, or density. They do not replace slide-level inspection.

## Visual Checks

For `all` scope:

- `crop`: meaningful content remains fully visible;
- `aspect_ratio`: images, logos, screenshots, and diagrams are not stretched;
- `resolution`: raster detail is adequate at displayed size;
- `content_match`: each meaningful image actually depicts and supports the slide's claimed subject, event, product, place, or concept; labels are not evidence;
- `overflow`: text and components remain inside their intended regions;
- `occlusion`: media and decoration do not obscure copy or controls;
- `text`: copy is readable and visually coherent;
- `text_bounds`: text remains inside its box, cell, button, badge, column, and safe area;
- `density`: cards, panels, and decorative shapes justify their area and do not leave sparse copy stranded in oversized empty boxes;
- `controls`: navigation and interactive elements are centered, readable, and usable.
- `identity`: on explicitly or automatically identity-routed slides, every candidate matches its canonical WebP reference and the intended character/person variant.

Text-only changes use `text`, `text_bounds`, and `density`; image-only changes use crop, aspect ratio, resolution, and content match; navigation-only changes use controls. Identity-required `all` and `image` reviews also include `identity` and one cue-based `identity_review` entry per target.

## Concrete Observations

Write what was visibly checked on that slide. Good observations name the composition and the result, for example:

> The two-line Korean title remains inside the left safe column, while the contained product image keeps all four edges and the bottom-right controls stay clear.

Do not reuse generic approval text across slides. Do not claim a model or person inspected evidence unless that inspection actually occurred.

## Fix Loop

After a scoped edit, rerun `validate_all.py --phase prepare` with `--slides` and the matching `--change-type`. The renderer keeps a CSS rule that matches one slide in that slide's fingerprint; shared styles and runtime changes still force a full render. Reopen only the refreshed slides routed to AI review, then run `validate_all.py --phase verify`.

## Full Validation Final Pass

After all findings are settled:

1. run `validate_all.py --phase finalize`;
2. have an independent presentation editor score the deck once with `quality-bar.md`;
3. add independent cross-reviews for cover, closing, and slides explicitly marked `data-visual-critical="true"`;
4. bind cross-reviews to current capture hashes;
5. run the visual-review validator again.

Quick Draft skips quality scoring and cross-review.

Image count does not create additional AI calls by itself. Inspect the rendered composition once per required slide/profile set. Do not open every fan-art source as a separate validation step, and do not infer critical status from styling classes such as `logo`, `key-visual`, `title-art`, or `diagram`.

## Evidence Limits

The validator checks capture origin, dimensions, PNG validity, hashes, current source fingerprints, adaptive routing, batch membership, geometry, and review-record structure. Reviewer names and observations are declarations, not cryptographic proof of a vision call. Report the result as evidence-consistent review, not independently attested inspection.
