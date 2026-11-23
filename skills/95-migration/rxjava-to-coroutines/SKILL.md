---
name: rxjava-to-coroutines
description: >-
  Migrate RxJava 2/3 streams to suspend functions and Flow without changing behaviour: operator
  mapping, backpressure, subscription lifetime, error handling, threading, and interop during the
  transition. Use when replacing RxJava in a module, when a stream type is Rx in a coroutine codebase,
  when CompositeDisposable management is leaking, or when observable semantics (hot vs cold) differ
  from Flow.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - awesome-android-agent-skills (rxjava-to-coroutines-migration)
    - agent-skills-standard (android-concurrency)
    - agent-agent-engineering (kotlin-coroutines-flow)
    - mobile-agent-skillpack (kotlin-coroutines)
---

# RxJava to Coroutines

The hard part is not operator names — it is that **Rx streams are hot/cold with their own subscription
model**, and Flow is always cold. Most behaviour changes during this migration come from that.

## Use when

- Converting a module/repository/ViewModel from RxJava to coroutines.
- An Rx type appears in an otherwise coroutine codebase.
- `CompositeDisposable`/`Disposable` management leaks or is applied inconsistently.
- A converted stream behaves differently (missed events, restarts, no replay).

## Do not use when

- The code is already coroutine-based and just misuses Flow → `compose-state-effects` /
  `unit-testing`.
- The target is Kotlin Multiplatform streams → `kmp` (RxJava is JVM-only).
- The concern is UI state shape → `state-holders`.

## Rules

1. **Map by cardinality first, then operators.** `Single<T>` → `suspend fun (): T`. `Maybe<T>` →
   `suspend fun (): T?`. `Completable` → `suspend fun ()` returning `Unit`. `Observable`/`Flowable` →
   `Flow<T>` (cold) or `StateFlow`/`SharedFlow` (hot, if it was a Subject).
2. **`CompositeDisposable` → a `CoroutineScope`** owned by the same thing (ViewModel → `viewModelScope`).
   Do not create ad-hoc scopes per call; that is the same leak in a new costume.
3. **Subscribe/observe thread selection becomes `flowOn` for upstream and the collector's context for
   downstream.** `subscribeOn(io)` ≈ `flowOn(Dispatchers.IO)` on the upstream; `observeOn(main)` ≈
   collecting from the main dispatcher. One `flowOn` per distinct upstream, not per operator.
4. **`Subject`s must become `StateFlow`/`SharedFlow`/`Channel` by intent**, not mechanically:
   `BehaviorSubject` (has a value, replays 1) → `StateFlow`; `PublishSubject` (events) →
   `SharedFlow(replay=0)` or `Channel` for one-shot; `ReplaySubject` → `SharedFlow(replay=n)`.
5. **Errors: `onErrorReturn` → `catch`, `onErrorResumeNext` → `catch { emitAll(…) }`, `retryWhen` →
   `retryWhen` on Flow (same name, different signature).** A thrown exception in a Flow cancels the
   collection — that is the equivalent of `onError` terminating the stream, so handle it or it kills the
   scope.
6. **Backpressure: `Flowable` semantics do not exist in Flow.** Flow is suspend-based, so the consumer
   is the backpressure. If the original used `onBackpressureBuffer`, the consumer must be fast enough or
   you need `.buffer()`. Verify with a slow collector test, not by inspection.
7. **Cold vs hot is the migration's main risk.** An `Observable` that was shared (`.share()`,
   `.replay().refCount()`) became a Flow that restarts per collector. Add `.shareIn(scope, started, replay)`
   deliberately, and only where the original was shared.
8. **Interop in both directions during the transition:** `Flow.asObservable()`/`Observable.asFlow()`
   (from `kotlinx-coroutines-rx3`). Use it to migrate leaf-first, and mark every interop boundary so it
   can be removed.
9. **Cancellation is cooperative.** Rx `dispose()` stops emissions; a coroutine only stops at suspension
   points. A blocking call inside a Flow ignores cancellation — use `runInterruptible`/injectable
   dispatcher or the collector cannot cancel.
10. **Tests move from `TestObserver` to Turbine with virtual time.** `TestScheduler.advanceTimeBy` →
    `advanceTimeBy` on the test dispatcher; assert the sequence with `awaitItem()`, not the last value.

## Procedure

1. Inventory types: `grep -rn "Observable<\|Single<\|Maybe<\|Completable\|Flowable<\|CompositeDisposable\|Disposable" --include=*.kt .`
2. Convert leaves first (repositories) to `suspend`/`Flow`, keeping public signatures for one commit
   where callers are still Rx (via `asObservable()` at the boundary).
3. Replace `CompositeDisposable` with the owner's scope; delete manual `dispose()` calls.
4. Convert Subjects by intent (rule 4); convert shared Observables with `shareIn` (rule 7).
5. Convert operator chains; fix error handling (rule 5) and `flowOn` placement (rule 3).
6. Convert tests to Turbine; verify sequences and timing.
7. Remove interop boundaries and the RxJava dependency once no Rx types remain.

## Checklist

- [ ] Cardinality mapping applied (`Single`/`Maybe`/`Completable`/`Observable`).
- [ ] `CompositeDisposable` replaced by the owner's scope.
- [ ] `flowOn` on upstream, collector context downstream.
- [ ] Subjects converted by intent (`StateFlow`/`SharedFlow`/`Channel`).
- [ ] Error handlers converted; no unhandled throw killing the scope.
- [ ] Backpressure verified with a slow collector.
- [ ] Shared streams use `shareIn` explicitly; cold streams stay cold.
- [ ] Cancellation verified for blocking calls.
- [ ] Tests converted to Turbine.
- [ ] Interop boundaries removed and RxJava dependency gone.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Duplicate work after migration | `.share()` dropped | `shareIn(scope, WhileSubscribed, 1)` | cold restart per collector |
| Restart loops | `BehaviorSubject` → cold Flow | `StateFlow` | cold re-executes |
| Missing events | `PublishSubject` → `StateFlow` | `SharedFlow`/`Channel` | StateFlow conflates |
| Scope crash | unhandled exception in Flow | `catch` | throw cancels collection |
| Main-thread work | `flowOn` on the collector side | upstream `flowOn` | wrong side |
| Uncancellable work | blocking call in Flow | `runInterruptible`/dispatcher | ignores cancellation |
| Leak | `GlobalScope.launch` | owner scope | no lifecycle |

## Verify

```bash
./gradlew :core:data:test
grep -rn "Observable<\|Single<\|CompositeDisposable" --include=*.kt core/data/src/main   # must be empty
./gradlew :core:data:dependencies | grep -c rxjava                                       # 0 at the end
```

Expected: identical emitted sequences (Turbine) before and after for the same inputs, no leaked
collections after the screen closes, and no RxJava on the module's classpath at completion.

## References

- `kotlinx-coroutines-rx3` — `asFlow()` / `asObservable()`, `rxSingle`
- Turbine for sequence assertions; `shareIn`/`stateIn` sharing semantics
