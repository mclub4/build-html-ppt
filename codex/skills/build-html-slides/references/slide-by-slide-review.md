# Slide-By-Slide Review

Read `validation-contract.md` first. That file decides which slides and profiles require AI inspection. This file explains how to inspect them and fill `review.json` without overstating evidence.

Use `validate_all.py OUTPUT.html --status` to list pending batches and the next phase. After inspecting the named current captures, use `record_review.py` with the matching `slide`, `cross-slide`, `quality`, or `squint` subcommand. Supply every requested check and a concrete observation. The recorder only performs schema-safe writes; it cannot see the captures and never creates a verdict.

## Before Vision

This procedure applies to Full Validation. Run the renderer and do not open captures while `automation_gate.status` is failing. Fix text bounds, control geometry, image load/aspect/resolution, or other deterministic failures first. Quick Draft does not create captures or enter this procedure.

Every slide retains all canonical captures. Only slides listed in `review_batches` require AI review.

## Batch Procedure

For each generated batch of at most four slides. Keep the batch intact in one vision call; do not open one call per slide or per image:

1. Open exactly the full-size PNGs listed in each slide's `required_ai_profiles`. When `identity_required` is true, also open every local `identity_targets[].reference_path`.
2. Inspect the images, not only HTML source, a contact sheet, or DOM metrics.
3. Inspect cross-layer relationships: look for imagery crossing dividers, labels, captions, copy, controls, or card edges even when every element remains inside the slide bounds. Check whether the visible subject—not the raster canvas—occupies a useful share of its frame.
4. Keep one concrete observation and one verdict per slide, even when several profiles were opened.
5. Copy `required_ai_profiles` to `inspected_profiles` only after actual inspection.
6. Fill only the checks required by `review_scope`. Complete each `identity_review` entry from pixel comparison, never from labels or filenames.
7. Record a readable reviewer label and stable run-specific `reviewer_ref`.

Use ordinary contact sheets only to notice deck-wide rhythm, repetition, density, or a report-like absence of subject imagery. They do not replace slide-level inspection. In Full Validation, `--phase finalize-prepare` also creates one lightly blurred squint contact sheet from every current `normal` capture. The final quality editor uses it for focal hierarchy, emphasis range, deck rhythm, and color/density balance only. It cannot approve text overlap, awkward line breaks, crop, distortion, overflow, identity, or media appropriateness; open the relevant full-size captures for those checks. The final quality editor must assess whether the deck's overall media mix fits the subject rather than rewarding chart-only rigor by default.

## Visual Checks

For `all` scope:

- `crop`: meaningful content remains fully visible;
- `aspect_ratio`: images, logos, screenshots, and diagrams are not stretched;
- `resolution`: inspect the full-size capture and confirm that edges, packaging, faces, screenshots, and embedded text are visibly sharp; reject thumbnails, prior upscales, heavy JPEG/WebP artifacts, ringing, or blur even when natural dimensions and effective pixel density pass;
- `content_match`: each meaningful image actually depicts and supports the slide's claimed subject, event, product, place, or concept; labels are not evidence. On the cover, chapter openers, company/entity profiles, and mechanism slides, also fail when a physical or observable subject that reasonably needs to be seen is replaced only by generic SVG, chart, or text treatment;
- `completion`: no visible placeholder, temporary/dummy asset, empty media frame, or generic substitute graphic stands in for a promised real subject image; `PLACE NOTE` is an automatic failure, not a design label;
- `overflow`: text and components remain inside their intended regions;
- `occlusion`: media and decoration do not obscure copy or controls;
- `text`: copy is readable and visually coherent, with natural phrase-boundary wrapping and no one- or two-character Korean final line;
- `text_bounds`: text remains inside its box, cell, button, badge, column, and safe area; rendered rows do not collide with each other or sibling copy, and navigation covers no caption, source, or footer text;
- `density`: cards, panels, and decorative shapes justify their area and do not leave sparse copy stranded in oversized empty boxes;
- `controls`: navigation and interactive elements are centered, readable, and usable.
- `identity`: on explicitly or automatically identity-routed slides, every candidate matches its canonical WebP reference and the intended character/person variant.

Text-only changes use `text`, `text_bounds`, and `density`; image-only changes use crop, aspect ratio, resolution, content match, and completion; navigation-only changes use controls. Identity-required `all` and `image` reviews also include `identity` and one cue-based `identity_review` entry per target.

## Concrete Observations

Write what was visibly checked on that slide. Good observations name the composition and the result, for example:

> The two-line Korean title remains inside the left safe column, while the contained product image keeps all four edges and the bottom-right controls stay clear.

Do not reuse generic approval text across slides. Do not claim a model or person inspected evidence unless that inspection actually occurred.

## Fix Loop

After a scoped edit, rerun `validate_all.py --phase prepare` with `--slides` and the matching `--change-type`. Pure copy, image, and slide-local CSS changes refresh only affected slides. Structure, order, transition, and adjacency-sensitive changes add immediate neighbors. Shared deck-wide CSS and runtime changes force a full render. CSS rules matching a finite slide subset and their background assets stay bound to that subset. Reopen every refreshed slide routed to AI review, then run `validate_all.py --phase verify`.

Never change a FAIL record to PASS in place. A FAIL requires a deck change, a new render run, and inspection of the new capture hashes. Focus that loop on the failed slide and check family; do not rerun unrelated validators or reopen unaffected captures. Do not bulk-generate reviewer labels, observations, checks, or PASS statuses. If a reviewer reports a defect after the main agent believes it is fixed, the reviewer verdict wins until a new independent inspection closes it.

## Full Validation Final Pass

After all findings are settled:

1. run `validate_all.py --phase finalize-prepare`;
2. have an independent presentation editor inspect and fill the generated squint record once;
3. have that editor score the deck once with `quality-bar.md`;
4. complete exactly the generated `cross_review_batches`, using reviewers outside the full primary-reviewer set;
5. bind squint and cross-reviews to current capture hashes;
6. run `validate_all.py --phase finalize-verify`.

The bounded set contains the cover, closing, explicit visual-critical/core slides, automation-warning slides, and identity-sensitive slides. Do not add distributed ordinary-slide samples, and do not expand high-risk cross-review to every slide. This independent pass is not removed as duplicate checking. After a focused repair, reuse a passing independent review only when the slide capture hash and review contract are unchanged; regenerate only the failed or changed slide's review.

Image count does not create additional AI calls by itself. Inspect the rendered composition once per required slide/profile set. Do not open every fan-art source as a separate validation step, and do not infer critical status from styling classes such as `logo`, `key-visual`, `title-art`, or `diagram`.

## Evidence Limits

The validator checks capture origin, dimensions, PNG validity, hashes, current source fingerprints, adaptive routing, batch membership, geometry, and review-record structure. Reviewer names and observations are declarations, not cryptographic proof of a vision call. Never manufacture those declarations to satisfy the schema. Report the result as evidence-consistent review, not independently attested inspection.
