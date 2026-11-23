---
name: code-review
description: >-
  Review an Android/Kotlin change for correctness, boundaries, concurrency, architecture, tests
  and reversibility, producing only findings that are actionable at a specific line. Use when
  reviewing a pull request or a diff, when an agent is asked to "check my change", before
  requesting review, or when a review is turning into a style debate.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering (android-code-review, workflows/code-review)
    - mobile-agent-skillpack (receiving-code-review, requesting-code-review, security-best-practices)
    - chrisbanes/skills (implement-with-subagents)
---

# Code Review

A review is a **bug-finding instrument with a severity contract**, not an opinion channel. Every
comment either points at a defect with a concrete alternative, or is labelled as preference and
can be ignored.

## Use when

- Reviewing a diff or pull request.
- An agent is asked to check or self-review a change.
- Reviewing before asking a human.
- A review thread is stuck on style, naming, or "I would have done it differently".

## Do not use when

- The task is to fix a known defect → `bug-fix`.
- The task is to restructure code → `refactor`.
- The only question is formatting → run the formatter/linter (`static-analysis` in roadmap).

## Rules

1. **Read the diff first, then only the code needed to judge it.** Reading whole files produces
   comments about untouched code, which drowns the review.
2. **Every finding has three parts: location, defect, replacement.** "This can crash" is not a
   finding. "`feed/FeedViewModel.kt:88` — `items.first()` throws on empty; use
   `items.firstOrNull()` and emit `Empty`" is.
3. **Assign severity, and mean it:**
   - **Blocker** — wrong output, crash, data loss, security exposure, broken revert.
   - **Major** — architecture boundary violated, missing error state, untested behaviour, perf
     regression with evidence.
   - **Minor** — readability with a concrete cheaper alternative.
   - **Nit** — preference. Max 2 per review, and prefixed `nit:`.
4. **Anything a linter can catch is not a review comment.** Formatting, import order, naming
   convention, unused symbol — configure the tool once. A review that argues style is a review
   that missed the bug.
5. **Check the change against its domain skill's checklist.** Architecture → `layering`;
   state/effects → `compose-state-effects`; data → `data-layer`; tests → `unit-testing`;
   crypto → `keystore-and-crypto`. The skill's `## Checklist` is the review rubric.
6. **Verify the tests actually constrain the change.** Ask: if I revert one line of the fix, does a
   test go red? A new test that passes on the old code is decoration.
7. **Look for the five boundary bugs first** — empty list, null, first/last element, permission
   denied, process death. These are 80% of shipped defects and are invisible in the happy-path diff.
8. **Flag unrelated changes as a separate finding, not as an objection.** Opportunistic refactors,
   renames, formatting and version bumps in a feature diff are `Blocker` only if they break
   revertability; otherwise request a split.
9. **Cap the review at ~10 findings, highest severity first.** Fifty comments means nobody fixes
   any of them. Repeated instances of one defect get one finding with "also at lines …".
10. **When unsure whether something is wrong, ask a question instead of asserting.** "Is `id`
    guaranteed non-null here?" — a wrong assertion costs trust; a question costs one round trip.

## Procedure

1. Read the description and the spec; state the intended behaviour in one line.
2. Skim the diff for shape (files, layers, size). Large diff → request a split before reviewing.
3. Pass 1 — correctness: boundaries (rule 7), error paths, concurrency, lifecycle.
4. Pass 2 — the owning domain skill's checklist.
5. Pass 3 — tests: does each added test fail without the change?
6. Pass 4 — reversibility: migration, public API, config defaults.
7. Write findings sorted by severity, each with location/defect/replacement.
8. Summarise: approve / request changes / comment, with the one-line intent it is judged against.

## Checklist

- [ ] Intended behaviour stated in one line before commenting.
- [ ] Every finding has location + defect + concrete replacement.
- [ ] Severities assigned and distinguishable (no "all major").
- [ ] Zero lint-catchable comments.
- [ ] Owning domain skill's checklist applied.
- [ ] Each new test proven to fail without the change (or explicitly noted as unproven).
- [ ] Boundary cases checked: empty, null, first/last, permission, process death.
- [ ] Unrelated changes raised as a split request, not a style objection.
- [ ] ≤10 findings, sorted by severity.
- [ ] Uncertainties phrased as questions.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Review ignored | 40 comments incl. formatting | 8 findings, blockers first | attention is the bottleneck |
| Style war | "rename this to `mFoo`" | configure lint, drop it | tooling exists |
| Opinion as defect | "I'd use `map` here" | `nit:` or omit | not a defect |
| Rubber stamp | LGTM on a 900-line diff | ask for a split | unreviewable |
| Decorative test | new test passes on old code | prove red first | no constraint |
| Missed bug | praised structure, missed null | boundary pass first | correctness before taste |
| Unfair assertion | "this is a race" (maybe) | "is this called from >1 thread?" | guessing erodes trust |

## Verify

The review is done when:

1. The one-line intended behaviour is written down.
2. Every finding would still make sense to a reviewer who only sees that line + the code.
3. Reverting one line of the change makes at least one test fail (or that gap is a finding).

## References

- `layering`, `state-holders`, `data-layer`, `unit-testing`, `keystore-and-crypto` — rubrics
- `implementation-plan` — the task-level definition of done this review checks
