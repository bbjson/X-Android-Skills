---
name: deliver-pr
description: >-
  Turn finished work into a pull request a reviewer can act on in one pass: single purpose, atomic
  commits, a description that states why/what/risk/verification, green CI, and a merge strategy that
  preserves the reason. Use when opening a PR, when a PR has been sitting unreviewed, when asked to
  "just push it", or when a change is too large to describe in one sentence.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - chrisbanes/skills (shepherd, changelog, deliver-issue)
    - mobile-agent-skillpack (requesting-code-review, bitbucket-pr-summary-qa)
    - android-agent-engineering (workflows/implement)
    - android-skill (review-android)
---

# Deliver PR

A pull request is a **claim plus its evidence**. If the claim cannot fit in one sentence, the PR is
two PRs.

## Use when

- Implementation is finished and you are about to request review.
- A PR is large, or has grown by "one more thing".
- Review feedback has arrived and you must respond.
- You need to decide the merge strategy (squash vs merge vs rebase).

## Do not use when

- The change is not implemented yet → `implementation-plan` / `implement`.
- The task is reviewing someone else's PR → `code-review`.
- The change is a mechanical refactor → `refactor` first, then this skill.

## Rules

1. **One sentence test.** Write "This PR `<does X>` so that `<Y>`." If it needs "and", split the PR.
   This is also the title.
2. **Commits are atomic and named after the transformation/reason**, not "wip", "fix", "update". The
   history is for the person bisecting a bug six months later.
3. **The description has five sections, always:** why (the problem), what (the change), risk (what
   could break and how it is mitigated), verification (commands/results/screenshots), rollback (how to
   undo).
4. **Self-review the diff before requesting review.** Read it top to bottom as if it were someone
   else's; you will find the leftover debug log and the accidental formatting.
5. **CI must be green for the checks the branch protects**, not "will be green". A reviewer who has to
   wait for CI is a reviewer who context-switches away.
6. **Screenshots or recordings for any user-visible change.** A UI PR without an image costs a round
   trip; a UI PR with a broken image costs trust.
7. **Link the issue and the spec.** `Closes #123`, and the spec/plan if one exists. The reviewer needs
   the intended behaviour, not just the diff.
8. **Squash merge by default** for feature branches (one logical change = one commit on the main
   line), but keep the PR body as the commit message body. Merge commits are for long-lived branches
   whose individual commits matter.
9. **Respond to review with either a change or a reason, never silence.** "Won't fix because …" is a
   valid answer; an unaddressed comment is not.
10. **A PR that grows past its sentence is closed and split.** Adding "while I'm here" commits is how
    a 200-line review becomes a 900-line one and gets rubber-stamped.
11. **Do not merge your own PR without review** unless the project explicitly allows it (solo repo,
    trivial change). Force-push after review only if the review was on content, not commits.

## Procedure

1. Run the local equivalent of CI: `./gradlew assembleDebug lintDebug testDebugUnitTest`.
2. `git log --oneline main..HEAD` — squash/rename commits that are noise.
3. Self-review: `git diff main...HEAD` and fix anything you would comment on.
4. Write the five sections; capture screenshots for UI changes.
5. Open the PR with the one-sentence title; request review from the owner of the touched area.
6. On feedback: address or explain each comment in a thread, then re-request.
7. Merge per the project's strategy; delete the branch.

## Checklist

- [ ] One-sentence title, no "and".
- [ ] Commits atomic, named by reason.
- [ ] Description has why / what / risk / verification / rollback.
- [ ] Self-reviewed the full diff.
- [ ] CI green (or the failure is explained and pre-existing).
- [ ] Screenshots for user-visible changes.
- [ ] Issue/spec linked.
- [ ] No unrelated formatting/rename/version bumps.
- [ ] Every review comment addressed or answered.
- [ ] Merge strategy matches the project's convention.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Rubber-stamped | 900-line "misc" PR | split by sentence | unreviewable |
| Empty description | "fixes stuff" | five sections | reviewer guesses intent |
| Reviewer waits | "CI will pass" | run it locally | context loss |
| Round trip | no screenshot for UI change | attach image | visual claim needs proof |
| Lost reason | squash with "wip" | body carries the why | future bisect |
| Ignored comment | silence | fix or explain | review stalls |
| Mixed change | refactor + feature | two PRs | neither revertable |

## Verify

The PR is reviewable when a reviewer who has not seen the work can answer from the PR alone:

1. What problem does this solve?
2. What exactly changed?
3. What could break, and how was it checked?
4. How do I undo it?

If any answer requires asking you, the description is incomplete.

Expected: a reviewer who never saw the work can answer all four questions from the description alone.

## References

- `code-review` — the rubric the reviewer will apply
- `implementation-plan` — the task list this PR closes
