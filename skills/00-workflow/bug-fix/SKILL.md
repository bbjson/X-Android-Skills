---
name: bug-fix
description: >-
  Diagnose and fix a defect in an Android app in a fixed evidence-first order, without
  rewriting surrounding code. Use when a crash, ANR, wrong state, or visual defect is
  reported, when a Logcat/Perfetto trace must be interpreted, or when you are asked to
  "just make this work" on broken behaviour.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering/workflows/bug-fix
    - mobile-agent-skillpack/android-logcat-root-cause
    - kotlin-footguns/engineering-method-footguns
    - android-skill/fix-build
---

# Bug Fix

One rule above all: **the fix must be explained by evidence you obtained, not by a hypothesis
you formed**. A patch that "seems to help" is a regression you have not noticed yet.

## Use when

- A crash, ANR, freeze, wrong value, lost state, or layout defect is reported.
- A Logcat, Perfetto, or Play Vitals trace must be turned into a root cause.
- A build/sync failure blocks work (`Unresolved reference`, KSP errors, dependency conflicts).
- A fix was attempted and the symptom persists.

## Do not use when

- Behaviour is not specified yet (the "bug" is a spec gap) → `requirements-grill`.
- The task is restructuring code with no behaviour change → `refactor`.
- Only tests are missing and behaviour is correct → `unit-testing` / `compose-ui-testing`.

## Rules

1. **Reproduce before reading code.** State the exact repro: device/API level, build variant,
   entry steps, expected vs actual. If you cannot reproduce, say so and ask for the missing
   artefact (log, screen recording, device model) — do not guess.
2. **Collect the primary artefact first.** Crash → full Logcat from the `FATAL EXCEPTION`
   block plus 40 lines above. ANR → `/data/anr/traces.txt` or `adb shell dumpsys activity anrs`.
   Jank → Perfetto trace, not a screenshot of a stutter.
3. **Read the first exception, not the last.** In a causal chain the earliest
   `Caused by:` is the root; later ones are fallout. Quote the exact first line in your notes.
4. **One discriminating experiment, then decide.** Between two candidate causes, design the
   cheapest observation that separates them (add one log, toggle one flag, run one release-mode
   build). Fix only after the experiment picks a side.
5. **Fix at the layer where the invariant broke.** If the UI receives `null` because the
   repository mapped a failed response to `null`, fix the mapper — not a `?: emptyList()`
   in the Composable.
6. **Never change more than the defect requires.** No reformatting, no renames, no "while I'm
   here" refactors in the same change. Follow-up refactors go to `refactor`.
7. **Add the failing test before the fix when the defect is unit-testable.** It must fail on
   the current code and pass after. For UI-only defects, add a screenshot case instead.
8. **Record the causal chain.** Final report has four lines: symptom → first exception/evidence →
   violated invariant → code change. A reader must be able to disagree with one line only.

## Procedure

1. Write the repro statement. If incomplete, stop and ask.
2. Capture the artefact:
   ```bash
   adb logcat -c && adb logcat -v time > /tmp/bug.log   # reproduce, then Ctrl-C
   adb shell dumpsys activity anrs                      # ANR only
   adb shell dumpsys meminfo <pkg>                      # OOM/leak only
   ```
3. Extract the first cause: `grep -n -m1 -A15 'FATAL EXCEPTION' /tmp/bug.log`, then walk
   `Caused by:` lines upward.
4. Map the exception to the violated invariant, and to the file that owns that invariant.
5. Run the discriminating experiment if two owners are plausible.
6. Write the failing test (JVM-level) or screenshot case (UI-level).
7. Apply the minimal fix, rerun the test, rerun the repro.
8. Re-read the diff and delete anything not required by rule 5.

## Checklist

- [ ] Repro steps written down and replayed after the fix.
- [ ] First `Caused by:` quoted, not paraphrased.
- [ ] Fix located in the layer that owns the broken invariant.
- [ ] Failing test added (or screenshot case) and it failed before the fix.
- [ ] Diff contains no unrelated formatting, rename, or cleanup.
- [ ] `./gradlew :app:assembleDebug` and the affected test task pass.
- [ ] Causal chain written in four lines in the change description.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| `null` reaches UI | `state ?: default` in Composable | fix the mapper that emitted `null` | hides the second occurrence |
| Crash in release only | lower `minifyEnabled` to false | read the R8 mapping, add the missing rule | disables the feature that found the bug |
| ANR on main thread | wrap in `runBlocking { withContext(IO) }` | move the blocking call out of the main thread entirely | still blocks the caller |
| Flaky test "fixed" | `Thread.sleep(2000)` | make the assertion wait on state, not time | trades failure for slowness |
| Symptom gone after edit | stop, ship | revert, apply rule 4, find the mechanism | coincidence is indistinguishable from fix |
| Build fails on KSP | add `kapt`, or disable the plugin | read the KSP error, fix the processor input | two compilers fight |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew test --tests '*<AffectedClass>*'
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Expected: the original repro no longer reproduces, and the new test fails when the fix is
reverted (verify once with `git stash`).

## References

- Logcat format and buffer ids: `adb logcat --help`
- ANR traces: `adb shell dumpsys activity anrs`
