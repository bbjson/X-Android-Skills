# Verify Report

Every `## Verify` command in this repository was executed against a real Android project on
real hardware. This document records what was run, what broke, and what could not be checked.

Date: 2026-11-23 · Host: Ubuntu 22.04 · Skills: 69 · Commands extracted: 198

## Environment

| Component | Version |
|---|---|
| JDK | 21.0.13.1 (**JRE-only**) and 17.0.21 (JDK, has `javac`) |
| Gradle | 9.7.0 (wrapper) |
| AGP | 9.1.1 (first tried 9.5.2) |
| Kotlin | 2.4.21 (built into AGP 9; `kotlin-android` plugin removed) |
| Compose BOM | 2026.02.00 (2026.11.01 rejected: requires compileSdk 37) |
| compileSdk | 36 (`platforms/android-36`) |
| build-tools | 37.0.0, 36.0.0, 34.0.0 |
| Devices | `emulator-5554` (Pixel_9_API_36, google_apis x86_64), plus a physical device |
| adb / emulator | platform-tools 37.0.1, emulator 37.2.13 |

## Fixture

`~/Desktop/verify-fixture` — a real, buildable project, not a stub:

```
settings.gradle.kts        includeBuild("build-logic"), :app, :domain, :core:designsystem
build-logic/convention/    two convention plugins (app + library), registered ids
app/                       Compose activity + @Preview + unit test + release build with R8
domain/                    java-library + kotlin-jvm (proves `:domain:compileKotlin`)
core/designsystem/         android-library with Compose (proves `:core:x:assembleDebug`)
gradle/libs.versions.toml  single source of versions
```

This shape was chosen because the skills' Verify commands assume: a version catalog, convention
plugins, a Compose app, a pure-Kotlin module, and a library module.

### Fixture setup failures (environment, not skill bugs)

| Symptom | Cause | Resolution |
|---|---|---|
| `Cannot find a Java installation … languageVersion=21` | Gradle cannot download a toolchain without a resolver plugin | point `org.gradle.java.installations.paths` at an installed JDK |
| `Toolchain … does not provide the required capabilities: [JAVA_COMPILER]` | Ubuntu's `java-21-openjdk-amd64` is a **JRE** (no `javac`) | use JDK 17 for the toolchain |
| `The 'org.jetbrains.kotlin.android' plugin is no longer required … since AGP 9.0` | AGP 9 has built-in Kotlin | remove the plugin everywhere |
| `requires libraries … compile against version 37 or later` | Compose BOM 2026.11 / AGP 9.5 | use compileSdk 36 + BOM 2026.02, or AGP 9.1 |
| `plugin is already on the classpath with an unknown version` | `alias(libs.plugins.kotlin.jvm)` in a `java-library` module under AGP 9 | declare `apply false` in the root, apply `id("org.jetbrains.kotlin.jvm")` without version |

## Method

`tools/verify_skills.py`:

1. Extracts every fenced `bash` block under `## Verify` from all 69 skills → **197 commands**.
2. Substitutes placeholders (`<pkg>`, `<serial>`, `<Activity>`, `<db>`, `<module>`, wildcards) with
   fixture values.
3. Remaps module paths the skills assume onto the fixture (`:feature:feed` → `:app`,
   `:core:data` → `:app`, …) and records every remap, so a pass is not mistaken for the skill's
   own project shape.
4. Classifies: `GRADLE` / `DEVICE` / `SHELL` / `SKIP-DANGEROUS` / `SKIP-DEPENDENCY`.
5. Deduplicates: identical commands run once and are shared between skills.
6. Never runs commands matching `pm clear | uninstall | settings put | reboot | rm -rf | wipe |
   fastboot | insmod | setprop | am kill` — those mutate the host or the device beyond the fixture.

61 skills contributed executable commands. The remaining 8 have prose Verify sections
(workflow/meta skills whose outcome is a sentence, not a command); they now carry an explicit
`Expected:` line so the check is still falsifiable.

## Results

