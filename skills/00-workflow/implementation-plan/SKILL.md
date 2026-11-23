---
name: implementation-plan
description: >-
  Convert a spec into an ordered set of independently verifiable tasks, each with a definition of
  done, the command that proves it, and an explicit dependency on the task before it. Use when
  starting implementation of a multi-file change, when work must be split across sessions or
  agents, when a change is too large for one reviewable commit, or when you need to know what can
  be done in parallel.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering (workflows/implementation-plan, workflows/implement)
    - chrisbanes/skills (to-plan, implement-with-subagents)
    - mobile-agent-skillpack (executing-plans, writing-plans, dispatching-parallel-agents)
---

# Implementation Plan

A plan is a **sequence of green states**. After every task the repository builds, tests pass, and
the change is revertable. If a task cannot be verified alone, it is not a task.

## Use when

- A spec exists and implementation is about to start.
- The change touches ≥3 files or ≥2 layers.
- Work will be interrupted (sessions, agents, days).
- You need to identify what is parallelisable.
- A task feels "too big to describe" — that is the signal to split it.

## Do not use when

- The change is one file / one obvious edit — just do it.
- The spec is missing → `feature-to-spec`.
- The work is reviewing someone else's change → `code-review`.

## Rules

1. **Every task ends at a green state.** Definition of done must include: build command, test
   command, and what observable behaviour changed. "Add the repository" is not done until
   `:core:data:test` passes.
2. **One task ≈ one reviewable commit, ≤ half a day.** If a task needs a paragraph of caveats, split
   it. Big tasks hide the failure until the end, which is when it is most expensive.
3. **Order by dependency, then by risk.** The riskiest / most uncertain task goes early (a spike),
   because discovering it cannot work after everything else is built destroys the plan.
4. **Dependencies are explicit and directional.** `T3: depends on T2`. If a task has no predecessor
   and no successor, ask whether it is needed at all.
5. **Contract before implementation.** First task is types/interfaces (domain + UiState), so the rest
   can be written in parallel against a compiling contract.
6. **Tests are scheduled as tasks, not as a phase at the end.** For each behaviour task, the test is
   either part of it or the immediately following task.
7. **Mark the parallelisable set explicitly.** Tasks with no shared files and no dependency can run
   concurrently; tasks touching the same file must be serialised regardless of the graph.
8. **Every task names its revert plan.** Usually "revert this commit"; if not possible (schema
   migration, published artefact), say what "undo" means instead.
9. **The plan states what is *not* in it.** Out-of-scope items from the spec are listed so a reader
   does not expect them.
10. **Estimate in tasks, not hours.** If you must estimate, use a range and mark it as a guess.
    A plan of 4 big tasks is almost always a plan of 11 real ones.

## Procedure

1. Extract the artefacts the spec requires: types, interfaces, stores, screens, tests.
2. Cut tasks by **verifiable milestone**, not by file type (rule 1).
3. Write each task as: `id | description | inputs | done (command + observable) | depends on`.
4. Find the critical path; move the riskiest node to the front (rule 3).
5. Identify parallel groups; note file-overlap conflicts (rule 7).
6. Add the test tasks.
7. Add a "not in this plan" section.

## Checklist

- [ ] Every task has a done condition with a command and an observable.
- [ ] No task exceeds one commit / half a day.
- [ ] Dependency edges written; no orphan tasks.
- [ ] Contracts task precedes implementation tasks.
- [ ] Test task per behaviour, scheduled not deferred.
- [ ] Parallel groups marked, file overlaps identified.
- [ ] Each task has a revert plan.
- [ ] "Not in this plan" section present.
- [ ] Riskiest task is early.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Red build mid-plan | task 3 of 9 leaves tests broken | each task ends green | cannot bisect or revert |
| Rework at the end | schema task last | contracts + risk first | late discovery is expensive |
| Unverifiable task | "wire up DI" with no check | "DI resolves X; `:app:assembleDebug` passes" | nothing to accept |
| Hidden scope | plan implies everything | explicit "not in this plan" | expectations drift |
| Fake parallel | two agents edit the same ViewModel | serialise by file | merge conflicts |
| 4 mega-tasks | "add the feature" ×4 | 11 verifiable tasks | no progress signal |

## Verify

The plan is executable when you can answer, for the **next** task only:

1. What command proves it is done?
2. What is the observable difference before/after?
3. What does reverting it look like?

If any answer requires opening a file, the task is not planned yet.

Expected: for the next task only, the command, the observable change, and the revert are all answerable without opening a file.

## References

- `feature-to-spec` — the input to this plan
- `code-review` — what each task will be judged by
