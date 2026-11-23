---
name: baseline-profiles
description: >-
  Generate, measure and CI-gate Android Baseline Profiles so startup and first-scroll run AOT
  compiled instead of interpreted. Use when reducing cold start time, fixing first-run jank,
  adding a baseline profile module, wiring macrobenchmark, or verifying that a profile is
  actually shipped in the APK/AAB.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - skydoves/compose-performance-skills (measurement/generating-baseline-profiles)
    - chrisbanes/skills (android-benchmark-comparison)
    - agent-skills-standard (android-performance)
---

# Baseline Profiles

A baseline profile converts startup and first-interaction hot code into compiled code at install
time. Without one, a Compose app spends its first ~10 seconds in the interpreter.

The decision this skill makes: **which journeys get profiled, and how do you prove the shipped
artifact contains the profile?**

## Use when

- Cold start is above target, or the first scroll after install janks and later scrolls do not.
- Setting up `:baselineprofile` module + `:macrobenchmark` module.
- A profile exists but `ProfileInstaller` reports nothing installed.
- CI must fail when the profile is missing from the release build.

## Do not use when

- The jank persists on warm start too → `recomposition` / `lazy-layouts` (the profile is not the cause).
- Startup cost is in `Application.onCreate` initialisers (library init, DI graph) → `startup-and-perfetto`.
- The build is failing for other reasons → `bug-fix`.

## Rules

1. **Profile only journeys a user actually repeats at startup.** Cold start to first frame,
   plus at most 2–3 critical entrances (deep link into main screen, open editor). Profiling the
   whole app inflates the profile and dilutes the benefit.
2. **`startup-profiling` variant is the only source of truth.** `BaselineProfileRule` must run
   against a non-debuggable, `profileable` build. Debug builds measure nothing.
3. **One generator, one journey list.** Keep the `@Test` methods semantic
   (`coldStartToFeed`, `deepLinkToDetail`) — each must be a real user path with `pressHome()`
   resets and `startActivityAndWait()`.
4. **The generated `baseline-prof.txt` is committed** only if the human-owned rules are merged
   with it; otherwise it is regenerated in CI and stored as an artefact. Never mix: choose one
   policy and write it in the repo README.
5. **Verify the profile ships.** Check the merged release output, not the source tree:
   `unzip -p app-release.aab base/profinstall.*` or
   `unzip -l app-release.apk | grep -i baseline`.
6. **Measure with Macrobenchmark, not with a stopwatch.** Use `StartupTimingMetric` with
   ≥10 iterations, `CompilationMode.Partial` (BASELINE_PROFILE) vs `None`, and report the median
   plus the improvement, not a single run.
7. **Never verify on an emulator.** Thermal state, CPU and I/O make emulator startup numbers
   meaningless. Physical device only, and record the model + API level with the result.
8. **Re-generate when the startup graph changes materially** — new DI root, new first screen,
   significant Compose version change. A stale profile is worse than none: it compiles dead code
   and skips new hot code.
9. **Do not hand-write rules to "help".** Human-written rules for Compose UI classes go stale
   fast and can hurt startup by over-compiling. Only add them for a proven-in-trace miss.

## Procedure

1. Create the modules (ids from the catalog, no literal versions):
   ```kotlin
   // :baselineprofile/build.gradle.kts
   plugins { alias(libs.plugins.android.test); alias(libs.plugins.baselineprofile) }
   android { targetProjectPath = ":app"; experimentalProperties["android.experimental.self-instrumenting"] = true }
   ```
2. Write journeys:
   ```kotlin
   @Test fun coldStartToFeed() = baselineProfileRule.collect(packageName = "com.example.app") {
       pressHome(); startActivityAndWait(); device.waitForIdle()
   }
   ```
3. Generate: `./gradlew :app:generateBaselineProfile`
4. Run macrobenchmark comparison (BASELINE_PROFILE vs NONE), 10 iterations.
5. Confirm the profile is in the release artefact (rule 5).
6. Add the CI job that regenerates/validates.

## Checklist

- [ ] `:baselineprofile` uses an `android.test` + `baselineprofile` plugin, version from catalog.
- [ ] Journeys are named user paths; each resets with `pressHome()`.
- [ ] Generator ran on a physical device, `startup-profiling` variant.
- [ ] Startup comparison reported with median of ≥10 iterations and both compilation modes.
- [ ] Release artefact verified to contain the profile.
- [ ] Regeneration policy (commit vs CI artefact) documented in the repo.
- [ ] No hand-written rules unless justified by a trace.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| "Faster" claimed | one debug run, stopwatch | Macrobenchmark median, 10 runs, release-like build | debug builds are ~10x slower and noisy |
| Profile missing in APK | profile file exists in source | unzip the release artefact | packaging step silently skips it |
| Emulator benchmarks | emulator on a laptop | physical device | meaningless thermal/CPU profile |
| Profile everything | `collect` with no journeys → whole app | 2–4 startup journeys | dilutes compilation budget |
| Stale profile | generated once, never again | regenerate on graph change | compiles dead code |
| Hand-tuned rules | manual Compose class list | only after trace shows a miss | over-compiles, hurts startup |

## Verify

```bash
./gradlew :app:generateBaselineProfile
./gradlew :macrobenchmark:connectedCheck -Pandroid.testInstrumentationRunnerArguments.androidx.benchmark.suppressErrors=EMULATOR
unzip -l app/build/outputs/apk/release/app-release.apk | grep -iE 'baseline|profinstall'
```

Expected: profile listed in the APK/AAB, and macrobenchmark output shows
`compilationMode=BASELINE_PROFILE` startup median below the `NONE` median, with the improvement
recorded next to the device model.

## References

- `androidx.benchmark:benchmark-macro-junit4` — `StartupTimingMetric`, `CompilationMode`
- `androidx.profileinstaller:profileinstaller` — must be a runtime dependency of `:app`
