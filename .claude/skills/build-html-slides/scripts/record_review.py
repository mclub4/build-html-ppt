#!/usr/bin/env python3
"""Safely record explicit human or vision-agent review observations in review.json."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path


QUALITY_DIMENSIONS = (
    "story", "art_direction", "layout_rhythm", "typography",
    "imagery", "composition", "evidence", "presentation_utility",
)
CONTRACT = json.loads(
    Path(__file__).with_name("validation_contract.json").read_text(encoding="utf-8")
)
SQUINT_REVIEW_CHECKS = tuple(CONTRACT["squint_review_checks"])


def fail(parser: argparse.ArgumentParser, message: str) -> None:
    parser.error(message)


def parse_checks(parser: argparse.ArgumentParser, values: list[str], expected: list[str]) -> dict[str, str]:
    checks: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            fail(parser, f"invalid --check {value!r}; use name=pass|fail")
        name, verdict = (part.strip() for part in value.split("=", 1))
        if name in checks or name not in expected or verdict not in {"pass", "fail"}:
            fail(parser, f"each expected check must appear exactly once: {', '.join(expected)}")
        checks[name] = verdict
    if set(checks) != set(expected):
        fail(parser, f"each expected check must appear exactly once: {', '.join(expected)}")
    return {name: checks[name] for name in expected}


def require_observation(parser: argparse.ArgumentParser, value: str) -> str:
    observation = " ".join(value.split())
    if len(observation) < 24:
        fail(parser, "observation must contain a concrete visual finding of at least 24 characters")
    return observation


def atomic_write(path: Path, data: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(temporary).replace(path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def update_batch_status(manifest: dict, batch_key: str, records_key: str, batch_id: str) -> None:
    records = [
        record for record in manifest.get(records_key, [])
        if record.get("review_batch_id") == batch_id
    ]
    for batch in manifest.get(batch_key, []):
        if batch.get("id") == batch_id:
            batch["status"] = "complete" if records and all(
                record.get("status") in {"pass", "fail"} for record in records
            ) else "pending"
            return


def record_slide(
    parser: argparse.ArgumentParser,
    manifest: dict,
    args: argparse.Namespace,
    *,
    cross: bool,
) -> None:
    records_key = "cross_reviews" if cross else "slides"
    batch_key = "cross_review_batches" if cross else "review_batches"
    records = manifest.get(records_key)
    if not isinstance(records, list):
        fail(parser, f"manifest has no {records_key}")
    record = next((item for item in records if item.get("slide") == args.slide), None)
    if not isinstance(record, dict):
        fail(parser, f"slide {args.slide} is not present in {records_key}")
    expected_profiles = list(record.get("required_ai_profiles", [])) if not cross else list(
        next(
            (
                item.get("capture_profiles", {}).get(str(args.slide), [])
                for item in manifest.get(batch_key, [])
                if item.get("id") == record.get("review_batch_id")
            ),
            record.get("inspected_profiles", []),
        )
    )
    inspected = [item.strip() for item in args.inspected.split(",") if item.strip()]
    if inspected != expected_profiles:
        fail(parser, f"--inspected must exactly match current required profiles: {','.join(expected_profiles)}")
    checks = parse_checks(parser, args.check, list(record.get("checks", {})))
    if args.status == "pass" and any(value != "pass" for value in checks.values()):
        fail(parser, "status=pass requires every explicit check to pass")
    if args.status == "fail" and all(value == "pass" for value in checks.values()):
        fail(parser, "status=fail requires at least one explicit failed check")

    record["reviewer"] = args.reviewer.strip()
    record["reviewer_ref"] = args.reviewer_ref.strip()
    record["inspected_profiles"] = inspected
    record["observation"] = require_observation(parser, args.observation)
    record["checks"] = checks
    record["status"] = args.status
    if args.note:
        record["notes"] = [" ".join(value.split()) for value in args.note if value.strip()]
    batch_id = str(record.get("review_batch_id", ""))
    if batch_id:
        update_batch_status(manifest, batch_key, records_key, batch_id)


def record_quality(
    parser: argparse.ArgumentParser,
    manifest: dict,
    args: argparse.Namespace,
) -> None:
    score = manifest.get("quality_score")
    if not isinstance(score, dict):
        fail(parser, "manifest has no quality_score")
    dimensions: dict[str, int] = {}
    for value in args.dimension:
        if "=" not in value:
            fail(parser, f"invalid --dimension {value!r}; use name=0..3")
        name, raw_score = (part.strip() for part in value.split("=", 1))
        if name in dimensions or name not in QUALITY_DIMENSIONS:
            fail(parser, f"each quality dimension must appear exactly once: {', '.join(QUALITY_DIMENSIONS)}")
        try:
            dimension_score = int(raw_score)
        except ValueError:
            fail(parser, f"quality dimension {name} must be an integer from 0 to 3")
        if dimension_score < 0 or dimension_score > 3:
            fail(parser, f"quality dimension {name} must be an integer from 0 to 3")
        dimensions[name] = dimension_score
    if set(dimensions) != set(QUALITY_DIMENSIONS):
        fail(parser, f"each quality dimension must appear exactly once: {', '.join(QUALITY_DIMENSIONS)}")

    slide_count = len(manifest.get("slides", []))
    weakest = []
    for value in args.weakest.split(","):
        try:
            number = int(value.strip())
        except ValueError:
            fail(parser, "--weakest must be a comma-separated list of slide numbers")
        if number < 1 or number > slide_count or number in weakest:
            fail(parser, "--weakest must contain distinct valid slide numbers")
        weakest.append(number)
    required_count = min(3, slide_count)
    if len(weakest) != required_count:
        fail(parser, f"--weakest must contain exactly {required_count} slide numbers")

    total = sum(dimensions.values())
    if args.status == "pass" and (total < 20 or min(dimensions.values()) < 2):
        fail(parser, "status=pass requires at least 20/24 and every dimension at least 2")
    if args.status == "fail" and total >= 20 and min(dimensions.values()) >= 2:
        fail(parser, "status=fail requires a score below the Full Validation threshold")

    score.update({
        "status": args.status,
        "reviewer": args.reviewer.strip(),
        "reviewer_ref": args.reviewer_ref.strip(),
        "dimensions": {name: dimensions[name] for name in QUALITY_DIMENSIONS},
        "total": total,
        "weakest_slides": weakest,
        "notes": require_observation(parser, args.observation),
    })


def record_squint(
    parser: argparse.ArgumentParser,
    manifest: dict,
    args: argparse.Namespace,
) -> None:
    review = manifest.get("squint_review")
    if not isinstance(review, dict):
        fail(parser, "manifest has no generated squint_review; run finalize-prepare first")
    checks = parse_checks(parser, args.check, list(SQUINT_REVIEW_CHECKS))
    if args.status == "pass" and any(value != "pass" for value in checks.values()):
        fail(parser, "status=pass requires every explicit check to pass")
    if args.status == "fail" and all(value == "pass" for value in checks.values()):
        fail(parser, "status=fail requires at least one explicit failed check")
    review.update({
        "status": args.status,
        "reviewer": args.reviewer.strip(),
        "reviewer_ref": args.reviewer_ref.strip(),
        "checks": checks,
        "observation": require_observation(parser, args.observation),
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    subparsers = parser.add_subparsers(dest="kind", required=True)
    for name in ("slide", "cross-slide"):
        command = subparsers.add_parser(name)
        command.add_argument("--slide", type=int, required=True)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--reviewer-ref", required=True)
        command.add_argument("--status", choices=("pass", "fail"), required=True)
        command.add_argument("--observation", required=True)
        command.add_argument("--inspected", required=True)
        command.add_argument("--check", action="append", default=[], required=True)
        command.add_argument("--note", action="append", default=[])
    quality = subparsers.add_parser("quality")
    quality.add_argument("--reviewer", required=True)
    quality.add_argument("--reviewer-ref", required=True)
    quality.add_argument("--status", choices=("pass", "fail"), required=True)
    quality.add_argument("--observation", required=True)
    quality.add_argument("--dimension", action="append", default=[], required=True)
    quality.add_argument("--weakest", required=True)
    squint = subparsers.add_parser("squint")
    squint.add_argument("--reviewer", required=True)
    squint.add_argument("--reviewer-ref", required=True)
    squint.add_argument("--status", choices=("pass", "fail"), required=True)
    squint.add_argument("--observation", required=True)
    squint.add_argument("--check", action="append", default=[], required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    path = args.manifest.resolve()
    if not path.is_file():
        parser.error(f"manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"manifest is invalid JSON: {exc}")
    if args.kind == "slide":
        record_slide(parser, manifest, args, cross=False)
    elif args.kind == "cross-slide":
        record_slide(parser, manifest, args, cross=True)
    elif args.kind == "quality":
        record_quality(parser, manifest, args)
    elif args.kind == "squint":
        record_squint(parser, manifest, args)
    atomic_write(path, manifest)
    print(f"OK: recorded explicit {args.kind} review in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
