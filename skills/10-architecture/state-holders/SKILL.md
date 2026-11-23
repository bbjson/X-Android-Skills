---
name: state-holders
description: >-
  Model screen state as one immutable type produced by one reducer, and keep one-shot events out
  of it. Use when designing a ViewModel or presenter, choosing between MVVM and MVI, deciding
  what belongs in UiState versus an event channel, handling SavedStateHandle and arguments,
  combining several sources into one screen state, or debugging impossible UI combinations and
  duplicated loading flags.
license: Apache-2.0
metadata:
  domain: architecture
  level: core
  sources:
    - agent-skills-standard (android-state)
    - awesome-android-agent-skills (android-viewmodel)
    - chrisbanes/skills (compose-state-and-effects)
    - kotlin-kmp-claude-agent-skills (kotlin-project-state-management)
---

# State Holders

The state holder's contract: **for any point in time, the screen state is one value that is
either valid or explicitly invalid — never a combination that cannot be rendered.**

## Use when

- Creating a ViewModel/presenter for a screen or a reusable state-holding component.
- Choosing between MVVM (state + methods) and MVI (state + intents).
- Deciding whether something is state or an event (snackbar, navigation, toast).
- Passing arguments or restoring after process death (`SavedStateHandle`).
- Combining 2+ upstream sources into one screen state.
- Seeing "loading spinner + error + content" at once, or a flag explosion.

## Do not use when

- The question is Compose-side ownership/effects → `compose-state-effects`.
- The state is persisted data → `data-layer`.
- The question is DI scope of the ViewModel → `dependency-injection`.

## Rules

1. **One immutable state type per screen.** A data class for orthogonal fields, or a sealed
   hierarchy when the screen is genuinely modal (Loading / Content / Error are mutually exclusive
   — they belong in a sealed type, not three booleans).
2. **State is a value, not a bag of flags.** `isLoading`, `hasError`, `data` as three fields
   permits 8 combinations, 5 of which are meaningless. Express the meaningful ones.
3. **One-shot events are not state.** Snackbar text, navigation, "show permission dialog" go
   through a `Channel`-backed flow (or a callback), never into `UiState` — a state that "already
   happened" reappears on rotation and on every recomposition that reads it.
4. **MVVM vs MVI is a choice about who computes the next state.**
   - MVVM: state-holder methods mutate/reduce; fine for most screens.
   - MVI: one `onIntent(Intent)` entry and a pure `reduce(state, intent) -> state`; choose it when
     the same screen has many interacting actions or you need replayable state.
   Do not mix: a screen with both `fun onRetry()` and `fun onIntent()` has two entry points and no
   contract.
5. **The reducer is pure.** `reduce` takes state + event, returns state; no suspend, no I/O, no
   logging. Effects (load, save) live outside it — that is what makes the reducer testable.
6. **Arguments and restore come through `SavedStateHandle`, not constructor parameters alone.**
   A field that must survive process death is read from `SavedStateHandle` (or the typed route),
   and the typed route is the single definition of the argument.
7. **Combine upstream flows once, in the state holder.** `combine(a, b, c) { … }` +
   `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), Initial)`. Scattered
   `.stateIn` in two places produces two state objects.
8. **The `5_000` timeout is deliberate**: it survives rotation and short backgrounding without
   re-fetching; it stops collection on real backgrounding. Do not use `Eagerly` for screen state.
9. **No Android types in the state holder beyond what it must have.** No `Context`, no `View`, no
   resource ids; strings are already resolved or the state carries a
   `@StringRes` id plus arguments — pick one and be consistent.
10. **State holders do not own UI decisions that need the current composition** (focus request,
    scroll position). Those stay in the UI and travel down as values/events.
11. **Every state holder is testable with a fake and virtual time** — that is the acceptance test
    for rules 4–7.

## Procedure

1. Write the states the screen can be in, as a list. Merge those that are mutually exclusive.
2. Choose data class vs sealed by that list (rule 1/2).
3. Define events separately (rule 3); decide channel vs callback per consumer count.
4. Pick MVVM or MVI (rule 4) and write the single entry point.
5. Build the state with one `combine` + `stateIn` (rule 7).
6. Read arguments from `SavedStateHandle`.
7. Write tests for each state and each transition (see `unit-testing`).

## Checklist

- [ ] One immutable state type; no meaningless field combinations possible.
- [ ] No event/one-shot value inside the state type.
- [ ] Exactly one entry point style (methods or intents), not both.
- [ ] Reducer (if MVI) is pure and testable without coroutines.
- [ ] All restorable values read from `SavedStateHandle`/typed route.
- [ ] Single `combine` + `stateIn(WhileSubscribed(5_000))`.
- [ ] No `Context`/`View`/resource id leaking into state.
- [ ] State transitions covered by tests.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Spinner and error together | `isLoading` + `error` fields | sealed `Loading/Content/Error` | impossible combos expressible |
| Snackbar repeats on rotate | snackbar text in `UiState` | `Channel<Event>` | state replay |
| Two entry points | `onRetry()` + `onIntent()` | one contract | two sources of truth |
| Refetch on rotate | `stateIn(Eagerly)` | `WhileSubscribed(5_000)` | re-subscribe churn |
| Lost after process death | `var id: String` ctor param used directly | `SavedStateHandle` | not restored |
| Untestable VM | I/O inside `reduce` | pure reducer + effect | needs coroutine harness for logic |
| State built twice | two `stateIn` calls | one `combine` + one `stateIn` | drift |

## Verify

```bash
./gradlew :feature:feed:test --tests '*FeedViewModelTest*'
adb shell am kill <pkg>   # then relaunch: arguments and state must restore
```

Expected: tests assert the sequence `Loading → Content/Error` (see `unit-testing` Turbine rules),
and after `am kill` + relaunch the screen reopens on the same destination with its arguments.

## References

- `androidx.lifecycle:lifecycle-viewmodel-savedstate` — `SavedStateHandle`
- `SharingStarted.WhileSubscribed` — cancellation semantics
