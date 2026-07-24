#!/usr/bin/env python3
"""Safely record explicit human or vision-agent review observations in review.json."""

from __future__ import annotations

import argparse
import json
import os
import shlex
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

# references/reviewer-gates.md, "Refute-or-confirm": a slide carrying a
# deterministic warning may not be closed with a general approval. The reviewer
# must open the boundary overlay and answer the warning with one of these two
# verdicts as the first token of the observation.
VERDICT_PREFIXES = ("CONFIRM:", "REFUTE:")

# The verdict body has to name something a later run can be compared against.
# These are deterministic proxies for "names an element and a location", chosen
# so the exact approvals that let the shipped defects through are rejected:
# "an intentional connecting rule that does not cover the product" carries no
# number, and "no overlap" carries neither number nor distinct vocabulary.
VERDICT_BODY_MIN_CHARS = 40
VERDICT_BODY_MIN_WORDS = 6


def normalized(value: str) -> str:
    return " ".join(value.lower().split())


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


def slide_warnings(manifest: dict, slide: int) -> list[str]:
    """Deterministic warnings raised against one slide by --phase prepare."""
    gate = manifest.get("automation_gate")
    if not isinstance(gate, dict):
        return []
    entries = gate.get("warnings")
    if not isinstance(entries, list):
        return []
    return [
        str(entry.get("warning", "")).strip()
        for entry in entries
        if isinstance(entry, dict) and entry.get("slide") == slide and str(entry.get("warning", "")).strip()
    ]


def require_warning_verdict(
    parser: argparse.ArgumentParser,
    warnings: list[str],
    observation: str,
    checks: dict[str, str],
    status: str,
) -> str:
    """Enforce the refute-or-confirm pass for a slide that carries a warning."""
    if not warnings:
        if observation.startswith(VERDICT_PREFIXES):
            fail(
                parser,
                "CONFIRM/REFUTE is reserved for slides carrying a deterministic warning; "
                "this slide has none in automation_gate.warnings",
            )
        return observation
    prefix = next((item for item in VERDICT_PREFIXES if observation.startswith(item)), "")
    if not prefix:
        fail(
            parser,
            "this slide carries a deterministic warning and enters the refute-or-confirm pass: "
            "the observation must begin with 'CONFIRM: ' or 'REFUTE: ' "
            f"({len(warnings)} warning(s): {' | '.join(warnings)})",
        )
    body = observation[len(prefix):].strip()
    if len(body) < VERDICT_BODY_MIN_CHARS or len(set(body.split())) < VERDICT_BODY_MIN_WORDS:
        fail(
            parser,
            f"a {prefix} verdict needs at least {VERDICT_BODY_MIN_CHARS} characters and "
            f"{VERDICT_BODY_MIN_WORDS} distinct words naming the element and where it sits",
        )
    if not any(character.isdigit() for character in body):
        fail(
            parser,
            f"a {prefix} verdict must name a coordinate, size, or distance the next run can be "
            "compared against; a generic approval does not close a warning",
        )
    compact = normalized(body)
    for warning in warnings:
        if compact and compact in normalized(warning):
            fail(parser, f"a {prefix} verdict must not restate the warning text back to the recorder")
    if prefix == "CONFIRM:":
        if status != "fail" or all(value == "pass" for value in checks.values()):
            fail(parser, "CONFIRM means the warning is real: record --status fail with the mapped check failed")
    return observation


def require_debug_inspection(
    parser: argparse.ArgumentParser,
    record: dict,
    supplied: list[str],
) -> list[str]:
    """A warned or failed slide has a boundary overlay; the reviewer must open it."""
    available = record.get("debug_captures")
    available = sorted(available) if isinstance(available, dict) else []
    inspected = sorted({item.strip() for item in supplied if item.strip()})
    if inspected and not available:
        fail(parser, "--inspected-debug was supplied but this slide has no debug_captures")
    if available and inspected != available:
        fail(
            parser,
            "--inspected-debug must exactly match this slide's boundary overlay captures: "
            f"{','.join(available)}",
        )
    return inspected


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

    observation = require_observation(parser, args.observation)
    observation = require_warning_verdict(
        parser, slide_warnings(manifest, args.slide), observation, checks, args.status
    )
    inspected_debug = require_debug_inspection(parser, record, args.inspected_debug)

    record["reviewer"] = args.reviewer.strip()
    record["reviewer_ref"] = args.reviewer_ref.strip()
    record["inspected_profiles"] = inspected
    record["inspected_debug_captures"] = inspected_debug
    record["observation"] = observation
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
        command.add_argument("--inspected-debug", action="append", default=[])
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
    template = subparsers.add_parser(
        "template",
        help="print copy-pasteable record_review.py invocations for every pending record",
    )
    template.add_argument("--slide", type=int, default=None)
    return parser


