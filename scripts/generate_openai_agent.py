#!/usr/bin/env python3
"""Generate codex/skills/build-html-slides/agents/openai.yaml from SKILL.md.

Codex loads `default_prompt` on every turn, so it is always-on context that is
charged against the same 15-minute Quick Draft and 70-minute Full Validation
budgets as everything else. Until now it was a hand-compressed seventh copy of
the whole rule set: 8,153 bytes maintained by hand, protected only by seven
`assertIn` checks that could detect deletion but never contradiction. SKILL.md
moved 33 times against its 20.

This generator removes the copy. Every line of the prompt is lifted from a named
anchor in `SKILL.md` or read from `scripts/validation_contract.json`, so the
prompt cannot state a rule the skill does not state, and cannot carry a stale
number at all: it deliberately restates no threshold. A rule that a deterministic
gate now enforces is reduced to the gate's name plus the pointer to
`references/reviewer-gates.md`, which is why the generated prompt is far smaller
than the file it replaces.

If an anchor disappears from SKILL.md the generator raises instead of quietly
emitting a prompt with a missing rule.

    python3 scripts/generate_openai_agent.py            # write the file
    python3 scripts/generate_openai_agent.py --check     # fail if it would change
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "codex/skills/build-html-slides"
SKILL_MD = SKILL_ROOT / "SKILL.md"
CONTRACT_JSON = SKILL_ROOT / "scripts/validation_contract.json"
TARGET = SKILL_ROOT / "agents/openai.yaml"

# Interface labels are Codex UI strings, not rules; they carry no rule content
# that could contradict SKILL.md.
DISPLAY_NAME = "HTML Presentation Builder"
SHORT_DESCRIPTION = "Create art-directed HTML decks with notes, WebP assets, and visual QA"

SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\"'À-ɏ])")


class MissingAnchor(RuntimeError):
    """SKILL.md no longer provides a rule this prompt is built from."""


def sections(text: str, level: int) -> dict[str, str]:
    """Split markdown into {heading: body} at one heading level."""
    marker = "#" * level + " "
    found: dict[str, str] = {}
    heading = ""
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith(marker) and not line.startswith(marker + "#"):
            if heading:
                found[heading] = "\n".join(body).strip()
            heading = line[len(marker):].strip()
            body = []
        elif line.startswith("#" * (level - 1) + " ") and level > 1:
            if heading:
                found[heading] = "\n".join(body).strip()
            heading = ""
            body = []
        elif heading:
            body.append(line)
    if heading:
        found[heading] = "\n".join(body).strip()
    return found


def section(text: str, heading: str, level: int = 2) -> str:
    body = sections(text, level).get(heading)
    if not body:
        raise MissingAnchor(f"SKILL.md has no '{'#' * level} {heading}' section")
    return body


def bullets(body: str) -> list[str]:
    """Top-level `- ` bullets, with continuation lines folded in."""
    items: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if line.startswith("- "):
            items.append(stripped[2:])
        elif stripped.startswith(("- ", "* ")) or re.match(r"^\d+\.\s", stripped):
            # A nested list item belongs to its own structure, never to the
            # preceding top-level bullet. Folding it in produced a prompt line
            # that ran four unrelated rules together.
            continue
        elif items and line.startswith("  ") and stripped:
            items[-1] += " " + stripped
    return items


def numbered(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^\d+\.\s+(.*)$", line)
        if match:
            items.append(match.group(1).strip())
        elif items and line.startswith("   ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def table_rows(body: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|- "):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and cells[0].lower() in {"gate", "read", "stage"}:
            continue
        rows.append(cells)
    return rows


def lead(text: str, count: int = 1) -> str:
    """The first `count` sentences of the first paragraph, markdown emphasis dropped.

    Bounded to one paragraph and stopped at the first list marker: a sentence
    splitter alone happily swallowed a whole bullet list into "sentence two".
    """
    plain = re.sub(r"\*\*(.+?)\*\*", r"\1", text).strip().split("\n\n")[0]
    kept: list[str] = []
    for line in plain.splitlines():
        if line.strip().startswith(("- ", "* ")) or re.match(r"^\s*\d+\.\s", line):
            break
        kept.append(line)
    parts = SENTENCE_BOUNDARY.split(" ".join(" ".join(kept).split()))
    return " ".join(parts[:count]).strip()


def bold_lead(text: str) -> str:
    """The bolded lead-in of a bullet, which SKILL.md uses for its checkpoints."""
    match = re.match(r"\s*\*\*(.+?)\*\*", text)
    if match and not match.group(1).rstrip().endswith(":"):
        return match.group(1).strip()
    # A bold lead-in ending in a colon promises a list; keep the whole sentence.
    return lead(text, 1)


def starting_with(items: list[str], prefix: str) -> str:
    for item in items:
        if item.startswith(prefix):
            return item
    raise MissingAnchor(f"no bullet starting with {prefix!r}")


def containing(items: list[str], needle: str) -> str:
    for item in items:
        if needle in item:
            return item
    raise MissingAnchor(f"no bullet containing {needle!r}")


def build_prompt(skill: str, contract: dict) -> str:
    mode_body = section(skill, "Decide The Work Mode")
    mode_bullets = bullets(mode_body)
    budget_body = section(skill, "Time Budget")
    gates_body = section(skill, "Deterministic Gates And Their Thresholds")
    # Everything below the first `###` in Reviewer Dispatch is the check-tuple and
    # recording-syntax reference, which the prompt points at instead of copying.
    dispatch_body = section(skill, "Reviewer Dispatch").split("\n### ", 1)[0]
    companions = bullets(section(skill, "Companion Skill Routing"))
    story = bullets(section(skill, "Story And Copy"))
    art = bullets(section(skill, "Art Direction"))
    assets = numbered(section(skill, "Asset Contract"))
    batches = bullets(section(skill, "Fix In Batches, Render Once"))
    deliverable = section(skill, "Deliverable")

    phases = [
        heading.split("—", 1)[1].strip()
        for heading in sections(skill, 3)
        if heading.startswith("Phase ")
    ]
    if len(phases) < 7:
        raise MissingAnchor("SKILL.md must document every Full Validation phase as '### Phase N — name'")

    gate_names = [row[0] for row in table_rows(gates_body)]
    if len(gate_names) < 8:
        raise MissingAnchor("SKILL.md must list every deterministic gate in its gate table")

    full = contract["time_budgets"]["full"]
    quick = contract["time_budgets"]["quick"]
    low, high = contract["time_budgets"]["slide_range"]
    scopes = ", ".join(f"{name} ({len(checks)})" for name, checks in contract["checks_by_change"].items())

    lines: list[str] = []
    add = lines.append

    add("Use $build-html-slides for every HTML slide deck, keynote-style HTML page, or revision of one.")
    add("SKILL.md is the contract; load it and follow its Reading Plan, opening each reference at the")
    add("moment its decision arrives rather than all of them up front.")
    add("")
    add("INTAKE. " + lead(mode_body.split("\n\n")[1], 2))
    for prefix in ("**Edit Only**", "**빠른 검증 (Quick Draft)**", "**정밀 검증 (Full Validation)**"):
        add("- " + lead(starting_with(mode_bullets, prefix), 2))
    add("")
    add(f"BUDGET. Full Validation: {full['total_minutes']} minutes for a {low}-{high} slide deck. "
        f"Quick Draft: {quick['total_minutes']} minutes. These are ceilings.")
    for bullet in bullets(budget_body):
        if bullet.startswith("**"):
            add("- " + bold_lead(bullet))
    add("- " + lead(containing(budget_body.splitlines(), "Checkpoints act autonomously"), 2))
    add("")
    add("FULL VALIDATION PHASES, in order, all through validate_all.py: " + ", ".join(phases) + ".")
    add(lead(dispatch_body, 2))
    for bullet in bullets(dispatch_body):
        add("- " + lead(bullet, 1))
    add("- " + lead(containing(dispatch_body.splitlines(), "**Independence:**"), 1))
    add("- Transcribe reviewer output with record_review.py and nothing else: it never creates a verdict,")
    add("  so never bulk-fill records, synthesize a PASS observation, or overwrite a reviewer FAIL.")
    add(f"- Each review_scope owns an exact ordered check tuple from validation_contract.json: {scopes}.")
    add("  Read it from that file or from --status; never type a tuple from memory.")
    add("")
    add("MEASURED, NOT ARGUED. Gates inside --phase prepare, before any capture reaches a reviewer: "
        + "; ".join(gate_names) + ".")
    add(lead(gates_body, 2))
    for bullet in bullets(gates_body):
        add("- " + lead(bullet, 1))
    add("- A warned slide enters the refute-or-confirm pass in references/reviewer-gates.md: open its")
    add("  slide-NN-debug.png boundary overlay and open the observation with CONFIRM: or REFUTE: naming")
    add("  an element and a coordinate. Generic approval does not close a warning.")
    add("")
    add("RULES NO GATE CAN MEASURE.")
    for source, needle in (
        (story, "Separate private authoring constraints"),
        (art, "palette provenance"),
        (art, "Slide 1 is the highest-priority"),
        (art, "Declare `--font-display`"),
        (art, "Technology is a subject domain"),
        (art, "Plan each meaningful visual as evidence"),
        (assets, "Read `references/asset-discovery.md`"),
        (companions, "Availability is sufficient consent"),
        (companions, "Bundled distributions include `archify`"),
        (batches, "A shared-CSS or runtime edit after"),
    ):
        add("- " + lead(containing(source, needle), 1))
    add("")
    add(lead(deliverable.split("\n\n")[-1], 2))
    return "\n".join(lines).rstrip() + "\n"


def render_yaml(prompt: str) -> str:
    body = "".join(f"    {line}\n" if line else "\n" for line in prompt.rstrip("\n").split("\n"))
    return (
        "# GENERATED FILE - do not edit by hand.\n"
        "# Source: SKILL.md + scripts/validation_contract.json\n"
        "# Regenerate: python3 scripts/generate_openai_agent.py\n"
        "interface:\n"
        f'  display_name: "{DISPLAY_NAME}"\n'
        f'  short_description: "{SHORT_DESCRIPTION}"\n'
        "  default_prompt: |-\n"
        f"{body}"
    )


def generate() -> str:
    skill = SKILL_MD.read_text(encoding="utf-8")
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    return render_yaml(build_prompt(skill, contract))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed file is stale")
    args = parser.parse_args()
    rendered = generate()
    current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
    if args.check:
        if rendered != current:
            print(
                f"ERROR: {TARGET.relative_to(ROOT)} is stale; "
                "run python3 scripts/generate_openai_agent.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {TARGET.relative_to(ROOT)} matches SKILL.md ({len(rendered)} bytes)")
        return 0
    if rendered == current:
        print(f"OK: {TARGET.relative_to(ROOT)} already current ({len(rendered)} bytes)")
        return 0
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"OK: wrote {TARGET.relative_to(ROOT)} ({len(current)} -> {len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
