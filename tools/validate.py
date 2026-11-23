#!/usr/bin/env python3
"""Validate X-Android-Skills against docs/skill-style.md.

Checks: frontmatter fields, name/directory match, required sections, length budget,
and the hardcoded-version rule (with the documented migration exceptions).

Usage: python3 tools/validate.py [--quiet] [path ...]
Exit: 0 clean, 1 errors, 2 errors+warnings only.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_SECTIONS = [
    "## Use when",
    "## Do not use when",
    "## Rules",
    "## Checklist",
    "## Anti-patterns",
    "## Verify",
]

# Skills whose subject *is* a version transition may name the source version.
VERSION_EXEMPT = {
    "agp9-migration",
    "kotlin-toolchain",
    "nav2-to-nav3",
    "xml-to-compose",
    "rxjava-to-coroutines",
    "java-to-kotlin",
    "hilt-to-koin",
    "cocoapods-to-spm",
}

VERSION_RE = re.compile(
    r"""(?xi)
    (?:agp|kotlin|compose|hilt|room|retrofit|espresso|junit|coil|navigation3?)
    \s*(?:=|:|version|["'])\s*
    ["']?\d+\.\d+
    """
)
LEN_BUDGET = {"core": 200, "advanced": 260, "specialized": 400, "migration": 300}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    fm: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if re.match(r"^\s+\S", line) and key:  # continuation
            fm[key] += " " + line.strip()
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip().strip("'\"")
    return fm, body


def check(path: Path) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    slug = path.parent.name
    rel = path.relative_to(ROOT)

    if not fm:
        errs.append("no YAML frontmatter")
        return errs, warns

    for field in ("name", "description", "license"):
        if not fm.get(field):
            errs.append(f"missing frontmatter field: {field}")

    if fm.get("name") != slug:
        errs.append(f"name '{fm.get('name')}' != directory '{slug}'")

    desc = fm.get("description", "")
    if len(desc) < 60:
        errs.append(f"description too short ({len(desc)} chars) — cannot route")
    if "use when" not in desc.lower():
        warns.append("description lacks 'Use when' trigger clause")

    level = ""
    meta = re.search(r"metadata:\n((?:\s+.*\n)+)", text)
    if meta:
        m = re.search(r"level:\s*(\w+)", meta.group(1))
        level = m.group(1) if m else ""
    if level not in LEN_BUDGET:
        warns.append(f"metadata.level missing or unknown: {level!r}")

    lines = text.count("\n") + 1
    budget = LEN_BUDGET.get(level, 260)
    if lines > budget:
        warns.append(f"{lines} lines exceeds {level or 'default'} budget {budget}")

    for section in REQUIRED_SECTIONS:
        if section not in body:
            errs.append(f"missing section: {section}")

    if "## Rules" in body and not re.search(r"^1\. ", body, re.M):
        errs.append("Rules section has no numbered rules")

    if slug not in VERSION_EXEMPT:
        for i, line in enumerate(text.splitlines(), 1):
            hit = VERSION_RE.search(line)
            if hit and "libs." not in line and "maven-metadata" not in line:
                warns.append(f"possible hardcoded version at line {i}: {line.strip()[:70]}")

    if not body.lstrip().startswith("# "):
        errs.append("body must start with an H1 title")

    return errs, warns


def main(argv: list[str]) -> int:
    quiet = "--quiet" in argv
    targets = [a for a in argv[1:] if not a.startswith("-")]
    paths = (
        [Path(t) for t in targets]
        if targets
        else sorted(ROOT.glob("skills/**/SKILL.md"))
    )
    if not paths:
        print("no SKILL.md found")
        return 1

    total_err = total_warn = 0
    for p in paths:
        errs, warns = check(p)
        total_err += len(errs)
        total_warn += len(warns)
        if not errs and not warns and quiet:
            continue
        status = "FAIL" if errs else ("WARN" if warns else "ok")
        print(f"{status}  {p.relative_to(ROOT)}")
        for e in errs:
            print(f"      error: {e}")
        for w in warns:
            print(f"      warn:  {w}")

    print(f"\n{len(paths)} skills — {total_err} errors, {total_warn} warnings")
    return 1 if total_err else (2 if total_warn else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
