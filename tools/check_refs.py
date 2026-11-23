#!/usr/bin/env python3
"""Check that every skill name referenced in a SKILL.md exists or is a known roadmap entry."""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
installed = {p.parent.name for p in ROOT.glob("skills/**/SKILL.md")}
roadmap = {
    l.strip() for l in (ROOT / "docs/roadmap.txt").read_text().splitlines()
    if l.strip() and not l.startswith("#")
}
known = installed | roadmap
REF = re.compile(r"(?:→|\|)\s*`([a-z0-9]+(?:-[a-z0-9]+)+)`")

bad = 0
for f in sorted(ROOT.glob("skills/**/SKILL.md")):
    for i, line in enumerate(f.read_text().splitlines(), 1):
        for name in REF.findall(line):
            if name not in known:
                print(f"{f.relative_to(ROOT)}:{i} unknown skill reference `{name}`")
                bad += 1
print(f"\n{len(installed)} installed, {len(roadmap)} roadmap — {bad} unknown references")
sys.exit(1 if bad else 0)
