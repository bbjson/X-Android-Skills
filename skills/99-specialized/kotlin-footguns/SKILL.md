---
name: kotlin-footguns
description: >-
  Recognise and remove the Kotlin and Compose patterns that silently misbehave: conflation, swallowed
  exceptions, shallow copies, locale formatting, non-exhaustive when, and cancellation that never
  cancels. Use when reviewing a Kotlin diff for known traps, when behaviour is "almost right", or when a
  bug is reproducible but not explainable by reading the happy path.
license: Apache-2.0
metadata:
  domain: specialized
  level: specialized
  sources:
    - kotlin-footguns (all eleven skills)
    - mobile-agent-skillpack (kotlin-null-safety, kotlin-coroutines)
    - agent-skills-standard (kotlin-best-practices)
    - skydoves/compose-performance-skills (side-effects)
---

# Kotlin Footguns

Each entry below is a construct that **compiles, looks correct, and fails in production**. The scan is
mechanical: grep the diff, then decide.

## Use when

- Reviewing a Kotlin/Compose diff and you want a trap checklist.
- Behaviour is "almost right" — an event missed, a value stale, a copy shared.
- A test passes but production misbehaves.
- Onboarding a codebase: run the scan to find its existing traps.

## Do not use when

- The bug has a known reproduction and cause → `bug-fix`.
- The concern is architecture → `layering`.
- The concern is Compose performance specifically → `recomposition`.

## Rules

1. **`StateFlow` conflates; it is not a queue.** Rapid updates collapse and the collector sees only the
   latest. For events use `Channel` (`receiveAsFlow`), for buffered state use `SharedFlow(replay, extraBufferCapacity)`.
2. **`runCatching { }` catches `CancellationException`.** Swallowing it breaks cancellation (a cancelled
   coroutine keeps running). Re-throw it: `runCatching { }.onFailure { if (it is CancellationException) throw it }`
   or catch specific exceptions.
3. **`data class copy()` is shallow.** `copy(items = items)` shares the same mutable list; mutations leak
   between "copies". Use immutable collections (`ImmutableList`) or copy the collection.
4. **`val list = listOf(...)` is read-only, not immutable.** The underlying list can be a mutable one cast
   down; treat only `kotlinx.collections.immutable` types as truly immutable across boundaries.
5. **`String.format`/`toUpperCase()`/`NumberFormat` default to the device locale.** Turkish `i` → `İ`,
   Arabic digits, German decimal comma. Always pass an explicit `Locale` for machine-facing strings;
   pass the user locale deliberately for display.
6. **Non-exhaustive `when` on an enum compiles when it has an `else`.** A new enum value silently falls
   into `else` (often a no-op). Omit `else` so the compiler forces an update, except for sealed
   hierarchies where exhaustiveness is checked.
7. **`Flow` is cold; collecting twice executes twice.** Two `collect` calls (or one in the UI and one in a
   test) duplicate network calls. Share with `stateIn`/`shareIn` when the work is expensive.
8. **`viewModelScope.launch` inside `init` with a blocking call is not cancellable by Back.** The scope
   outlives the screen until `onCleared`; a long blocking call must be interruptible or dispatcher-based.
9. **`lateinit` hides an ordering bug.** A `lateinit` accessed before assignment throws
   `UninitializedPropertyAccessException` at a random later point. Prefer constructor `val` or nullable
   with an explicit state.
10. **`Thread.sleep`/`runBlocking` on the main thread freezes the UI** and, in a Flow, blocks cancellation.
    Use `delay`, injected dispatchers, or `runInterruptible`.
11. **`equals` on `Float`/`Double` and money in `Double`.** Use integer minor units for money, and
    epsilon/`BigDecimal` for other floats; `0.1 + 0.2 != 0.3`.
12. **Compose `remember` without keys keeps stale values**; and `remember(key)` with a new instance key
    invalidates every time (see `recomposition` cause (b)).
13. **`collectAsState()` keeps collecting in the background**; use `collectAsStateWithLifecycle()`
    (`compose-state-effects` rule 4).
14. **`Dispatchers.Main` in common code / on a background thread throws** — inject it; never assume.

## Procedure

Scan a diff (or a module) mechanically, then read each hit:

```bash
grep -rn "runCatching" --include=*.kt . | grep -v test
grep -rn "\.copy(" --include=*.kt . | head -20
grep -rn "String.format\|toUpperCase()\|toLowerCase()\|NumberFormat" --include=*.kt . | grep -v "Locale"
grep -rn "collectAsState()" --include=*.kt . | grep -v Lifecycle
grep -rn "Thread.sleep\|runBlocking" --include=*.kt . | grep -v test
grep -rn "lateinit" --include=*.kt . | head -20
grep -rn "when (" --include=*.kt -A8 . | grep -B2 "else ->"   # enum whens with else
grep -rn "Double\|Float" --include=*.kt . | grep -i "price\|amount\|money"
```

For each hit: is the construct one of the traps above? If yes, classify (correctness / cancellation /
locale / immutability) and fix with the corresponding rule.

## Checklist

- [ ] Event delivery not via `StateFlow`.
- [ ] `runCatching` re-throws `CancellationException`.
- [ ] Copies of collections are deep or immutable.
- [ ] Machine-facing string/format operations pass an explicit `Locale`.
- [ ] Enum `when` without `else` (or the `else` is intentional and documented).
- [ ] Cold Flows shared where work is expensive.
- [ ] No `lateinit` where a constructor `val` works.
- [ ] No `Thread.sleep`/`runBlocking` on main or in Flow.
- [ ] Money as integer minor units.
- [ ] `collectAsStateWithLifecycle` in UI.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Event lost under load | `StateFlow` for events | `Channel` | conflation |
| Cancelled job keeps running | `runCatching {}` | re-throw `CancellationException` | cancellation swallowed |
| Shared mutation | `copy(items = items)` | `copy(items = items.toImmutableList())` | shallow copy |
| Break on Turkish locale | `"I".toLowerCase()` | `toLowerCase(Locale.ROOT)` | locale-sensitive |
| Stale value | `remember { }` no key | `remember(key)` | never invalidated |
| Crash in prod | `lateinit` ordering | `val` / nullable | hidden init order |
| UI freeze | `runBlocking` on main | `delay` / dispatcher | blocks thread |

## Verify

```bash
./gradlew :app:assembleDebug test
```

Behavioural checks: with the device locale set to `tr-TR` and `ar-EG`, no formatting crash and no
mangled machine identifiers; a cancelled scope (navigating away) stops the work within a frame.

## References

- `CancellationException` and structured concurrency
- `kotlinx.collections.immutable`, `Locale.ROOT`, `BigDecimal` for money
