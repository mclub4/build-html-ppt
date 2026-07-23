#!/usr/bin/env python3
"""Suggest chart forms from an explicit data shape instead of topic keywords."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "references" / "chart-selection.json"


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    shapes = sorted({shape for chart in data["charts"] for shape in chart["data_shapes"]})
    parser = argparse.ArgumentParser(description="Rank charts after the agent identifies the data shape.")
    parser.add_argument("--data-shape", required=True, choices=shapes)
    parser.add_argument("--category-count", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.category_count < 1:
        parser.error("--category-count must be at least 1")

    ranked = []
    for chart in data["charts"]:
        if args.data_shape not in chart["data_shapes"]:
            continue
        over_limit = args.category_count > chart["max_categories"]
        ranked.append({
            **chart,
            "fit": "avoid" if over_limit else "candidate",
            "reason": (
                f"category count {args.category_count} exceeds the recommended maximum "
                f"of {chart['max_categories']}"
                if over_limit else chart["use_when"]
            ),
        })
    ranked.sort(key=lambda chart: (chart["fit"] == "avoid", chart["id"]))
    result = {"data_shape": args.data_shape, "category_count": args.category_count, "charts": ranked}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for chart in ranked:
        print(f"{chart['id']}: {chart['fit']} - {chart['reason']}")


if __name__ == "__main__":
    main()