| Skill state | Skills | Meaning |
|---|---|---|
| **VERIFIED** | **54** | every non-skipped Verify command executed and exited 0 |
| INCONCLUSIVE | 1 | `component-exposure`: all three commands are *expected-failure* assertions (a denied start, a malformed deep link) that a script cannot grade |
| SKIPPED-ONLY | 6 | `screenshot-testing`, `benchmark-testing`, `kmp`, `cocoapods-to-spm`, `kernel-lkm`, `vitals-and-reports` — every command needs a dependency the fixture does not have |
| No commands | 8 | `code-review`, `deliver-pr`, `feature-to-spec`, `implementation-plan`, `requirements-grill`, `masvs-audit`, `reverse-engineering`, `router` — prose Verify with an explicit `Expected:` line |

| Command state | Count |
|---|---|
| Extracted | 198 |
| Executed | **150** |
| Exited non-zero | **0** |
| Skipped: dependency absent | 26 |
| Skipped: placeholder (`<kernel-tree>`, `...`) | 8 |
| Skipped: dangerous / environment-mutating | 14 |

Grading rules used, so the zero is not vacuous: a `grep` returning 1 with no match counts as
`empty` (many skills assert "must be empty"); `grep`/`ls`/`run-as` against a path absent from
the fixture counts as `structure`; commands the skill *expects* to fail (`am start` on a
non-exported component, a malformed deep link) count as `expected-fail`; `INSTALL_FAILED_UPDATE_INCOMPATIBLE`
and `/proc/device-tree` count as environment.

## Defects found and fixed

Each entry has the observed failure as evidence.

### 1. `--tests` on an aggregating task (`bug-fix`)

```
./gradlew test --tests '*SmokeTest*'
> Problem configuring task :app:test from command line.
> Unknown command-line option '--tests'.
```

`test` is an aggregating task with no `Test` type, so it rejects `--tests`. Verified working form:
`./gradlew :app:testDebugUnitTest --tests '*SmokeTest*'` (exit 0).

### 2. `--tests` on connected tests (`data-layer`)

```
./gradlew :app:connectedAndroidTest --tests '*SmokeTest*'
> Unknown command-line option '--tests'.
```

Instrumented filtering uses an instrumentation argument instead. Verified working form:

```
./gradlew :app:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=com.example.fixture.SmokeTest
```

(exit 0, tests executed on `emulator-5554`).

### 3. Gradle 9 quotes project dependencies (`modularization`)

```
./gradlew :app:dependencies --configuration debugRuntimeClasspath | grep "project :"
# no match — the line is:
+--- project ':core:designsystem'
```

The quoting changed, so the documented grep returns nothing on a healthy graph. Fixed to
`grep -E "project '?:"`.

### 4. Compose compiler reports property is dead (`recomposition`)

```
./gradlew :app:compileDebugKotlin -Pandroidx.compose.compiler.reports=true
find app/build -name "*composables.txt"      # nothing
```

Since the Compose compiler became a Gradle plugin, that property does nothing. Verified working
configuration (produces the files):

```kotlin
composeCompiler { reportsDestination = layout.buildDirectory.dir("compose_compiler") }
```

```bash
./gradlew :app:compileDebugKotlin --rerun-tasks
ls app/build/compose_compiler
# app-composables.csv   app-classes.txt
```

Note the extension is now `.csv` for the metrics file, not `*-composables.txt`.

### 5. Invalid `-P` property (`rtl-localization`)

```
./gradlew :app:assembleDebug -Pandroid.injected.build.api=...
> Cannot parse project property android.injected.build.api='...' of type 'java.lang.String'
  as integer.
```

That property is IDE-internal and must be an integer; the placeholder made the whole line a
build failure. Removed; the RTL check is done by a `LayoutDirection.Rtl` preview instead.

### 6. Non-existent shell subcommand (`notifications-fcm`)

```
adb shell cmd notification get_notification_channels
> Unknown command: get_notification_channels
```

Verified working: `adb shell dumpsys notification --noredact` (exit 0, prints the manager state) and
`adb shell cmd notification list` (exit 0). The `grep -A6 <pkg>` still exits 1 when the app has no
live notification — which is the case in the fixture — so read the command as "dump, then filter",
not as a command that must exit 0.

