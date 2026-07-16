#!/usr/bin/env python3
"""Run the complete deterministic, render, and evidence-validation workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    from source_cache import local_assets
except ModuleNotFoundError:  # Allows unittest imports from the skill root.
    from scripts.source_cache import local_assets


SCRIPTS = Path(__file__).resolve().parent
CONTRACT = json.loads((SCRIPTS / "validation_contract.json").read_text(encoding="utf-8"))
IMPACT_SCOPES = set(CONTRACT["impact_scopes"])
CONTENT_CHANGE_CATEGORIES = set(CONTRACT["content_change_categories"])
COMMAND_TIMEOUT_SECONDS = int(os.environ.get("BUILD_HTML_SLIDES_COMMAND_TIMEOUT", "900"))


def default_notes(deck: Path) -> Path:
    candidates = (
        deck.with_name(f"{deck.stem}-notes.md"),
        deck.with_name(f"{deck.stem}_notes.md"),
        deck.with_name("speaker-notes.md"),
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def run(label: str, command: list[str]) -> None:
    started = time.monotonic()
    print(f"RUN: {label}")
    try:
        result = subprocess.run(
            command,
            text=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{label} exceeded the {COMMAND_TIMEOUT_SECONDS}s per-command safety timeout"
        ) from exc
    elapsed = time.monotonic() - started
    if result.returncode:
        raise RuntimeError(f"{label} failed after {elapsed:.1f}s")
    print(f"PASS: {label} ({elapsed:.1f}s)")


def deterministic_commands(
    deck: Path,
    notes: Path,
    sources: Path,
    change_type: str,
    *,
    browser_e2e: bool = False,
    content_changes: list[str] | None = None,
) -> list[tuple[str, list[str]]]:
    python = sys.executable
    if content_changes is None:
        content_changes = {
            "all": ["text", "image", "structure", "style", "runtime"],
            "text": ["text"],
            "image": ["image"],
            "navigation": ["runtime"],
        }[change_type]
    changed = set(content_changes)
    commands = [
        ("deck structure", [python, str(SCRIPTS / "validate_deck.py"), str(deck)]),
        (
            "placeholder and incomplete-asset gate",
            [python, str(SCRIPTS / "validate_placeholders.py"), str(deck)],
        ),
    ]
    if changed & {"text", "structure"}:
        commands.append(
            ("presenter notes", [python, str(SCRIPTS / "validate_speaker_notes.py"), str(deck), str(notes)])
        )
    if "image" in changed:
        commands.append(("source locality", [python, str(SCRIPTS / "validate_source_locality.py"), str(deck)]))
    assets = local_assets(deck)
    if "image" in changed:
        if assets or sources.exists():
            commands.append((
                "hash-bound source cache",
                [python, str(SCRIPTS / "source_cache.py"), str(deck), str(sources), "--check"],
            ))
        commands.append(("image reuse", [python, str(SCRIPTS / "validate_image_reuse.py"), str(deck)]))
    if "runtime" in changed or change_type == "navigation" or browser_e2e:
        commands.extend((
            ("interaction semantics", [python, str(SCRIPTS / "validate_interactions.py"), str(deck)]),
            ("browser interaction and print E2E", ["node", str(SCRIPTS / "validate_browser_e2e.js"), str(deck)]),
        ))
    return commands


def review_directory(deck: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    result = subprocess.run(
        ["node", str(SCRIPTS / "render_slides.js"), "--review-dir", str(deck)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or "could not resolve review directory")
    return Path(result.stdout.strip()).resolve()


def classify_change_scope(
    deck: Path,
    review: Path,
    requested: str,
    mode: str,
    review_risk: str,
    responsive: bool,
    cache: Path,
) -> dict[str, object]:
    result = subprocess.run(
        [
            "node",
            str(SCRIPTS / "render_slides.js"),
            "--classify-change",
            str(deck),
            str(review),
            requested,
            mode,
            review_risk,
            str(responsive).lower(),
            str(cache),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or "could not classify the source change")
    try:
        classification = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("change classifier returned invalid JSON") from exc
    effective = classification.get("effective")
    if effective not in {"all", "text", "image", "navigation"}:
        raise RuntimeError("change classifier returned an invalid effective scope")
    if classification.get("impact") not in IMPACT_SCOPES:
        raise RuntimeError("change classifier returned an invalid impact scope")
    if not isinstance(classification.get("navigation_changed"), bool):
        raise RuntimeError("change classifier returned an invalid navigation flag")
    content_changes = classification.get("content_changes")
    if (
        not isinstance(content_changes, list)
        or len(content_changes) != len(set(content_changes))
        or any(value not in CONTENT_CHANGE_CATEGORIES for value in content_changes)
    ):
        raise RuntimeError("change classifier returned invalid content change categories")
    if effective != requested:
        print(
            f"NOTICE: requested change type {requested} resolved to {effective} "
            f"after detecting {classification.get('detected', 'unknown')} changes"
        )
    return classification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", type=Path)
    parser.add_argument(
        "--phase",
        choices=("prepare", "verify", "finalize-prepare", "finalize-verify", "finalize"),
        default="prepare",
    )
    parser.add_argument("--mode", choices=("quick", "full"))
    parser.add_argument("--review-risk", choices=("standard", "high"), default="standard")
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--review-dir", type=Path)
    parser.add_argument("--slides")
    parser.add_argument("--change-type", choices=("all", "text", "image", "navigation"), default="all")
    parser.add_argument("--responsive", action="store_true")
    args = parser.parse_args()
    if args.phase == "finalize":
        print("NOTICE: --phase finalize is deprecated; using finalize-prepare")
        args.phase = "finalize-prepare"

    deck = args.deck.resolve()
    if not deck.is_file():
        parser.error(f"deck not found: {deck}")
    if args.phase == "prepare" and args.mode is None:
        parser.error("--mode quick|full is required for prepare")
    if args.phase != "prepare" and args.slides:
        parser.error("--slides is only valid during prepare")

    notes = (args.notes or default_notes(deck)).resolve()
    sources = (args.sources or deck.with_name("sources.json")).resolve()
    started = time.monotonic()
    fingerprint_cache: Path | None = None

    try:
        review = review_directory(deck, args.review_dir)
        manifest = review / "review.json"
        if args.phase == "prepare":
            if not args.slides:
                run("tool preflight", [sys.executable, str(SCRIPTS / "check_environment.py")])
            classification: dict[str, object] = {
                "effective": "all" if not args.slides else args.change_type,
                "impact": "full" if not args.slides else "direct",
                "navigation_changed": True if not args.slides else args.change_type == "navigation",
                "content_changes": (
                    ["text", "image", "structure", "style", "runtime"]
                    if not args.slides
                    else {
                        "all": ["text", "image", "structure", "style", "runtime"],
                        "text": ["text"],
                        "image": ["image"],
                        "navigation": ["runtime"],
                    }[args.change_type]
                ),
            }
            if args.slides:
                fingerprint_cache = review / ".fingerprint-cache.json"
                classification = classify_change_scope(
                    deck,
                    review,
                    args.change_type,
                    args.mode,
                    args.review_risk,
                    args.responsive,
                    fingerprint_cache,
                )
            validation_scope = str(classification["effective"])
            for label, command in deterministic_commands(
                deck,
                notes,
                sources,
                validation_scope,
                browser_e2e=bool(classification["navigation_changed"])
                or args.change_type == "navigation",
                content_changes=list(classification["content_changes"]),
            ):
                run(label, command)

            command = [
                "node", str(SCRIPTS / "render_slides.js"), str(deck), str(review),
                "--mode", args.mode, "--review-risk", args.review_risk,
                "--change-type", args.change_type,
            ]
            if args.slides:
                command.extend(("--slides", args.slides))
            if args.responsive:
                command.append("--responsive")
            if fingerprint_cache and fingerprint_cache.is_file():
                command.extend(("--fingerprint-cache", str(fingerprint_cache)))
            run("Chromium render and geometry gate", command)
            print(f"NEXT: complete only the AI batches listed in {manifest}, then run --phase verify")
        elif args.phase == "verify":
            run(
                "visual evidence contract",
                [
                    sys.executable,
                    str(SCRIPTS / "validate_visual_review.py"),
                    str(deck),
                    str(manifest),
                    "--capture-scope",
                    "refreshed",
                    "--source-fingerprint-scope",
                    "metadata",
                ],
            )
        elif args.phase == "finalize-prepare":
            run(
                "iteration evidence before finalization",
                [
                    sys.executable,
                    str(SCRIPTS / "validate_visual_review.py"),
                    str(deck),
                    str(manifest),
                    "--capture-scope",
                    "metadata",
                    "--source-fingerprint-scope",
                    "metadata",
                ],
            )
            run(
                "prepare final review without rerender",
                ["node", str(SCRIPTS / "render_slides.js"), str(deck), str(review), "--finalize-prepare"],
            )
            print(
                f"NEXT: fill the final quality score and generated cross-review batches in {manifest}, "
                "then run --phase finalize-verify"
            )
        else:
            run(
                "final quality score and cross-review evidence",
                [
                    sys.executable,
                    str(SCRIPTS / "validate_visual_review.py"),
                    str(deck),
                    str(manifest),
                    "--capture-scope",
                    "full",
                    "--source-fingerprint-scope",
                    "metadata",
                ],
            )
    except (OSError, RuntimeError, ValueError) as exc:
        if fingerprint_cache:
            fingerprint_cache.unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"OK: complete validation entrypoint phase '{args.phase}' finished in {time.monotonic() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
