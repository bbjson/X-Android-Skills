---
name: benchmark-testing
description: >-
  Measure Android performance claims with benchmarks that survive scrutiny: Macrobenchmark for
  startup and jank, Microbenchmark for hot code, physical devices, compilation modes, iteration counts
  and median/P90 reporting. Use when proving a performance change, adding a performance gate to CI,
  comparing two implementations, or reproducing a "it feels faster now" claim.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - chrisbanes/skills (android-benchmark-comparison)
    - skydoves/compose-performance-skills (measurement/testing-compose-in-release-mode)
    - agent-skills-standard (android-performance)
    - awesome-android-agent-skills (compose-performance-audit)
---

# Benchmark Testing

A benchmark produces a **number with an error bar and a device**. Everything else — "it feels
faster" — is not a measurement.

## Use when

- Proving a performance change (before/after) for a PR or a review.
- Adding a performance gate to CI (startup time, frame timing).
- Comparing two implementations (Compose vs View, two algorithms).
- Validating a Baseline Profile's effect.
- Someone quotes a single stopwatch reading.

## Do not use when

- You do not yet know *what* is slow → `startup-and-perfetto` / `recomposition` first.
- The claim is correctness → `unit-testing`.
- The measurement is of the build, not the app → `build-performance`.
- APK/AAB size as the metric → `app-size`.
- Native hot paths and JNI overhead → `ndk-jni`.

## Rules

1. **Macro vs micro by claim:** a user-visible claim (startup, scroll, navigation) → Macrobenchmark.
   A hot function or algorithm → Microbenchmark (JVM, no device). Using micro to prove a UX claim is
   the most common misuse.
2. **Physical device only for macro benchmarks.** Emulators have no meaningful thermal or CPU
   profile; `suppressErrors=EMULATOR` exists because emulator numbers are invalid, not because they
   are convenient.
3. **Iterate at least 10 times and report median plus P90 (or P95).** One run measures the device's
   mood. Macrobenchmark defaults to 5 iterations with 1 warmup — raise it for comparisons.
4. **Always compare compilation modes.** For startup/scroll, run `CompilationMode.None` and
   `CompilationMode.Partial` (baseline profile) — a "win" that only exists in one mode is a profile
   artefact.
5. **Use a release-like, non-debuggable build.** `debuggable=true` disables the optimisations being
   measured; a benchmark on a debug build measures debug.
6. **Warm the device and control the environment:** screen on, airplane mode where possible, fixed
   brightness, no other apps, same thermal state, unplugged. Record the device model, API level and
   build variant with the numbers.
7. **Never compare across devices or across days without a control run.** Run both variants on the
   same device in the same session; if separated, re-measure the baseline.
8. **Report the metric's own definition.** `StartupTimingMetric` timeToInitialDisplay vs
   timeToFullDisplay differ; `FrameTimingMetric` frameDurationCpuMs vs frameOverrunMs differ. Name the
   metric, not "startup time".
9. **A benchmark is a test, so it must fail.** Set an absolute or relative threshold in CI; a
   benchmark that only prints numbers regresses silently.
10. **Keep benchmark code out of the app's test task.** A separate `:benchmark` module with
    `benchmark` build type; otherwise every CI run pays for it.
11. **One variable per comparison.** Changing the code *and* the Compose version *and* the device
    state produces a number that cannot be attributed.

## Procedure

1. State the claim: "cold start to first frame improves by ≥10% on Pixel 6, API 34, partial
   compilation".
2. Create the module: `:benchmark` with `android.test` plugin + macrobenchmark dependency, targeting
   the app's `benchmark` build type.
3. Write the benchmark with a fixed iteration count and both compilation modes.
4. Run the baseline (unchanged code), record median/P90.
5. Apply the single change; run again in the same session on the same device.
6. Report a table: metric, compilation mode, median, P90, device, build type.
7. Add a threshold assertion if the metric must not regress.

## Checklist

- [ ] Macro for user-visible claims; micro for hot code.
- [ ] Physical device, release-like non-debuggable build.
- [ ] ≥10 iterations; median and P90 reported.
- [ ] Both `CompilationMode.None` and `Partial` measured for startup/scroll.
- [ ] Environment controlled (airplane, brightness, no background apps) and recorded.
- [ ] Baseline and change measured in the same session on the same device.
- [ ] Metric named precisely (initial vs full display; cpu vs overrun).
- [ ] One variable changed per comparison.
- [ ] Threshold assertion in CI (not just printed numbers).
- [ ] Benchmark module separate from the app test task.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Emulator numbers | emulator, 3 runs | physical device, 10+ | meaningless profile |
| Debug build measured | `assembleDebug` | release-like `benchmark` variant | optimisations off |
| One run | single stopwatch | median + P90 over 10+ | noise |
| Cross-day comparison | yesterday's baseline | same-session control run | thermal drift |
| Ambiguous metric | "startup 800ms" | `timeToInitialDisplay` median | different metrics |
| Silent regression | prints numbers | threshold assertion | nobody watches |
| Multi-variable | new lib + new device | one change | unattributable |

## Verify

```bash
./gradlew :benchmark:connectedBenchmarkAndroidTest -Pandroid.testInstrumentationRunnerArguments.androidx.benchmark.suppressErrors=EMULATOR,DEBUGGABLE
```

Expected: a table of median/P90 per compilation mode on a named physical device, with the baseline and
the change measured in the same session, and CI failing when the threshold is exceeded.

## References

- `androidx.benchmark:benchmark-macro-junit4` — `StartupTimingMetric`, `FrameTimingMetric`,
  `CompilationMode.Partial`
- `androidx.benchmark:benchmark-junit4` — microbenchmark on JVM
