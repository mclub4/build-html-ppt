# Time-Aware Fan-Art Discovery

Use this contract when a request asks for many fan artworks, as many images as possible, character galleries, creator-community imagery, or a fan-art-heavy deck. Full Validation increases assurance; it does not require exhaustive image research.

## Default Targets

These are planning targets, not hard limits:

- total delivery target: 60-90 minutes for 20-25 slides;
- fan-art search target: 25-35 minutes;
- candidate target: 40-50 works;
- selected fan-art target: 24-30 works;
- normally one contact-sheet selection pass;
- normally one replacement pass affecting no more than 20% of selected works;
- aim to freeze asset selection around minute 35-40 and preserve the final 25-35 minutes for implementation and validation.

Reaching the upper end of a target does not terminate the task. Use it as a checkpoint: inspect visual-role coverage, candidate quality, diversity, and remaining validation time. Freeze the set when it is already strong. Continue searching when the expected improvement is meaningful and the schedule remains reasonable. If the task is likely to exceed 90 minutes, explain the cause and ask whether to continue discovery or finish with the current candidates; do not abruptly stop.

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
- If further rights verification would push the task beyond 90 minutes, ask whether to continue verification or replace the affected work.

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
- Image count alone does not make a slide critical. `data-visual-critical="true"` requests additional stress profiles; Full Validation independently cross-reviews every slide after the primary pass.
- Do not create auxiliary fan-art, source, or rights-review agents for an ordinary internal/private entertainment deck. Standard Full Validation uses its two primary reviewers and one final editor only.
- Low-resolution, failed-load, crop, or attribution problems may replace the affected work once; they do not reopen broad discovery.

If external access, login, rate-limit, download, or rights problems threaten the target duration, checkpoint the work. Reduce the selected quantity when quality remains sufficient, or ask whether to continue when more research is materially useful. Never claim exhaustive coverage without actually performing it.