def quote(value: str) -> str:
    return shlex.quote(value)


def slide_template(manifest_path: Path, record: dict, manifest: dict, *, cross: bool) -> str:
    """Build one runnable invocation with this slide's real tuple and profiles."""
    number = record.get("slide")
    profiles = ",".join(record.get("required_ai_profiles") or record.get("inspected_profiles") or [])
    checks = list(record.get("checks", {}))
    warnings = slide_warnings(manifest, number if isinstance(number, int) else -1)
    debug = sorted(record.get("debug_captures") or {}) if isinstance(record.get("debug_captures"), dict) else []
    parts = [
        f"python3 {quote(str(Path(__file__).resolve()))} {quote(str(manifest_path))}",
        "cross-slide" if cross else "slide",
        f"--slide {number}",
        "--reviewer build-html-slides-visual-reviewer --reviewer-ref REVIEWER_REF",
        "--status pass",
        f"--inspected {quote(profiles)}" if profiles else "--inspected PROFILES",
    ]
    parts.extend(f"--inspected-debug {quote(name)}" for name in debug)
    parts.extend(f"--check {quote(name)}=pass" for name in checks)
    if warnings:
        parts.append("--observation 'CONFIRM: NAME THE ELEMENT AND ITS COORDINATE'")
    else:
        parts.append("--observation 'REPLACE WITH ONE CONCRETE VISUAL FINDING'")
    return " \\\n  ".join(parts)


def print_templates(manifest_path: Path, manifest: dict, only: int | None) -> int:
    """Emit runnable commands for every record --status reports as pending."""
    emitted = 0
    for records_key, batch_key, cross in (
        ("slides", "review_batches", False),
        ("cross_reviews", "cross_review_batches", True),
    ):
        pending_batches = {
            batch.get("id")
            for batch in manifest.get(batch_key, []) or []
            if isinstance(batch, dict) and batch.get("status") != "complete"
        }
        for record in manifest.get(records_key, []) or []:
            if not isinstance(record, dict) or record.get("status") in {"pass", "fail"}:
                continue
            if record.get("review_batch_id") not in pending_batches:
                continue
            if only is not None and record.get("slide") != only:
                continue
            for warning in slide_warnings(manifest, record.get("slide")):
                print(f"# WARNING slide {record.get('slide')}: {warning}")
            print(slide_template(manifest_path, record, manifest, cross=cross))
            print()
            emitted += 1
    if only is None:
        score = manifest.get("quality_score")
        if isinstance(score, dict) and score.get("status") != "pass":
            dimensions = " ".join(f"--dimension {name}=3" for name in QUALITY_DIMENSIONS)
            slide_count = len(manifest.get("slides") or [])
            weakest = ",".join(str(number) for number in range(1, min(3, slide_count) + 1)) or "1"
            print(
                f"python3 {quote(str(Path(__file__).resolve()))} {quote(str(manifest_path))} quality \\\n"
                "  --reviewer build-html-slides-quality-editor --reviewer-ref REVIEWER_REF \\\n"
                f"  --status pass {dimensions} --weakest {weakest} \\\n"
                "  --observation 'REPLACE WITH ONE CONCRETE DECK-LEVEL FINDING'\n"
            )
            emitted += 1
        squint = manifest.get("squint_review")
        if isinstance(squint, dict) and squint.get("status") != "pass":
            checks = " ".join(f"--check {name}=pass" for name in SQUINT_REVIEW_CHECKS)
            print(
                f"python3 {quote(str(Path(__file__).resolve()))} {quote(str(manifest_path))} squint \\\n"
                "  --reviewer build-html-slides-quality-editor --reviewer-ref REVIEWER_REF \\\n"
                f"  --status pass {checks} \\\n"
                "  --observation 'REPLACE WITH ONE CONCRETE DECK-WIDE HIERARCHY FINDING'\n"
            )
            emitted += 1
    if not emitted:
        print("OK: no pending review records")
    return 0


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
    if args.kind == "template":
        return print_templates(path, manifest, args.slide)
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
