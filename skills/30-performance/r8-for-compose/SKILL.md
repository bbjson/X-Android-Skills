---
name: r8-for-compose
description: >-
  Shrink and obfuscate a release build without breaking serialization, reflection, WebView bridges
  or DI, and keep the mapping so crash reports stay readable. Use when enabling minification,
  debugging a crash that only happens in release, when Gson/kotlinx fields arrive null after
  obfuscation, when a class is missing at runtime, or when resource shrinking removes a
  dynamically-referenced resource.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - skydoves/compose-performance-skills (build/configuring-r8-for-compose)
    - android-skill (release-check)
    - agent-skills-standard (android-deployment)
    - mobile-agent-skillpack (android-release-checklist)
---

# R8 for Compose

R8 is not an optional optimisation pass: it is the step that makes release builds faster, smaller
and **different** from debug. Everything that works by naming — serialization, reflection, JSON,
JS bridges — is at risk.

## Use when

- Enabling `minifyEnabled` / `shrinkResources` for the first time, or after a long gap.
- A crash happens only in release (`ClassNotFoundException`, `NoSuchMethodException`, `NPE` on a
  field, empty enum, null DTO field).
- A dynamically-referenced resource or class is missing in release.
- Setting up mapping handling and deobfuscation for crash reporting.
- Deciding whether a `-keep` rule is needed or is masking a design problem.

## Do not use when

- The release problem is signing/tracks → `release-flow`.
- The problem is an obfuscated *stack trace* only → still this skill (mapping), but the fix may be
  `bug-fix`.
- The build fails to compile before minification → `bug-fix` / `agp9-migration`.

## Rules

1. **Minification is enabled for release and verified by an actual release run.** A release build
   that has never been installed is not a verified configuration. `assembleRelease` green is not
   enough; exercise the app's serialization paths on a device.
2. **Kotlin serialization: keep the generated serializers, not the DTO classes.** The compiler plugin
   generates `$serializer` companions; R8 needs to keep them reachable. If using Gson/Moshi with
   field-name reflection, annotate every field (`@SerializedName`) *or* keep the class — annotation is
   better because it survives renaming without a broad keep.
3. **Every interface implemented by a DI framework must be kept** (Hilt/Dagger generated code,
   Koin's reflective lookup if used). Hilt ships its own consumer rules — do not duplicate them; do
   add rules only for your own reflective lookups.
4. **`@JavascriptInterface` methods must be kept with their names.** Add a targeted
   `-keepclassmembers` for the bridge class; a renamed JS method is a silent `undefined` in the page.
5. **`Class.forName` / `getIdentifier` / resource-name lookups are invisible to R8.** Replace with
   direct references where possible. If unavoidable, keep the targets explicitly and use
   `shrinkResources`-safe names — a shrunk resource referenced by name is a `Resources$NotFoundException`.
6. **`-dontobfuscate` / `-ignorewarnings` are not fixes.** The first removes the size benefit and
   hides rename bugs; the second hides missing-class bugs until runtime. Both are deferral, not
   mitigation.
7. **Keep `mapping.txt` from every release, and deobfuscate crashes with it.**
   `./gradlew :app:assembleRelease` → `app/build/outputs/mapping/release/mapping.txt`. Upload it with
   the release; a stack trace without the mapping is unreadable and unreproducible.
8. **Never `-keep class ** { *; }` to silence a problem.** Keep the narrowest member. Broad keeps
   disable shrinking exactly where it matters and grow the APK.
9. **R8 full mode changes reflection behaviour.** If a library relies on reflection, check its
   consumer rules for the AGP version in use rather than adding your own `-keep`.
10. **Order matters with Baseline Profiles: generate the profile against the R8-processed,
    non-debuggable build.** Profiling a debug build records the wrong method shapes, and the profile
    then misses the real hot methods (see `baseline-profiles`).
11. **Verify the release APK, not the debug APK, for: startup, first list scroll, one serialization
    round trip, one WebView page, one DI-heavy screen.** Five checks catch almost all R8 breakage.

## Procedure

1. Enable in the release build type: `isMinifyEnabled = true`, `isShrinkResources = true`,
   and the default/optimised proguard file set.
2. Grep the risk surface:
   ```bash
   grep -rn "SerializedName\|@Serializable\|JavascriptInterface\|Class.forName\|getIdentifier" --include=*.kt .
   ```
3. Add narrow rules for the gaps (rules 2–5); confirm no duplicate of library-provided rules.
4. Build release, install, and run the five checks (rule 11).
5. Save `mapping.txt` and confirm the crash pipeline can deobfuscate one known trace.

## Checklist

- [ ] `minifyEnabled` + `shrinkResources` enabled for release.
- [ ] Serialization fields annotated or narrowly kept (no broad class keep).
- [ ] `@JavascriptInterface` members kept by name.
- [ ] No `Class.forName`/`getIdentifier` without explicit keep.
- [ ] No `-dontobfuscate` / `-ignorewarnings` added as a workaround.
- [ ] `mapping.txt` archived per release; deobfuscation verified.
- [ ] No `-keep class ** { *; }`.
- [ ] Release APK exercised: startup, list scroll, serialization round trip, WebView, DI screen.
- [ ] Baseline profile generated against the R8 build.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Null DTO fields in release | broad `-keep class **` | `@SerializedName` per field | keep disables shrinking everywhere |
| Missing class at runtime | `-ignorewarnings` | add the narrow keep / fix the lookup | warning was the bug |
| Unreadable crash | no mapping saved | archive `mapping.txt`, retrace | no names to debug |
| Bridge returns undefined | renamed JS interface method | `-keepclassmembers` with names | JS calls by string |
| Resource missing | `getIdentifier("ic_x", …)` shrunk | direct `R.drawable` reference | R8 cannot see strings |
| Slower release | `-dontobfuscate` | narrow keeps | size and load time up |
| Profile misses hot code | profile generated on debug | profile on R8 non-debuggable | method shapes differ |

## Verify

```bash
./gradlew :app:assembleRelease
ls -l app/build/outputs/mapping/release/mapping.txt
adb install -r app/build/outputs/apk/release/app-release.apk
adb logcat -c && adb shell am start -n <pkg>/.MainActivity
adb shell dumpsys gfxinfo <pkg> framestats | head -20
# retrace one known stack trace
retrace app/build/outputs/mapping/release/mapping.txt crash.txt
```

Expected: release APK launches, loads a list, deserializes real data, and a deliberately-failed
trace resolves to original class/method names through `retrace`.

## References

- `mapping.txt`, `retrace`, `-keepclassmembers`, `-if`/`-keep` conditional rules
- Library consumer rules: `META-INF/proguard/*` inside AARs
