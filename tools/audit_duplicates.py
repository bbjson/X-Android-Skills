#!/usr/bin/env python3
"""Report rule-level overlap between skills, for human review.

This is an *aid*, not a judge. Two skills legitimately share an identifier
(`collectAsStateWithLifecycle` appears in both the Compose state skill and the footgun
scan). What matters is whether they state *conflicting* rules — which no script can decide.
So this prints the closest pairs with the identifiers they share, and you read them.

Usage: python3 tools/audit_duplicates.py [--top N] [--min-score 0.20] [--pairs]
Exit: always 0 (informational).
"""
from __future__ import annotations

import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "be", "it", "its",
    "that", "this", "as", "at", "by", "for", "with", "not", "no", "you", "your", "if",
    "when", "then", "than", "so", "but", "from", "one", "two", "every", "each", "into",
    "must", "never", "always", "only", "any", "all", "same", "use", "used", "using",
    "rule", "rules", "skill", "skills", "code", "see", "per",
}
# Identifiers worth comparing: CamelCase, snake_case, call-like, or dotted API names.
IDENT = re.compile(r"\b(?:[a-z]+[A-Z]\w*|[A-Z][a-z]+[A-Z]\w*|\w+\.\w+|\w+\(\)|\w+_\w+)\b")
WORD = re.compile(r"[a-z]{4,}")


def rules_text(path: Path) -> str:
    text = path.read_text()
    m = re.search(r"^## Rules\s*$(.*?)^## ", text, re.S | re.M)
    return m.group(1) if m else text


def tokens(text: str) -> set[str]:
    ids = {t for t in IDENT.findall(text) if len(t) > 4}
    words = {w for w in WORD.findall(text.lower()) if w not in STOP}
    return ids | words


def main(argv: list[str]) -> int:
    top = 8
    min_score = 0.20
    for i, a in enumerate(argv):
        if a == "--top" and i + 1 < len(argv):
            top = int(argv[i + 1])
        if a == "--min-score" and i + 1 < len(argv):
            min_score = float(argv[i + 1])

    skills = {}
    for p in sorted(ROOT.glob("skills/**/SKILL.md")):
        skills[p.parent.name] = tokens(rules_text(p))

    scored = []
    for (na, ta), (nb, tb) in combinations(skills.items(), 2):
        inter = ta & tb
        if not inter:
            continue
        jac = len(inter) / len(ta | tb)
        scored.append((jac, na, nb, inter))
    scored.sort(reverse=True)
    scored = [s for s in scored if s[0] >= min_score]

    print(f"{len(skills)} skills; {len(scored)} pairs with Jaccard >= {min_score}\n")
    for jac, na, nb, inter in scored[:top]:
        shared = sorted(inter, key=len, reverse=True)[:8]
        print(f"{jac:.2f}  {na}  ~  {nb}")
        print(f"       shared: {', '.join(shared)}")

    if len(scored) > top:
        print(f"\n... {len(scored) - top} more pairs (use --top N)")
    print("\nShared identifiers are expected where skills cross-reference each other.")
    print("Review a pair only if it states the same rule twice or contradicts itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
