# High-Volume Sourced Media

Use this workflow when a presentation needs many distinct images of existing subjects and serial image research would dominate the schedule. Examples include products and menu items, artworks, athletes, performers, characters, travel destinations, buildings, archival objects, interfaces, scientific specimens, or multiple photos of one named subject. Apply it from the actual media burden, not a keyword or a fixed slide-count parser.

The goal is not to weaken factual or identity review. It is to move cheap checks earlier, batch visual judgment, and reserve expensive research for the candidates that actually fail.

## 1. Freeze a media roster

Before broad search, write an authoring-only JSON roster. Give each required subject:

- a stable `id`;
- the exact audience-facing `label`;
- `kind`, such as `product`, `artwork`, `person`, `place`, `interface`, or `evidence`;
- one short visible `cue` that distinguishes the intended subject or variant;
- the planned slide or visual role;
- the expected slot size or minimum useful source pixels.

The cue must fit the subject:

- product or food: exact flavor, package generation, manufacturer, size, or regional variant;
- artwork: title, attributed artist, year or edition when relevant, and a visible composition cue;
- person or athlete: canonical facial, uniform, era, team, or event cues;
- character: canonical costume, hair, insignia, silhouette, or other identity cues;
- place or building: landmark, facade, viewpoint, season, or location cue;
- interface or device: exact product/version and the state being explained;
- scientific or historical evidence: specimen, modality, date, collection, or source context.

Keep the roster private. It is not slide copy.

## 2. Use a lightweight discovery gate

Search in parallel by roster item. Initially retain one strong candidate and at most one fallback for each item. Before downloading, check only:

1. the page and image appear to name the correct subject, work, person, place, product, or variant;
2. the source page is recorded and fits the distribution context;
3. the original has enough pixels for the planned slot;
4. the candidate has no obvious disqualifier such as an unrelated collage, visible stock watermark, or tiny search thumbnail.

Do not repeatedly open, crop, convert, render, and deep-review each item in isolation. Do not reverse-search every candidate before seeing whether it survives the batch. Public or commercial rights checks still follow the source contract, but perform them as a metadata pass over the selected set rather than rediscovering unchanged sources.

## 3. Acquire and normalize once

Download the selected originals in one batch, convert them to local WebP once, and update `sources.json`. Preserve one canonical reference per named person or character when identity review requires it; several candidates for the same subject can share that reference. Reuse unchanged cached files and source records.

Create a manifest outside the deliverable directory:

```json
{
  "title": "Artwork candidate audit",
  "items": [
    {
      "id": "work-01",
      "label": "Banksy — Girl with Balloon",
      "kind": "artwork",
      "path": "../../project/assets/girl-with-balloon.webp",
      "cue": "Girl silhouette reaching toward one red heart-shaped balloon",
      "source_url": "https://example.org/source-page",
      "planned_use": "slide 4 hero",
      "min_width": 1400,
      "min_height": 900
    }
  ]
}
```

Run one Chromium process for batches of up to twelve:

```bash
node scripts/build_media_contact_sheet.js MEDIA-ROSTER.json WORKSPACE/tmp/media-audit
```

The tool creates numbered PNG contact sheets and an index containing local hashes, intrinsic dimensions, duplicate groups, expected labels, distinguishing cues, and source hosts.

## 4. Review batches, not files

Open each contact sheet once with vision. Compare every visible image to its expected label and cue. Flag only:

- wrong subject, person, character, work, place, flavor, package, version, era, team, or event;
- uncertain attribution or an image too small to verify;
- thumbnail softness, prior upscaling, severe compression, watermark, or unusable intrinsic whitespace;
- a source whose composition cannot survive the planned crop;
- duplicates that do not have a deliberate narrative reason.

Do not turn the batch review into a new source search. Deep-research and replace only flagged items, then regenerate only the affected sheet. For several photos of one person or character, compare the batch against one canonical reference rather than rediscovering identity for every file. For many different people or characters, keep one canonical reference per subject and review them in batches.

## 5. Compose once, then inspect usage

After the candidate set passes, place all selected media and render the presentation once. The media contact sheet proves candidate suitability; the full-size slide captures prove actual crop, aspect ratio, sharpness at rendered size, caption relationship, text occlusion, and navigation clearance. They are different checks.

Use the normal slide captures for the full visual pass. Let deterministic geometry inspect stress profiles. If a slide or asset fails, replace that asset and rerender only the implicated slide unless shared layout or runtime changed. Do not restart source discovery, contact-sheet review, or unaffected slide review.

## Mode behavior

- **Quick Draft**: use the roster and lightweight discovery gate, but do not run Chromium or AI review. Build with the selected candidates and disclose that image identity, crop, and visual quality were not validated.
- **Full Validation**: use the batch contact-sheet pass when the number or diversity of sourced subjects makes serial inspection expensive. This is an authoring accelerator, not another mandatory review layer for every presentation. Final slide review remains required, but it must not reopen every source page or repeat candidate-level investigation for assets that passed and did not change.

## Stop rule

Stop broad media research when every required visual role has one plausible candidate and the batch has enough diversity to tell the story. Improve only flagged, weak, duplicated, or compositionally unusable items. “Find as many as possible” is a coverage instruction, not permission for an unbounded search.
