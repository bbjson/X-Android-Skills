---
name: feature-to-spec
description: >-
  Turn grilled requirements into an engineering spec with an exhaustive state machine, an error
  matrix, API contracts and a test plan, before any implementation file is created. Use when
  requirements are decided and before planning tasks, when a feature spans multiple screens or
  data sources, when the same error can arrive from three places, or when an implementation
  started and keeps discovering new states.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering (workflows/feature-to-spec, workflows/implementation-plan)
    - mobile-agent-skillpack (writing-plans, mobile-modern-clean-architecture)
    - agent-skills-standard (system-design)
---

# Feature to Spec

A spec is a **closed set of states plus the transitions between them**. If the state set is not
closed, implementation will keep discovering new states — each one a small redesign.

## Use when

- Requirements are decided (see `requirements-grill`) and code has not been written.
- The feature has ≥2 screens, ≥2 data sources, or a background/notification path.
- A single user action can fail in multiple ways (validation, network, auth, conflict).
- Implementation has started and "one more state" keeps appearing.

## Do not use when

- Requirements are still ambiguous → `requirements-grill` first.
- The change is a defect fix → `bug-fix`.
- The task is already a concrete list of edits → `implementation-plan` directly.

## Rules

1. **Enumerate states before screens.** List every state the feature can be in, as a closed set.
   Each state must be renderable by some screen. Any state with no screen is dead; any screen
   input not in the set is a missing state.
2. **Model the error matrix — errors are not one state.** At minimum: validation (local),
   permission denied, offline, timeout, server 4xx, server 5xx, conflict/stale, corrupt cache.
   For each: what the user sees, what is retryable, what is preserved.
3. **Write interface signatures before implementations.** Repository/use-case methods with types,
   nullability and failure type. If a signature is awkward to write, the design is awkward.
4. **One UiState type per screen, derived from the state set.** (See `state-holders` for shape.)
   The spec names each state, not "handle loading".
5. **Events are listed separately from state.** Navigation, snackbar text, permission prompts:
   name them, name their trigger, name their consumer. (See `compose-state-effects` rule 5.)
6. **Data ownership is explicit per field.** Which store, which cache, which lifecycle, what
   survives process death. Unstated ownership is the top cause of "worked in dev".
7. **Non-goals and boundaries carry over verbatim from the grill.** Do not soften them.
8. **The test plan is part of the spec, not a later task.** For each state and each error: the test
   name that proves it. Missing test = state not designed.
9. **No implementation detail beyond what constrains the design.** Do not specify file names,
   private helpers or line-by-line structure — that belongs to `implementation-plan`.
10. **Every acceptance criterion is checkable by someone who did not write the code.** Numbers,
    observable UI, or a command's output. "Fast" and "robust" are not criteria.

## Procedure

1. Copy the eight grill slots (actor, happy path, data source, states, boundaries, permissions,
   non-goals, done).
2. Expand slot 4 into the closed state list (rule 1).
3. Fill the error matrix (rule 2).
4. Write typed interfaces (rule 3).
5. Map states → per-screen UiState types (rule 4).
6. List events + triggers + consumers (rule 5).
7. Fill data ownership table (rule 6).
8. Write the test plan as named tests (rule 8).
9. Review against rule 10; split anything that fails.

## Checklist

- [ ] Closed state set; every state has a renderer; no unreachable state.
- [ ] Error matrix covers validation, permission, offline, timeout, 4xx, 5xx, conflict, corruption.
- [ ] Every error names what is retryable and what is preserved.
- [ ] Interface signatures written with nullability and failure types.
- [ ] One UiState type per screen, named after the state set.
- [ ] Events listed with trigger and consumer.
- [ ] Data ownership table filled per field (store, lifecycle, process-death).
- [ ] Non-goals unchanged from the grill.
- [ ] Test plan names one test per state and per error.
- [ ] Acceptance criteria are checkable by a third party.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Endless states | "we'll handle states as they come" | closed set up front | each discovery = redesign |
| One error state | `Error(String)` for everything | matrix with 8 classes | wrong retry affordance |
| Spec = code | file-by-file instructions | states + contracts + tests | micromanagement, stale fast |
| Untestable criteria | "should be responsive" | "list scrolls at ≥50fps on <device>" | nothing to verify |
| Forgotten events | snackbar in UiState | named event + consumer | replay bugs |
| Ambiguous ownership | "cached somewhere" | store, lifecycle, process-death | dev-only success |

## Verify

The spec is complete when a second engineer can answer, from the document alone:

1. What are the states, and which screen renders each?
2. What happens on each of the eight error classes?
3. Which tests must exist before this is "done"?

If any answer requires asking the author, the spec is not finished.

Expected: a second engineer can answer the three questions without asking the author.

## References

- `state-holders` — the shape of the UiState types this spec names
- `bug-fix` — what happens when a state was missed (it becomes a defect)
