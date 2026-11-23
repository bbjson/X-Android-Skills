---
name: structured-concurrency
description: >-
  Decide coroutine scope ownership, cancellation propagation, exception handling and Flow
  buffering so work stops when its owner stops and failures stay local. Use when creating a scope
  or Job, using async/launch in parallel, catching exceptions around suspend calls, choosing
  StateFlow vs SharedFlow vs Channel, debugging a coroutine that never cancels, or a crash from
  an exception nobody awaited.
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - kotlinlang (coroutines guide, re-expressed)
    - this-repo (gap analysis: only footgun fragments existed)
---

# Structured Concurrency

One decision: **every coroutine has an owner, and that owner's lifetime is the answer to "when
does this stop".** If you cannot name the scope, you do not yet know when the work dies.

## Use when

- Creating a `CoroutineScope`, `Job`, `SupervisorJob`, or launching from a non-UI owner.
- Running work in parallel (`async`/`awaitAll`) or racing (`select`).
- Wrapping suspend calls in `try`/`catch` or `runCatching`.
- Choosing between `StateFlow`, `SharedFlow` and `Channel` for a stream of values or events.
- A coroutine keeps running after its screen is gone, or a test hangs.
- Editing `**/*ViewModel.kt`, `**/*Repository.kt`, or any `suspend` function.

## Do not use when

- Which owner holds UI state and how effects are triggered → `compose-state-effects`.
- Rx stream conversion and subscription lifetime → `rxjava-to-coroutines`.
- Test-only dispatch/dispatcher rules → `unit-testing`.
- Chooser between MVVM and MVI, and what belongs in the state type → `state-holders`.

## Rules

1. **`GlobalScope` is forbidden.** Every coroutine belongs to a scope with a real owner:
   `viewModelScope`, `lifecycleScope`, a repository-owned `SupervisorJob` scope with an explicit
   `close()`/`cancel()`.
2. **`viewModelScope` cancels at `onCleared`.** Work that must survive the screen (upload, sync)
   belongs to a repository or `WorkManager` scope (`background-work`), not to the ViewModel.
3. **`CancellationException` must propagate.** `catch (e: Exception)` and `runCatching` both swallow
   it; rethrow explicitly (`if (e is CancellationException) throw e`) or catch narrower types.
   Swallowing it makes `withTimeout` and navigation-cancel silently not work.
4. **`coroutineScope { }` fails fast; `supervisorScope { }` isolates.** Sibling `async` failures
   cancel each other in the former and do not in the latter. Pick by whether partial success is
   meaningful, and record the choice.
5. **Never `async` without awaiting inside the same scope.** A fire-and-forget `async` hides its
   exception until the scope ends, then crashes an unrelated place. Fire-and-forget work is
   `launch` with its own try/catch.
6. **Cleanup that must run on cancellation uses `withContext(NonCancellable)`.** Releasing a lock,
   closing a stream or deleting a temp file in a `finally` that itself suspends needs it.
7. **Check cancellation in long CPU loops** (`ensureActive()`/`isActive`). A tight loop ignores
   cancellation and keeps a dead ViewModel's work on the main thread.
8. **Dispatchers are injected, not hardcoded** — an `ioDispatcher: CoroutineDispatcher` parameter,
   so tests are deterministic without `Dispatchers.setMain` gymnastics.
9. **`flowOn` changes only upstream.** It does not move `collect`; putting it after a `map` does not
   make that `map` off-main.
10. **`StateFlow` for state, `Channel`/`receiveAsFlow` for one-shot events, `SharedFlow` only when
    multiple collectors must each see the value.** A `SharedFlow(replay = 1)` used as an event bus
    replays after rotation — the classic duplicate-navigation bug.
11. **Hot streams are started with an explicit sharing policy:** `stateIn(scope, WhileSubscribed(5_000), initial)`
    for UI state, so a configuration change does not re-fetch.
12. **Backpressure is a decision, not a default:** with `extraBufferCapacity > 0` and
    `onBufferOverflow = DROP_OLDEST`, values are silently lost. If loss is unacceptable, use a
    suspending/channel design and say so.
13. **Mutex for shared mutable state; `AtomicX`/`Mutex` instead of `synchronized`** in coroutine
    code, because a blocking monitor can deadlock a dispatcher thread that must resume the holder.

## Checklist

- [ ] Every `launch`/`async` sits in a named scope; no `GlobalScope`.
- [ ] Long-lived work is in a repository/`WorkManager` scope, not `viewModelScope`.
- [ ] No `catch (e: Exception)` or `runCatching` that drops `CancellationException`.
- [ ] `async` results are awaited in the same scope.
- [ ] Cancellation-sensitive cleanup wrapped in `NonCancellable`.
- [ ] CPU loops call `ensureActive()`.
- [ ] Dispatchers injected via constructor parameters.
- [ ] `flowOn` placed where it actually changes the upstream.
- [ ] State/event stream types match rule 10; sharing policy explicit.
- [ ] Buffer overflow policy stated where a buffer exists.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Work after screen death | `GlobalScope.launch` | repository scope or `viewModelScope` | nothing cancels it |
| Timeout never fires | `runCatching { withTimeout(...) }` | rethrow `CancellationException` | cancellation swallowed |
| Crash in unrelated code | `async` never awaited | `launch` + own try/catch | exception surfaces at scope end |
| Double navigation | `SharedFlow(replay = 1)` | `Channel` + `receiveAsFlow` | replay on rotation |
| Re-fetch on rotate | cold flow per collection | `stateIn(WhileSubscribed(...))` | new upstream each collect |
| Lock never released | `finally` with suspend cleanup | `withContext(NonCancellable)` | finally cannot suspend |
| Deadlock on main | `synchronized` around suspend | `Mutex` | blocking a dispatcher thread |

## Verify

```bash
./gradlew :app:testDebugUnitTest --tests '*ViewModelTest*'
grep -rn "GlobalScope" --include=*.kt app core domain | grep -v Test | wc -l    # expected: 0
grep -rn "runCatching" --include=*.kt app core domain | grep -v Test | wc -l    # review each hit
```

Expected: tests green; no production `GlobalScope`; every `runCatching` around a suspend call is
paired with a `CancellationException` rethrow.

## References

- Kotlin coroutines: `coroutineScope`, `supervisorScope`, `NonCancellable`, `ensureActive`
- Flow: `stateIn`, `shareIn`, `flowOn`, `buffer`/`onBufferOverflow`
- `CancellationException` semantics in `kotlinx.coroutines`