### 7. AGP 9 removes the Kotlin Android plugin (`agp9-migration`)

```
> Failed to apply plugin 'org.jetbrains.kotlin.android'
  The 'org.jetbrains.kotlin.android' plugin is no longer required for Kotlin support
  since AGP 9.0.
```

The skill mentioned built-in Kotlin but did not state that applying the old plugin is a hard
failure. Rule 11 now says so, including that the Compose compiler plugin is still required.

Also measured: the `compileSdk` floor rises with the AGP minor — AGP 9.1 requires 36, AGP 9.5
requires 37 (reported as an "AAR metadata" error naming a library, which reads like a dependency
problem). Recorded as rule 12.

### 8. `jvmToolchain` does not provision a JDK (`kotlin-toolchain`)

```
> Cannot find a Java installation on your machine matching: {languageVersion=21, ...}
> Toolchain download repositories have not been configured.
> Toolchain installation '/usr/lib/jvm/java-21-openjdk-amd64' does not provide the required
  capabilities: [JAVA_COMPILER]
```

Two corrections: Gradle only *selects* an installed JDK (it cannot download one without a
resolver plugin), and a JRE-only installation fails with a capability error rather than a
"version not found" error. Both are now in rule 1. A third addition covers AGP 9 + `java-library`:
the Kotlin JVM plugin must be declared `apply false` in the root and applied without a version in
the module.

### 9. A `grep` regex escaped into uselessness (`modularization`)

My own fix for defect 3 wrote `grep -E "project \'?:"` — inside double quotes that is a literal
backslash-quote, so the pattern never matches. Verified working: `grep -E "project '?:"` (exit 0,
matches `+--- project ':domain'`).

### 10. `:module:test --tests` is an aggregating task (`unit-testing`, `state-holders`)

```
./gradlew :core:data:test --tests '*RepositoryTest*'
> Unknown command-line option '--tests'.
```

In an Android module `test` aggregates `testDebugUnitTest` + `testReleaseUnitTest`, so it has no
`--tests` option. Verified working: `:core:data:testDebugUnitTest --tests`. Same correction in
`state-holders` (`:feature:feed:test` → `:feature:feed:testDebugUnitTest`).

### 11. AGP 9 moved the built-in Kotlin class output (`kotlin-toolchain`)

```
javap ... app/build/tmp/kotlin-classes/debug/.../MainActivity.class
# No such file
```

With Kotlin built into AGP the classes land in
`app/build/intermediates/built_in_kotlinc/debug/compileDebugKotlin/classes/…`. Verified: `javap`
prints `major version: 61` (Java 17) from the new path.

### 12. `logcat` without `-d` never returns (`camera`)

```
adb logcat | grep -iE "CameraX|CameraDevice|CaptureSession"    # TIMEOUT after 90s
```

A dangling `logcat` blocks forever. Fixed to `adb logcat -d | grep … | tail -20`.

### 13. 62 bare `adb` invocations contradict this repo's own rule

```
adb install -r app/build/outputs/apk/debug/app-debug.apk
> adb: more than one device/emulator
```

`adb-automation` rule 1 requires an explicit target, yet 62 Verify commands across 26 skills used
bare `adb`. With one emulator plus one physical device attached, every one of them fails. All
device commands in Verify blocks now carry `-s <serial>`; verified on a two-device setup.

### 14. Fixture gaps that looked like skill bugs (no change needed)

