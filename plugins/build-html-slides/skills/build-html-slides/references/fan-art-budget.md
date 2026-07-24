# Time-Aware Fan-Art Discovery

Use this contract when a request asks for many fan artworks, as many images as possible, character galleries, creator-community imagery, or a fan-art-heavy deck. Full Validation increases assurance; it does not require exhaustive image research. When the roster reaches the numeric trigger in `high-volume-media-workflow.md`, run the batch contact-sheet accelerator instead of inspecting downloads one by one.

## Default Targets

An image-heavy deck uses the same envelope as every other Full Validation deck: **70 minutes maximum for 20-25 slides**, as defined in `validation-contract.md`. There is no separate, longer fan-art budget. Discovery is allocated inside it:

- fan-art search: 20 minutes, hard ceiling;
- candidates: 40 works;
- selected works: 24-30;
- one contact-sheet selection pass;
- one replacement pass affecting no more than 20% of selected works;
- asset selection freezes at minute 20 so the validation pipeline keeps its full allowance.

Hitting a ceiling is an instruction, not a suggestion. At the 20-minute mark, freeze the set you have and move on; a strong set of 24 works delivered on time beats 30 works delivered late. If coverage is genuinely thin at that point, cut slides rather than extend the search — fewer works presented legibly is the better deck either way.

Apply the autonomous budget checkpoint in `validation-contract.md` when `validate_all.py --status` reports the allowance running short. Do not ask the user whether to continue searching; decide, act, and state what was reduced at delivery.

Interpret "maximum," "as many as possible," and similar superlatives as a request for a strong and varied set, not an automatic instruction to crawl every platform exhaustively. If the requested slide count cannot present the selected works legibly, prefer fewer stronger works over dense galleries. When the user explicitly prioritizes exhaustive coverage, adapt the targets and communicate the expected duration.

## Provenance By Distribution

### Internal Or Private

- A discovery URL and visible creator name/handle are sufficient.
- Set `source_kind: fan-art` and `origin_status: discovery-only` in `sources.json`.
- `verified_at` records when the discovery URL and visible credit were checked; it does not claim ownership or permission.
- Preserve signatures and watermarks. Reject work with intentionally removed attribution.
- Do not reverse-image-search, hop across platforms, or inspect repost history unless the user explicitly requests strict provenance.

### Public Or Commercial

- Use origin-verified, licensed, supplied, official, or original assets.
- At the research checkpoint, prefer a smaller verified set over presenting uncertain fan art as cleared.
- If further rights verification would exceed the discovery ceiling, replace the affected work with a verified alternative or drop it. Do not spend the budget asking.

## Efficient Collection

1. Search the highest-yield direct platforms first using the character's native name and established tags.
2. Collect candidates into the validation workspace, not the deliverable assets folder.
3. Deduplicate before conversion. Do not download cosmetic re-encodes of the same work.
4. Normally make one contact sheet and select the final set in one pass. Split it only when the number or visual variety of candidates makes one sheet unreadable.
5. Convert only selected works to WebP. Default to a longest edge of 2560px and quality 82-88; retain larger sources only for a documented deep crop.
6. Record only selected deliverable assets in `sources.json`.
7. After selection freezes, reopen search only for a broken, duplicate, unusably small, or clearly mismatched asset. Prefer one focused replacement pass; expand it only when the rendered deck reveals a broader visual problem.

## Validation Scope

- Validate fan art as part of the rendered slide, not with a separate AI call per artwork.
- Batch up to four slide captures per vision call as defined by `slide-by-slide-review.md`.
- Image count alone does not make a slide critical. `data-visual-critical="true"` requests additional stress profiles and inclusion in the focused final cross-review set. Ordinary slides are not sampled merely because the deck is image-heavy, and high-risk Full Validation does not automatically cross-review every slide.
- Do not create auxiliary fan-art, source, or rights-review agents for an ordinary internal/private entertainment deck. Standard Full Validation uses its two primary reviewers and one final editor only.
- Low-resolution, failed-load, crop, or attribution problems may replace the affected work once; they do not reopen broad discovery.

If external access, login, rate-limit, download, or rights problems threaten the ceiling, reduce the selected quantity and continue. Deliver on time with a stated limitation rather than asking for more time. Never claim exhaustive coverage without actually performing it.
