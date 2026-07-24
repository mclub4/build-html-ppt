# Reviewer Gates

Single authoritative home for the rules every reviewer shares: which checks a slide owes, what the deterministic gates already prove, how a warned slide is adjudicated, and which defects block delivery regardless of any score.

Other references cite this file instead of restating it. `scripts/validation_contract.json` remains the machine authority for check tuples, profiles, batch size, variety thresholds, and time budgets.

## Check tuples

`validate_visual_review.py` compares the recorded `checks` object against the tuple for the slide's `review_scope` **exactly and in order**. A missing or reordered key fails the phase.

| `review_scope` | Required checks, in contract order |
| --- | --- |
| `all` | `crop`, `aspect_ratio`, `resolution`, `content_match`, `completion`, `overflow`, `occlusion`, `text`, `text_bounds`, `contrast`, `density`, `controls` |
| `text` | `text`, `text_bounds`, `contrast`, `density` |
| `image` | `crop`, `aspect_ratio`, `resolution`, `content_match`, `completion` |
| `navigation` | `controls` |

An identity-routed `all` or `image` review appends `identity` and one cue-based `identity_review` entry per target.

## What the machine already proves

These gates run before any capture reaches a reviewer. Do not re-litigate them in prose, and never overrule a measured issue with an aesthetic argument. Each row names the real threshold and the message prefix that appears in `review.json`.

| Gate | Measures | Threshold | Blocking message |
| --- | --- | --- | --- |
| `measure_image_geometry.js` | image escaping its container padding box | more than `2px` on any edge | `…: image overflows its container <name> (left Npx, …; image WxH at x,y; container WxH at x,y)` |
| | hero/cover subject prominence | under `15%` of the 1280×720 stage | `…: hero subject renders at only N% of the 1280x720 stage (WxH stage px, M% opaque body), below the 15% hero prominence minimum` |
| | ordinary subject prominence | under `2%` of the stage | `…: subject image renders at only N% …, below the 2% subject prominence minimum` |
| | subject short edge | under `96` stage px | `…: renders only N stage px on its short edge, below the 96px legibility minimum` |
| | raster resolution | under `1.0×` device pixels | `…: effective raster resolution is only N x device pixels` |
| `measure_text_bounds.js` | rendered glyph-ink row collision | over `1px` of ink | `…: rendered text lines collide by Npx of glyph ink; increase line-height or reduce/reflow the display type` |
| | opaque foreground biting into glyph ink | over `1.5px` | `…: rendered text is covered by an opaque visual layer (Npx of glyph ink)` |
| | unsupported synthesized weight | weight outside the local `@font-face` set | `…: font-family "…" requests weight N outside its declared local faces` |
| `measure_geometry.js` | navigation exclusion zone intrusion | over `1px` on both axes | `…: <kind> intrudes W×Hpx into the reserved lower-right navigation exclusion zone (280×84px stage area); move it out or mark an explicit data-nav-exclusion-ok exception` |
| `measure_contrast.js` | provable contrast interval | `best < required` (4.5:1 body, 3:1 large) | `…: text contrast is at most N:1 against every backdrop this text can sit on (…), below the required M:1` |
| `measure_container_density.js` | union ink coverage of every layout region | region ≥ 7% of the slide and ≥ 200×110px with low ink | warning `…: oversized low-information region (slide N%, ink M%, chars C, largest type Tpx, content height H%)` |
| `validate_slide_variety.py` | near-duplicate slide compositions | skeleton similarity ≥ `0.90` with equal card counts, column counts, and asset sets, on slides of ≥ `8` structural elements | `ERROR: slides A and B are near-duplicate compositions: skeleton similarity N …` |

Escape hatches are author declarations, not reviewer opinions, and every one of them still requires a visual verdict: `data-image-bleed-ok`, `data-subject-scale-ok`, `data-low-res-ok`, `data-image-geometry-ignore`, `data-nav-exclusion-ok`, `data-density-ignore`, `data-line-break-ok`, `data-text-overlap-ok`, `data-variety-ok`. A reviewer who sees an escape hatch on a slide must say in its observation what makes the exception legitimate.

## Navigation exclusion zone

The lower-right `280×84px` of the logical 1280×720 stage is reserved. `measure_geometry.js` reads `--nav-exclusion-width` and `--nav-exclusion-height` from `:root` at runtime, falls back to `280×84` when they are absent, projects the rectangle through the stage transform, and unions it with the real controls rectangle plus an `8px` breathing margin. Any rendered ink outside the controls subtree that lands inside that rectangle is a blocking issue.

- The shell's `.nav-safe-note` helper clears the zone by construction — it is anchored at `right: var(--nav-exclusion-width)` — so it needs no exemption.
- `data-nav-exclusion-ok` is the only explicit exemption, and it must be a deliberate relocation of the controls, not a silencer.
- `.slide-media`, `.nav`, `.controls`, `.edge`, `.progress`, and `[data-runtime-control]` are already excluded from the scan.

## Refute-or-confirm: how a warned slide is adjudicated

A deterministic warning is a finding that has not yet been resolved, not a suggestion. In the incident that produced this contract, `measure_contrast.js` reported an unresolved overlapping-media backdrop on a slide, and both reviewers wrote a general approval — "an intentional connecting rule that does not cover the product" — while the rule sat across the product photo and the price. Both saw the same flat capture and the same pass-shaped checklist, so the second review added nothing.

When any measurement raises a warning on a slide, that slide enters a **refute-or-confirm pass** instead of an ordinary review:

