# Character And Person Identity Review

Use this contract whenever a slide claims that one or more images depict a named fictional character or real person. It applies to official art, screenshots, fan art, photos, generated images, alternate costumes, younger/older forms, and group scenes.

## Ground The Identity

Before selecting candidate images, obtain one local WebP reference per subject from an official, licensed, or user-supplied authoritative source. Prefer a clear front-facing portrait or character sheet over stylized fan work. `source_cache.py` collects `data-identity-reference` even when that file is not displayed as an `<img>` and records its `identity-reference` role in `sources.json`. Note at least two stable visual cues: hair and eye treatment, silhouette, halo, ears or horns, signature clothing, emblem, weapon, accessory, age, or named form.

Do not accept a filename, folder, alt text, repost caption, search tag, or source-page tag as proof that the rendered subject is correct. Compare the pixels. When two characters are easily confused, include a cue that distinguishes them. When the requested form matters, identity includes the correct costume, age, transformation, or variant.

## HTML Contract

Annotate every character/person profile, gallery, comparison, or image-led slide:

```html
<section class="slide" data-title="Character profile" data-identity-review="required">
  <div class="slide-media" aria-hidden="true"></div>
  <div class="slide-content">
    <img
      src="assets/mari/fan-art-01.webp"
      alt="Mari fan art"
      data-subject-id="bluearchive:mari"
      data-subject-name="Mari / 마리"
      data-identity-reference="assets/identity/mari-official.webp"
      data-identity-cues="blonde hair; cat ears; Trinity halo; white nun habit"
      data-identity-mode="primary">
  </div>
</section>
```

- `primary`: the named subject must be the visually dominant person.
- `contains`: the named subject must be clearly present in a group image.
- Identity review activates when the slide is explicitly marked, any subject/reference metadata is present, `data-slide-kind`/`data-content-kind` declares a named subject, or character/person/profile markup is detected. Omitting the slide flag does not bypass review.
- Every meaningful image on an identity-required slide needs a subject ID, readable name, local WebP reference, and at least two semicolon-separated cues.
- The candidate and reference must be different local files inside the deck bundle.
- Decorative imagery belongs in `.slide-media`, remains excluded from identity review, and must not be used to make a factual identity claim.

Missing or invalid metadata blocks AI review. Automatically detected identity slides always receive at least one full-size AI inspection in Quick Draft as well as Full Validation. Use `data-identity-review="not-applicable"` only when profile-like markup describes a product or other non-person subject and no subject identity metadata is present.

## Rendered Review

For every entry in `identity_targets`, open both the rendered slide PNG and `reference_path`. Judge the pixels without relying on labels. Record one `identity_review` result per target:

```json
{
  "target_id": "slide-7-identity-1",
  "subject_name": "Mari / 마리",
  "verdict": "pass",
  "observation": "The candidate and official reference share the blonde bob, cat ears, Trinity halo, and white nun habit; no conflicting character cues are visible."
}
```

Fail when identity is uncertain, a lookalike is more likely, the intended variant is wrong, the named subject is too small to verify, a `primary` subject is not dominant, or the image conflicts with the slide's claim, tone, spoiler boundary, or audience. Replace uncertain imagery instead of rationalizing it.

The primary reviewer performs this comparison. During Full Validation, the quality editor repeats identity and appropriateness checks while inspecting every normal capture; critical identity slides also need hash-bound `identity_review` entries in their independent cross-review.
