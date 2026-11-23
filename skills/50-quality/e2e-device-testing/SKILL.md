---
name: e2e-device-testing
description: >-
  Run end-to-end flows on a real device or a managed emulator that are trustworthy: isolated accounts
  and data, no sleeps, deterministic waits, evidence on failure, and a suite small enough to stay under
  its time budget. Use when adding an E2E test, when instrumented tests flake in CI, when a flow spans
  login → action → notification → deep link, or when deciding what belongs in E2E versus unit/UI tests.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - android-agent-engineering (android-testing)
    - mobile-agent-skillpack (mobile-ci-release-flow)
    - micorlov-e2e-mobile
    - Appium-Scripter
    - android-qa-kit
---

# E2E Device Testing

An E2E test is the most expensive test you can write. It earns that cost only if it **covers a
contract no cheaper test can** — a real OS integration, a real app boundary, a real device sensor.

## Use when

- The flow crosses app boundaries: permission dialog, notification, deep link, share sheet, account
  manager, biometric prompt, background work.
- Validating a release build against real OS behaviour.
- A bug escaped unit + UI tests because it involved the platform.
- Building a smoke suite for release candidates.

## Do not use when

- The claim is logic or state transitions → `unit-testing`.
- The claim is Compose rendering/interaction → `compose-ui-testing`.
- The claim is pixels → `screenshot-testing`.
- The claim is performance → `benchmark-testing`.

## Rules

1. **E2E is for boundaries only.** If a scenario can be proven with a fake at a lower level, do it
   there. A 40-test E2E suite is a sign that unit tests are missing, and it will be skipped within a
   year because it takes 30 minutes.
2. **Every test owns its data.** Fresh account (or a seeded fake backend), `clearPackageData`/`pm clear`,
   no shared fixture that another test mutates. Cross-test state is the #1 flake source in E2E.
3. **Wait on conditions, never on time.** `IdlingResource`/`waitUntil` for UI, polling for a file or
   notification. A `Thread.sleep` in an E2E test is a future failure on a slower device.
4. **Disable animation and system dialogs that steal focus.** Animation scales to 0; do not let a
   "system update" dialog land on top of the test.
5. **Prefer a real user path over a helper shortcut.** Logging in via the login screen tests the login
   screen; injecting a token does not. Use the shortcut only for tests whose subject is elsewhere, and
   label it.
6. **No network dependency on a real backend you do not control.** Use a test environment with a
   `/healthcheck` you can wait on, or a mocked server (MockWebServer/Docker). A test that fails when
   someone deploys is not a test.
7. **On failure, capture evidence automatically:** screenshot, `logcat -d` for the app pid, and the
   UI tree dump. A failure without these becomes a manual re-run.
8. **Retries hide flakiness; fix or delete instead.** A `@Retry` policy masks real defects and
   multiplies suite time. Allow at most one retry *while triaging*, never permanently in the suite.
9. **Keep the suite under a fixed budget** (e.g. ≤10 minutes on the reference device). When it grows,
   move scenarios down a level rather than splitting CI into more agents.
10. **Run against a release-like build.** `debuggable=false`, R8 enabled, real signing (upload key) —
    this is where the R8/serialization/DI failures appear that debug builds hide.
11. **Managed devices over a single hand-managed emulator.** Gradle Managed Devices (or an equivalent)
    gives reproducible API levels and clean state per run.

## Procedure

1. Decide the boundary being tested; write it down. If it is not a boundary, move the test down.
2. Create the test in the instrumented source set (`androidTest`) or a managed-device source set.
3. Isolate state (rule 2) in `@Before`; add a cleanup in `@After` for anything the app writes.
4. Drive the flow with waits on conditions (rule 3).
5. Add evidence capture on failure (rule 7) via a test rule.
6. Run locally on a physical device; then in CI on a managed device with the release-like build.
7. Measure duration; if over budget, demote a scenario.

## Checklist

- [ ] Test covers a real app/OS boundary; it could not be replaced by a unit or UI test.
- [ ] State isolated per test (`clearPackageData`, fresh account, no shared fixture).
- [ ] No `Thread.sleep`; all waits are condition-based with timeouts.
- [ ] Animations disabled; interfering system dialogs handled.
- [ ] Backend is controlled (test env with healthcheck or a mock).
- [ ] Failure evidence: screenshot + logcat + UI dump.
- [ ] No permanent retry policy.
- [ ] Suite within its time budget.
- [ ] Runs against release-like build in CI.
- [ ] Managed device / reproducible API level.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| 30-minute suite nobody runs | E2E for everything | boundaries only | cost without value |
| Flaky on CI | shared account across tests | isolate state per test | order dependence |
| `sleep(2000)` everywhere | fixed delays | condition waits | device speed |
| Green with broken release | debug build only | release-like build | R8/DI failures hidden |
| Hidden flakiness | permanent `@Retry` | fix or delete | masks real defects |
| Fails on deploy day | real staging backend | mock or healthchecked env | external coupling |
| No diagnosis | assert failure only | screenshot + logcat | manual re-run |

## Verify

```bash
./gradlew :app:connectedDebugAndroidTest
# managed devices
./gradlew :app:pixel6Api34DebugAndroidTest
adb -s <serial> shell pm list instrumentation
```

Expected: the suite passes twice in a row from a clean state, each test under its budget, and a
deliberately broken flow produces a failure with an attached screenshot and logcat excerpt.

## References

- Gradle Managed Devices (`testOptions.managedDevices`)
- `IdlingResource`, `UiAutomator`, `ComposeTestRule.waitUntil`
