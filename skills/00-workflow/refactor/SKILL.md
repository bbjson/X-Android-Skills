---
name: refactor
description: >-
  Restructure existing code with provable behaviour preservation: tests green before and after, one
  mechanical transformation per commit, no feature change mixed in. Use when extracting a class,
  renaming across modules, moving code between layers, breaking up a god object, or when a change is
  described as "cleanup" without a behavioural justification.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering (workflows/refactor)
    - mobile-agent-skillpack (safe-refactor-guard)
    - chrisbanes/skills (to-plan)
    - agent-skills-standard (android-architecture)
---

# Refactor

A refactor has an **observable contract**: no behaviour changes. If you cannot state how that is
verified, you are rewriting, not refactoring — and rewriting needs a spec.

## Use when

- Extracting a class/function/interface, renaming, moving files between layers or modules.
- Breaking up a file that is too large to reason about.
- Preparing for a feature by making room (a preparatory refactor, merged separately).
- Removing dead code or an unused dependency.

## Do not use when

- Any behaviour changes (even a bug fix) → `bug-fix` or the feature workflow.
- The goal is a new architecture with new tests → `feature-to-spec` + `implementation-plan`.
- You are reviewing someone else's refactor → `code-review`.

## Rules

1. **Green before, green after.** Run the relevant tests *before* touching anything and record the
   result. Refactoring on top of a red suite means you cannot distinguish your breakage from the
   pre-existing one.
2. **One transformation per commit.** Extract → commit. Rename → commit. Move → commit. A commit with
   three transformations cannot be reviewed, and cannot be bisected when something does break.
3. **No behaviour change, including "improvements".** Renaming a parameter is fine; changing its
   default is not. Fixing an adjacent bug is a separate commit that says so.
4. **Use the IDE's mechanical refactors where available.** Rename/move/extract by hand across modules
   misses references that the tool would have found (string resources, reflection, manifests,
   serialization names).
5. **State the verification for behavioural equivalence.** Options: existing tests, a golden
   screenshot set, a characterisation test written *first* against the old code, or "pure move, same
   diff". "It looks equivalent" is not a verification.
6. **Characterisation tests come first** when the code has no tests: write tests asserting current
   (possibly wrong) behaviour, so a refactor that accidentally fixes a bug is caught.
7. **Keep the diff dominated by moves and renames.** If a refactor commit adds substantial new lines,
   something else is happening — split it.
8. **Public/API surfaces change last, or not at all.** Refactor internals first; if a public signature
   must change, do it in a separate commit with the call sites updated mechanically.
9. **Preparatory refactors merge before the feature.** A PR that refactors *and* adds a feature cannot
   be reviewed for either; the refactor also cannot be reverted independently.
10. **Delete dead code in its own commit, after a search, not "while here".** `grep` for reflection,
    manifests, resources, and build files before deleting anything.

## Procedure

1. Write the goal in one sentence: "extract `FeedMapper` out of `FeedRepository` with no signature
   change".
2. Run tests, record green.
3. If untested, write characterisation tests; record green.
4. Apply one mechanical transformation (IDE where possible).
5. Run the same tests. Compare: same set, same results.
6. Commit with the transformation named. Repeat from 4.
7. Final: run the full suite + `assembleRelease`, and diff the public API surface if it changed.

## Checklist

- [ ] Tests green before the first edit (or characterisation tests added).
- [ ] One transformation per commit.
- [ ] Nothing else changed: no bug fix, no formatting, no new feature.
- [ ] IDE mechanical refactor used where available.
- [ ] Behavioural-equivalence verification named (tests / screenshots / pure move).
- [ ] Public API diff reviewed or empty.
- [ ] Commit message states the transformation, not the goal.
- [ ] Feature work split into a separate PR.
- [ ] Dead code removal justified by a search, in its own commit.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Unreviewable PR | refactor + feature | two PRs | neither is reviewable |
| Unbisectable history | extract+rename+move in one commit | one each | cannot find the break |
| Silent behaviour change | "also fixed a small bug" | separate commit | contract broken |
| Refactor with no tests | trust the compiler | characterisation tests first | no proof |
| Hand rename | grep and replace | IDE rename | missed references |
| Broken serialization | rename the field | `@SerialName` then rename | wire format changes |
| Deleted a used class | "nothing imports it" | check manifest/resources/reflection | runtime crash |

## Verify

```bash
./gradlew test                  # same failures/tests as before
git diff --stat                 # dominated by renames/moves
git show --stat HEAD            # one transformation
```

Expected: identical test results before and after, and a diff whose added code is limited to the
extraction's plumbing.

## References

- `code-review` — how each refactor commit will be judged
- `feature-to-spec` — when "refactor" actually means redesign
