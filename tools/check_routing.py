#!/usr/bin/env python3
"""Check the routing evals against the router table.

Each eval asserts: the expected skill exists, and the router names it in a `Load` column.
A route that is missing from the router is the failure this catches — the eval file is the
specification, the router table is the implementation.

Usage: python3 tools/check_routing.py [--verbose]
Exit: 0 all cases routed, 1 otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals/routing.tsv"


def parse_router() -> tuple[set[str], dict[str, str]]:
    """Return (skills named in a Load column, skill -> neighbouring 'Not' skill)."""
    loaded: set[str] = set()
    nots: dict[str, str] = {}
    for line in (ROOT / "skills/router/SKILL.md").read_text().splitlines():
        line = line.strip()
        if line.startswith("## Rules"):
            break          # only the routing tables are routing data; anti-patterns are not
        if not line.startswith("|") or line.startswith("|---") or "Request shape" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        load = cells[1].strip("`").split()[0] if cells[1] else ""
        if load and load not in {"Load", ""} and "(" not in load:
            loaded.add(load)
            if len(cells) > 2:
                not_ = cells[2].strip("`").split()[0]
                if not_ and not_ != "Not":
                    nots[load] = not_
    return loaded, nots


def main(argv: list[str]) -> int:
    verbose = "--verbose" in argv
    installed = {p.parent.name for p in ROOT.glob("skills/**/SKILL.md")}
    loaded, nots = parse_router()

    cases: list[tuple[str, str, str, int]] = []
    for lineno, raw in enumerate(EVALS.read_text().splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            print(f"{EVALS.name}:{lineno} malformed (need task<TAB>skill)")
            continue
        task, skill = parts[0].strip(), parts[1].strip()
        forbidden = parts[2].strip() if len(parts) > 2 else "-"
        cases.append((task, skill, forbidden, lineno))

    failures = 0
    for task, skill, forbidden, lineno in cases:
        problems = []
        if skill not in installed:
            problems.append(f"skill '{skill}' does not exist")
        elif skill not in loaded:
            problems.append(f"router never routes to '{skill}'")
        if forbidden != "-" and forbidden == skill:
            problems.append("expected and forbidden skill are the same")
        if forbidden != "-" and forbidden not in installed:
            problems.append(f"forbidden skill '{forbidden}' does not exist")
        if problems:
            failures += 1
            print(f"FAIL  {EVALS.name}:{lineno}  {task[:56]}")
            for p in problems:
                print(f"        {p}")
        elif verbose:
            print(f"ok    {task[:56]} -> {skill}")

    # A `Not` column that names a typo silently disables the routing contract.
    for load, not_ in sorted(nots.items()):
        if not_ not in installed and not_ not in {"Not", ""}:
            failures += 1
            print(f"FAIL  router 'Not' column for '{load}' names unknown skill '{not_}'")

    covered = {c[1] for c in cases}
    # `router` is meta and routes to itself by definition; no eval case can be meaningful.
    uncovered = sorted(installed - covered - {"router"})
    print(f"\n{len(cases)} cases, {len(covered)}/{len(installed)} skills covered, {failures} failures")
    if uncovered:
        print(f"no eval case yet ({len(uncovered)}): {', '.join(uncovered)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
