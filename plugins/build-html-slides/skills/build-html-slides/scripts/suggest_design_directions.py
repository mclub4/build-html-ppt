#!/usr/bin/env python3
"""Rank presentation design candidates from semantic facets selected by the agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "references" / "design-candidates.json"


def distance_score(value: int, bounds: list[int], weight: float) -> float:
    low, high = bounds
    if low <= value <= high:
        return weight
    return max(0.0, weight - min(abs(value - low), abs(value - high)) * (weight / 5))


def score_candidate(candidate: dict, args: argparse.Namespace) -> float:
    score = 0.0
    if args.subject_family in candidate["subject_families"]:
        score += 8
    if args.communication_job in candidate["communication_jobs"]:
        score += 7
    if args.luminosity == "any" or args.luminosity in candidate["luminosity"]:
        score += 4
    score += distance_score(args.density, candidate["density_range"], 3)
    score += distance_score(args.media_need, candidate["media_need_range"], 3)
    score += distance_score(args.variance, candidate["variance_range"], 3)
    score += distance_score(args.motion, candidate["motion_range"], 2)
    return score


def choose_diverse(ranked: list[tuple[float, dict]], count: int = 3) -> list[tuple[float, dict]]:
    chosen: list[tuple[float, dict]] = []
    remaining = list(ranked)
    while remaining and len(chosen) < count:
        best_index = 0
        best_value = float("-inf")
        for index, (base_score, candidate) in enumerate(remaining):
            penalty = 0.0
            for _score, selected in chosen:
                if set(candidate["luminosity"]) == set(selected["luminosity"]):
                    penalty += 0.8
                overlap = set(candidate["composition_families"]) & set(selected["composition_families"])
                penalty += min(1.5, len(overlap) * 0.5)
            value = base_score - penalty
            if value > best_value:
                best_index, best_value = index, value
        chosen.append(remaining.pop(best_index))
    return chosen


def parser_for(data: dict) -> argparse.ArgumentParser:
    contract = data["selection_contract"]
    parser = argparse.ArgumentParser(
        description=(
            "Return three presentation design candidates after the agent has semantically selected "
            "subject family, communication job, and design dials. This tool does not parse raw prompts."
        )
    )
    parser.add_argument("--subject-family", required=True, choices=contract["subject_families"])
    parser.add_argument("--communication-job", required=True, choices=contract["communication_jobs"])
    parser.add_argument("--luminosity", default="any", choices=["any", *contract["luminosity"]])
    parser.add_argument("--density", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--media-need", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--variance", type=int, default=5, choices=range(1, 11))
    parser.add_argument("--motion", type=int, default=4, choices=range(1, 11))
    parser.add_argument("--exclude", action="append", default=[], help="candidate id to exclude")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    args = parser_for(data).parse_args()
    excluded = set(args.exclude)
    ranked = sorted(
        (
            (score_candidate(candidate, args), candidate)
            for candidate in data["candidates"]
            if candidate["id"] not in excluded
        ),
        key=lambda item: (-item[0], item[1]["id"]),
    )
    selected = choose_diverse(ranked)
    result = {
        "input": {
            "subject_family": args.subject_family,
            "communication_job": args.communication_job,
            "luminosity": args.luminosity,
            "density": args.density,
            "media_need": args.media_need,
            "variance": args.variance,
            "motion": args.motion,
        },
        "candidates": [
            {
                "rank": index,
                "score": round(score, 2),
                **candidate,
            }
            for index, (score, candidate) in enumerate(selected, 1)
        ],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for candidate in result["candidates"]:
        print(
            f"{candidate['rank']}. {candidate['name']} ({candidate['score']}) | "
            f"luminosity={','.join(candidate['luminosity'])} | "
            f"compositions={', '.join(candidate['composition_families'][:3])}"
        )


if __name__ == "__main__":
    main()