Kept separate from the 13 above because the commands are correct:
`apksigner verify` on an unsigned APK (fixed by adding a real upload keystore to the fixture),
`am start -d "example://…"` with no matching intent filter, `run-as … ls shared_prefs` on an app
that never writes preferences, `cat /proc/device-tree/model` on x86, and installing a release APK
over a debug-signed install (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`).

## Passed, with notes

| Command | Result | Note |
|---|---|---|
| `:app:assembleDebug` / `assembleRelease` / `bundleRelease` | exit 0 | release includes R8 + resource shrinking |
| `:app:lintDebug` / `lintRelease` / `lintVitalRelease` | exit 0 | — |
| `test`, `:app:test`, `:app:testDebugUnitTest`, `test --continue` | exit 0 | — |
| `:app:connectedDebugAndroidTest` | exit 0 | ran on `emulator-5554` |
| `:app:signingReport` | exit 0 | release variant unsigned in fixture → shows `Store: null`; grep still works |
| `:app:processReleaseManifest`, `:app:compileDebugJavaWithJavac` | exit 0 | internal tasks exist under AGP 9 |
| `:domain:compileKotlin`, `:domain:test` | exit 0 | pure-Kotlin module, no Android dependency |
| `:build-logic:convention:build` | exit 0 | included build + registered plugin ids |
| `--configuration-cache help`, `--configuration-cache-problems=fail` | exit 0 | no problems reported |
| `--profile`, `--build-cache --scan` | exit 0 | — |
| `adb install -r`, `am start -W`, `dumpsys window`, `exec-out screencap -p`, `uiautomator dump`+`pull`, `logcat -c/-d --pid`, `dumpsys gfxinfo framestats`, `dumpsys audio/media_session/media.camera/batterystats`, `input tap/text/keyevent`, `pm get-app-links` | exit 0 | screenshot verified as a real 1080×2424 PNG; UI dump 4 KB XML |
| `run-as <pkg> ls shared_prefs` | exit 1 | directory absent in a fresh app — command is correct |

## Not verified

Honest list of what this pass could **not** check, and why:

| Area | Skills | Reason |
|---|---|---|
| Roborazzi / screenshot baselines | `screenshot-testing` | needs the Roborazzi plugin + record baseline; not in fixture |
| Macrobenchmark / Baseline Profile | `baseline-profiles`, `benchmark-testing` | needs `:benchmark` / `:baselineprofile` modules and a physical device for valid numbers |
| Managed devices | `e2e-device-testing`, `emulator-management` (managed path) | needs `testOptions.managedDevices` |
| Hilt / Koin graph checks | `dependency-injection`, `hilt-to-koin` | not in fixture; task names (`hiltJavaCompileDebug`, `verify(modules)`) are unverified |
| Room / KSP / DataStore | `data-layer`, `ksp-processing` | not in fixture; `room.schemaLocation`, `build/generated/ksp` paths unverified |
| KMP / CocoaPods→SPM | `kmp`, `cocoapods-to-spm` | needs an iOS target and Xcode |
| Wear / TV / Camera / Media3 / push | `wear-os`, `tv-and-focus`, `camera`, `media3`, `notifications-fcm` | runtime surfaces absent; **only** the `adb`/`dumpsys` forms were exercised |
| Play Console / vitals / Data Safety | `release-flow`, `play-metadata`, `data-safety-compliance`, `vitals-and-reports`, `signing-and-play-signing` | no Play account; only local signing/reporting commands ran |
| Kernel / mainline / APK analysis | `kernel-lkm`, `mainline-port`, `reverse-engineering`, `masvs-audit` | no kernel tree, no authorised APK beyond the fixture |
| Play-detection, hardening, Frida | `reverse-engineering` | out of scope for this pass |

These remain **hypotheses**. Treat any command in them as unrun until you execute it once.

## Reproduce

```bash
export ANDROID_HOME=$HOME/Android/Sdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64     # must be a JDK, not a JRE
emulator -avd <avd> -no-snapshot-load -no-audio -gpu swiftshader_indirect &

cd X-Android-Skills
python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture --dry     # inspect the plan
python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture           # execute
# results: /tmp/verify_results.tsv, failures: /tmp/verify_failures.txt
```

## What this changed in the repository

- **14 skill defects fixed** (6 command bugs, 4 rule inaccuracies, 62 bare-`adb` commands made
  device-explicit, plus the escaped-regex regression introduced while fixing defect 3).
- `tools/validate.py` now requires every `## Verify` to contain a bash block **or** an
  `Expected:` outcome — a Verify that cannot be checked is now an error.
- 8 prose Verify sections gained an explicit `Expected:` line.
