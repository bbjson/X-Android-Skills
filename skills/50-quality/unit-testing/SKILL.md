---
name: unit-testing
description: >-
  Write JVM tests that fail when behaviour breaks and stay green when implementation changes,
  by testing observable outcomes instead of interactions. Use when adding tests for a ViewModel,
  repository, use case, mapper, or coroutine/Flow pipeline; when a test is flaky or breaks on
  every refactor; when deciding between fake and mock; or when a coroutine test hangs or needs
  dispatcher injection.
license: Apache-2.0
metadata:
  domain: quality
  level: core
  sources:
    - agent-skills-standard (android-testing)
    - android-agent-engineering (android-testing)
    - mobile-agent-skillpack (test-driven-development, mutation-testing)
    - awesome-android-agent-skills (android-testing)
---

# Unit Testing

A test earns its place by failing for exactly one reason. If it also fails when you rename a
private method, it is testing the implementation and will be deleted or ignored within a quarter.

## Use when

- Adding the first tests to a ViewModel, repository, use case, or mapper.
- A test is flaky, order-dependent, or hangs.
- Deciding fake vs mock, or how to test a `Flow`/`StateFlow`.
- A refactor broke tests that should not have broken.

## Do not use when

- The behaviour is Compose UI or interaction → `compose-ui-testing`.
- The claim is about pixels → `screenshot-testing`.
- The claim needs a real device, camera, or OS service → `e2e-device-testing`.
- You need to find *missing* tests in existing code → mutation testing (`benchmark-testing` roadmap).

## Rules

1. **Assert observable outcomes, not interactions.** `verify(repo).save(x)` is a coupling
   assertion. Assert what the caller/user can see: the emitted state, the returned value, the
   stored result. If a fake records calls, assert on its *state* after, not on call counts.
2. **Fake by default; mock only at process boundaries you cannot implement.** In-memory fake for
   repositories, dispatchers, clocks, and stores. Mocking a repository you can fake in 20 lines
   buys you refactor fragility and nothing else.
3. **One reason to fail per test.** Multiple unrelated assertions in one test hide which
   invariant broke. Group by behaviour, not by method.
4. **Inject every side-effect source: `Dispatcher`, `Clock`, `Random`, `Locale`, `NetworkMonitor`.**
   No `System.currentTimeMillis()`, no `Dispatchers.IO` literal, no `Random()` in tested code.
5. **Never `Thread.sleep` or `delay` in a test.** Advance virtual time
   (`advanceUntilIdle()`, `advanceTimeBy`) or await the state. A sleep is a flake with a timer.
6. **`StateFlow` tests must assert the whole state sequence, not just the last value.** The bug is
   almost always in the transition (`Loading → Error` vs `Loading → Success → Error`). Use Turbine
   (`test { }` + `awaitItem()`), and always `awaitComplete()`/`cancelAndIgnoreRemainingEvents()`.
7. **A cold `Flow` test needs a terminal operator inside the test scope.** `flow.test { }` does
   this; calling `first()` hides the rest of the sequence.
8. **Deterministic dispatchers per test class**, not per test:
   `Dispatchers.setMain(StandardTestDispatcher(testScheduler))` in `@Before`,
   `resetMain()` in `@After`. `UnconfinedTestDispatcher` when you want eager starts — decide once.
9. **Name the test after the invariant**: `error_keepsPreviousContent()` not
   `testLoad2()`. The name is the only documentation a failing CI run shows.
10. **Do not test the framework.** Asserting that `StateFlow.value` was set is only meaningful
    when the mapping to it is your logic. Skip tests that restate Room's or coroutines' behaviour.
11. **Cover the four edges of every branch:** empty, single, many, failure. A "many" case catches
    ordering, dedupe and pagination bugs a single-item case cannot.

## Procedure

1. Write the invariant as the test name.
2. Build the fake with the minimum state the code needs; no mocking framework unless unavoidable.
3. Arrange with explicit values (no `randomString()`, no "now").
4. Act, then assert the outcome (returned value, fake's state, emitted sequence).
5. For flows: `flow.test { assertEquals(Loading, awaitItem()); … awaitComplete() }`.
6. Run the test, then break the code deliberately and confirm it goes red.

## Checklist

- [ ] Test names state an invariant, not a method.
- [ ] No `verify(...)` on internal collaborators; no call-count assertions.
- [ ] Dispatchers/clock/random injected and deterministic.
- [ ] No `Thread.sleep`, no real `delay`.
- [ ] Flow tests assert the full sequence and terminate cleanly.
- [ ] `Dispatchers.setMain` / `resetMain` paired.
- [ ] Each branch has empty/single/many/failure coverage where meaningful.
- [ ] Test proven to fail when the behaviour is removed.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Breaks on every refactor | mock + `verify` calls | fake + assert outcome | interactions change, behaviour does not |
| Hangs forever | `runTest { repo.load().collect { } }` | `flow.test { }` with cancel | infinite collection |
| Flaky on CI | `Thread.sleep(500)` | `advanceUntilIdle()` / `awaitItem()` | timing-dependent |
| Passes with bug present | bare `assertEquals(Success, state.value)` | Turbine sequence | intermediate Error missed |
| Untestable code | `Dispatchers.IO` inside function | injected dispatcher | no virtual time |
| Time-dependent | `System.currentTimeMillis()` | injected `Clock` | untestable, TZ bugs |
| 1 giant test | 12 asserts, one test | one assert per invariant | cannot localise failure |

## Verify

```bash
./gradlew :core:data:test --tests '*RepositoryTest*'
./gradlew test --continue          # all JVM tests, no early abort
```

Then, once: delete the behaviour (comment it out) and confirm the test fails. A test never seen
red is not known to test anything.

## References

- `kotlinx-coroutines-test` — `runTest`, `StandardTestDispatcher`, `Dispatchers.setMain`
- `app.cash.turbine:turbine` — `awaitItem`, `awaitComplete`
