# Bounded Fan-Art Discovery

Use this contract when a request asks for many fan artworks, as many images as possible, character galleries, creator-community imagery, or a fan-art-heavy deck. Full Validation increases assurance; it does not authorize unbounded image research.

## Default Envelope

Unless the user explicitly accepts a longer exhaustive search after being warned that it may exceed two hours:

- target total delivery time: 90 minutes;
- hard delivery envelope: 120 minutes;
- fan-art search target: 30 minutes, hard stop at 40 minutes;
- candidate target: 40, hard stop at 50;
- selected fan-art target: 24, hard stop at 30;
- one contact-sheet selection pass;
- one replacement pass affecting at most 20% of selected works;
- freeze asset selection before minute 45 and preserve the remaining time for implementation and validation.

Interpret "maximum," "as many as possible," and similar superlatives as "the strongest varied set within this envelope." Do not silently convert them into exhaustive platform crawling. If the requested slide count cannot present the selected works legibly, select fewer works rather than making denser galleries or extending the search.

## Provenance By Distribution

### Internal Or Private

- A discovery URL and visible creator name/handle are sufficient.
- Set `source_kind: fan-art` and `origin_status: discovery-only` in `sources.json`.
- `verified_at` records when the discovery URL and visible credit were checked; it does not claim ownership or permission.
- Preserve signatures and watermarks. Reject work with intentionally removed attribution.
- Do not reverse-image-search, hop across platforms, or inspect repost history unless the user explicitly requests strict provenance.

### Public Or Commercial

- Use origin-verified, licensed, supplied, official, or original assets.
- If rights cannot be established inside the same 40-minute research ceiling, skip or replace the work.
- Prefer a smaller verified set over extending the task or presenting uncertain fan art as cleared.

## Efficient Collection

1. Search the highest-yield direct platforms first using the character's native name and established tags.
2. Collect candidates into the validation workspace, not the deliverable assets folder.
3. Deduplicate before conversion. Do not download cosmetic re-encodes of the same work.
4. Make one contact sheet and select the final set in one pass.
5. Convert only selected works to WebP. Default to a longest edge of 2560px and quality 82-88; retain larger sources only for a documented deep crop.
6. Record only selected deliverable assets in `sources.json`.
7. After selection freezes, reopen search only for a broken, duplicate, unusably small, or clearly mismatched asset, and keep replacements within the one-pass limit.

## Validation Scope

- Validate fan art as part of the rendered slide, not with a separate AI call per artwork.
- Batch up to four slide captures per vision call as defined by `slide-by-slide-review.md`.
- Image count alone does not make a slide critical. Only `data-visual-critical="true"` requests stress-profile and final independent cross-review treatment.
- Do not create auxiliary fan-art, source, or rights-review agents for an ordinary internal/private entertainment deck. Standard Full Validation uses its two primary reviewers and one final editor only.
- Low-resolution, failed-load, crop, or attribution problems may replace the affected work once; they do not reopen broad discovery.

If the bounded envelope cannot be met because of external access, login, rate-limit, download, or rights problems, reduce the selected quantity and report the limitation. Never claim exhaustive coverage.
