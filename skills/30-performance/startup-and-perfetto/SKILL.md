---
name: startup-and-perfetto
description: >-
  Measure and reduce cold start with real traces: separate process creation, Application.onCreate,
  first Activity, and first frame; find main-thread I/O, eager initialisers and ContentProvider
  autostarts; verify with Macrobenchmark on physical devices. Use when cold start is too slow, the
  first frame is late, reportFullyDrawn is far from display time, or someone claims a startup win
  without a trace.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - agent-skills-standard (android-performance)
    - android-skill (profile-performance)
    - chrisbanes/skills (android-benchmark-comparison)
    - skydoves/compose-performance-skills (measurement/testing-compose-in-release-mode)
---

# Startup and Perfetto

Startup is a four-phase pipeline. Optimising without knowing which phase dominates is guessing with
extra steps.

```
T0 process fork → T1 Application.onCreate → T2 first Activity.onCreate → T3 first frame → T4 fully drawn
```

## Use when

- Cold start exceeds its budget, or `am start -W` TotalTime is high.
- `reportFullyDrawn` is much later than first frame.
- A library may be initialising itself at startup (ContentProvider trick).
- Verifying a startup optimisation claim with numbers.
- Choosing between lazy init, App Startup, or removing a dependency from the startup path.

## Do not use when

- The slowness appears after the first frame (scrolling, interactions) → `recomposition` / `lazy-layouts`.
- First-scroll-only jank after install → `baseline-profiles`.
- The app crashes at startup → `bug-fix`.

## Rules

1. **Measure the four phases separately, on a release-like build and a physical device.** Debug builds
   are ~2–10× slower and mislead about which phase dominates. Use `CompilationMode.None` vs
   `Partial`, and a non-debuggable build.
2. **`am start -W` gives TotalTime/WaitTime; it does not tell you why.** For the why, use a Perfetto
   trace with the app's process and the main thread visible. A number without a trace is not a
   diagnosis.
3. **The main thread does zero disk, network, or lock-waiting work before the first frame.** This is
   the single highest-value rule. `StrictMode` with `detectDiskReads`/`detectDiskWrites` on the main
   thread turns violations into visible log lines — enable it in internal builds and treat a
   violation as a defect.
4. **Every ContentProvider auto-initialiser is a startup cost you did not ask for.** Firebase,
   WorkManager, Play Core, analytics, crash SDKs all use this trick. Check the merged manifest:
   ```bash
   ./gradlew :app:processDebugManifest
   grep -c "<provider" app/build/intermediates/merged_manifests/debug/AndroidManifest.xml
   ```
   Replace with explicit lazy init or `androidx.startup` with a deliberate ordering.
5. **`Application.onCreate` does only what the first screen provably needs.** DI graph *creation* is
   usually cheap; eagerly constructing every singleton is not. Prefer lazy bindings (`@Lazy`,
   `Provider`) for anything not used on the first screen.
6. **`reportFullyDrawn()` marks the moment content is usable.** Call it when the first screen has real
   data, not when it is empty. Without it, "fully drawn" is invisible in `am start` output.
7. **Optimise the biggest phase first, then re-measure.** A 20 ms win in `Application.onCreate` does
   not matter when 800 ms is spent inflating the first screen.
8. **A startup win must hold on the slowest target device, not the fastest.** Thermal state and CPU
   class change the ranking of costs. Record device model + API level with every number.
9. **Never "optimise" by deferring work in a way that moves the cost to first interaction without
   measuring both.** Deferring is legitimate, moving the jank to the first scroll is not a fix.
10. **Keep the numbers in the repository.** A `startup.md` with device, build type, compilation mode,
    P50/P90 and the trace file makes regressions reviewable. Numbers in a chat message do not.

## Procedure

1. Get the baseline:
   ```bash
   adb shell am force-stop <pkg>
   adb shell am start -W -n <pkg>/.MainActivity     # 5 runs, record TotalTime
   adb shell dumpsys gfxinfo <pkg> framestats | head -30
   ```
2. Record a Perfetto trace around a cold start (or use Studio's System Trace):
   ```bash
   adb shell perfetto -o /data/misc/perfetto-traces/startup.pftrace -t 5s \
     sched freq idle am wm gfx view binder_driver hal dalvik
   adb pull /data/misc/perfetto-traces/startup.pftrace
   ```
3. Read the trace by phase: process fork → `Application.onCreate` → Activity `onCreate`/`onResume`
   → first `Choreographer#doFrame` → first draw. Attribute time to the phase, not to the app.
4. Rank costs; pick the top one. Then apply exactly one of: remove from startup path, make lazy,
   move off the main thread, precompute at build time.
5. Re-run steps 1–3 with the same device and build type. Keep the change only if the phase's time
   dropped and no other phase grew.
6. Add a Macrobenchmark `StartupTimingMetric` test so CI can watch it.

## Checklist

- [ ] Four phases identified in a trace, not just a total.
- [ ] Measured on a physical device, release-like, non-debuggable.
- [ ] `StrictMode` main-thread I/O violations are zero on the startup path.
- [ ] ContentProvider autostarts enumerated and justified or removed.
- [ ] `Application.onCreate` contains only first-screen needs.
- [ ] Lazy bindings for singletons not used by the first screen.
- [ ] `reportFullyDrawn()` called when the first screen has data.
- [ ] Before/after numbers recorded with device + build type.
- [ ] Macrobenchmark startup test added.
- [ ] No phase got worse.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Optimised the wrong thing | tune `onCreate` while inflation dominates | trace, attribute per phase | 80% elsewhere |
| Numbers from debug | `am start` on debug build | release-like, non-debuggable | debug is 2–10× slower |
| Invisible startup cost | "we don't init analytics" | check merged manifest providers | auto-init by SDK |
| Main-thread IO | read config in `onCreate` | async load + placeholder | blocks first frame |
| Empty first frame | `reportFullyDrawn` at `onCreate` | call when data renders | metric meaningless |
| Fastest device only | flagship numbers | slowest target device | real user experience |
| Moved the cost | defer heavy work to first scroll | measure both phases | jank moved, not removed |
| Lost numbers | chat message | `startup.md` + trace file | not reviewable |

## Verify

```bash
adb shell am force-stop <pkg>
for i in 1 2 3 4 5; do adb shell am start -W -n <pkg>/.MainActivity | grep TotalTime; done
adb shell app_process ... && adb shell dumpsys meminfo <pkg> | head
```

Expected: same device, same build type, TotalTime P50 improved versus the recorded baseline, with the
trace showing which phase shrank; `reportFullyDrawn` time moved closer to first frame.

## References

- Perfetto trace config: `sched freq am wm gfx view binder_driver dalvik`
- Macrobenchmark `StartupTimingMetric`, `CompilationMode.Partial/None`
- `androidx.startup` for explicit initialiser ordering
