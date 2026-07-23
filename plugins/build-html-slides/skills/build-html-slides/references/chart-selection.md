# Chart Selection

Choose a chart only after stating the slide claim and data shape. Topic nouns do not select charts.

```bash
python3 scripts/suggest_chart.py --data-shape uncertainty --category-count 6 --json
```

The machine-readable table records when each form works, when it should be avoided, a category ceiling, and non-color encodings. Treat the ceiling as a readability warning: split, filter, small-multiple, or use a precise table when the audience must retrieve many values.

## Rules

1. Put the claim in the slide title; do not title a slide only `Revenue` or `Results`.
2. Do not use a chart when one number, a short comparison, a process, or a source image makes the point more directly.
3. Use position, length, line style, marker shape, pattern, direct labels, and ordering so meaning does not depend on color alone.
4. State units, date range, denominator, source, and uncertainty where consequential.
5. Avoid pies or donuts for precise comparison, dual axes without a compelling shared interpretation, and decorative 3D perspective.
6. Preserve honest scales. If an axis is truncated, make the break and reason unmistakable.
7. For room presentation, reduce series and annotations to the claim. Put exact supporting values in notes or a companion table.