1. The parent supplies the reviewer with the verbatim warning text, the full-size `normal` capture, and the boundary overlay capture that the renderer wrote for that slide and profile: `review/<profile>/slide-NN-debug.png`, recorded at `captures.<profile>.debug_overlay.path` and `records[N].debug_captures.<profile>`. The renderer produces this capture for every slide/profile with at least one measured issue or warning. It draws the slide bounds, every resolved container in cyan, every image box in magenta, every text line's ink box in green, the reserved navigation zone in amber, and fills overflow and intersection regions in warning red, with a caption reading `slide N · <profile> · X issue(s), Y warning(s)`.
2. The reviewer must open both captures and return exactly one of two verdicts for the warning, as the first token of the slide observation:
   - `CONFIRM: ` followed by what is visibly wrong, named by element and location — for example `CONFIRM: the 1px connecting rule crosses the handset at x≈690 and passes through the "₩1,290,000" numeral`.
   - `REFUTE: ` followed by what is actually there instead, named by element and location, plus why the measurement could not see it — for example `REFUTE: the rule terminates at x≈612, 78px left of the handset edge; the warning came from the scrim rectangle, which is fully transparent at that row`.
3. Neither verdict may be a restatement of the warning, and none of `looks fine`, `intentional`, `by design`, `no overlap`, `acceptable`, or `everything fits` closes a warning. An observation that names no coordinate, element, or measurable relationship is rejected and the slide returns unresolved.
4. `CONFIRM` sets the mapped check to `fail`. `REFUTE` may set it to `pass`, but the refutation text is retained in `notes` so the next run can be compared against it.
5. A warning may not be closed by the author, by the reviewer that wrote the slide, or by any reviewer reusing an earlier observation.

`validate_visual_review.py` already routes every automation-warning slide into `cross_review_batches` — `required_cross_review_slides()` is the union of visual-critical, identity-required, and automation-warning slides — so a warned slide is always adjudicated twice.

## Two independent lenses

Cross-review exists to catch what the first lens is structurally unable to see. Running the same checklist twice is not independence.

- **Primary lens — composition as built.** Slide-local. Does each element sit where the layout intends, does each image serve its declared role, does the copy read. Enters with the slide's checks and the debug overlay.
- **Cross-review lens — composition as received.** Deck-level and adversarial. Enters with the pending batch, the warning text, and the two previous observations, and is told to try to break them: what would an audience member in the back row misread, what does the earlier slide already say, which element would you delete. It must not reuse the primary wording or any reviewer reference from the primary set.

Every cross-reviewer is outside the complete primary-reviewer set, not merely different from the reviewer assigned to that slide.

## Reviewer sweep — only what a machine cannot measure

Container overflow, glyph-row collision, foreground bite into text ink, navigation-zone intrusion, subject prominence, and near-duplicate skeletons are measured. Do not spend review turns re-deriving them by eye. Spend the turns on what no gate can reach:

1. **Does the image show the thing it claims?** Subject, variant, era, package, uniform, interface state. Filenames, alt text, folders, and source tags are not evidence.
2. **Is the media generated where it must be authentic?** A generated `source_kind` in a subject, evidence, or identity role blocks delivery even when the pixels look plausible.
3. **Does the crop still contain the meaning?** Cut logos, faces, product edges, title art, map keys, axis labels.
4. **Is the raster genuinely sharp at playback size?** Prior upscales, ringing, mosquito noise, banding, and unreadable embedded text pass the pixel-density gate and still fail here.
5. **Does the slide finish?** Placeholders, `PLACE NOTE`, empty media frames, repeated generic stand-ins, dummy assets.
6. **Does the composition have a focal point?** One dominant element, an obvious reading order, evidence beside its claim.
7. **Escape hatches.** Any `data-*-ok` attribute on the slide must be justified in the observation.

Report the result as a concrete observation naming visible elements and their locations. `Everything fits` is not evidence of anything.

## Non-negotiable blocking gates

Each of these blocks delivery on a single occurrence, independently of the 24-point score and independently of every other dimension being strong. A deck may not be delivered at 21/24 with one of these open.

1. A near-duplicate slide pair reported by `validate_slide_variety.py` and not opted out with a matching `data-variety-ok` token on both slides.
2. Any visible placeholder, `PLACE NOTE`, temporary or dummy asset, empty media frame, or generic replacement graphic standing in for a promised real subject image.
3. Generated media occupying a subject, evidence, or identity role for an existing named person, group, product, place, event, released work, interface, or measured result.
4. A wrong subject, wrong variant, or unverifiable identity on an identity-routed slide.
5. An unresolved deterministic warning — no `CONFIRM` or `REFUTE` on record for it.
6. A reviewer `fail` rewritten to `pass` without a new render and a new capture hash.
7. A cover that fails `cover-design.md` as a cover, however clean its geometry.
8. Prompt residue — validation mode, slide count, requested workflow, image quantity, `개념 강의 + 팀 활동` — rendered as visible decorative metadata with no audience-facing reason.

## Reviewer capabilities

Both `build-html-slides-visual-reviewer` and `build-html-slides-quality-editor` hold `Read`, `Glob`, and `Grep` only. They cannot render, run a validator, write `review.json`, search the web, or fetch a replacement asset. They open the exact paths the parent hands them and return findings; the parent writes every record with `record_review.py`. Never ask a reviewer to do anything else, and never treat a reviewer's declaration as proof that a vision call occurred — it is an agent-provided record.
