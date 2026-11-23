---
name: agp9-migration
description: >-
  Move an Android project from Android Gradle Plugin 8.x to the 9.x line in a verified sequence,
  removing APIs that 9.x deleted instead of silencing them. Use when upgrading AGP, when a build
  breaks after an AGP bump with "unresolved reference" in build scripts or a removed variant API,
  when preparing for built-in Kotlin support, or when deciding whether to migrate now.
license: Apache-2.0
metadata:
  domain: build
  level: migration
  sources:
    - kotlin-agent-skills (kotlin-tooling-agp9-migration)
    - android-skill (fix-build)
    - awesome-android-agent-skills (android-gradle-logic)
    - claude-android-ninja
---

# AGP 9 Migration

This skill is the one place in this repository allowed to name versions: **from** 8.x, **to**
9.x. Everything else follows `version-catalog`.

The failure mode of an AGP upgrade is not "the build is red" — it is "the build is green because
someone deleted the check". A migration is complete only when every removed API has been
*replaced*, not when the warnings stopped.

## Use when

- Bumping AGP across the 8 → 9 boundary.
- A build script uses `applicationVariants` / `libraryVariants` / `variantFilter` and the build
  no longer compiles after the bump.
- Warnings mention deprecated or removed APIs in `build.gradle.kts`.
- Preparing for the newer built-in Kotlin / KMP build path.
- Deciding whether to migrate now or pin the current AGP.

## Do not use when

- The breakage is in Kotlin/Compose versions, not AGP → `version-catalog` + `kotlin-toolchain`.
- The breakage is annotation processing (kapt/KSP) → `ksp-processing`.
- The breakage is dependency resolution → `bug-fix`.

## Rules

1. **Climb the ladder in this order, one commit each:** Gradle wrapper → AGP → Kotlin/Compose
   compiler → KSP → libraries. Skipping a rung makes the failure ambiguous.
2. **Read the removal list before touching code.** For every deprecated API you use, the output
   must be a replacement, not a suppression. `@Suppress("DEPRECATION")` on a build script is a
   deferred outage.
3. **Removed variant API → `androidComponents`.** `applicationVariants`, `libraryVariants`,
   `variantFilter`, `variant.outputs` are gone. The replacement is
   `androidComponents.onVariants { variant -> … }` with `Variant`/`VariantOutput` accessors. Do not
   keep the old blocks behind a flag.
4. **`buildConfig` is a feature flag.** If production code reads `BuildConfig`, the module must
   enable the `buildFeatures.buildConfig` flag explicitly. Missing it is a compile error that
   looks like a missing class.
5. **`namespace` is mandatory; nothing may rely on the manifest `package` attribute.** Grep all
   modules first (rule 2 of `modularization`: one place per concern).
6. **`lint`/`packaging` blocks replace their pluralised, `Options`-suffixed predecessors**
   (`lintOptions`, `packagingOptions`, `adbOptions`, `aaptOptions`). Rename them as part of the
   bump, do not leave both.
7. **kapt must be gone before you finish.** If kapt has to stay, document the module and the
   reason; AGP 9-era builds treat kapt as a compatibility path with real build-time cost.
8. **R8/AGP behaviour changes must be checked against a release build, not a debug build.** Rules
   that silently stop applying (missing `-keep`, changed default) only manifest in `release`.
9. **Keep every module's `compileSdk` in one place (convention plugin) and raise it before the
   bump** — an AGP bump that also raises `compileSdk` conflates two failures.
10. **Record the outcome**: AGP version, Gradle wrapper version, Kotlin version, JDK, and the
    exact list of removed APIs you replaced. Without this, the next upgrade re-discovers them.

## Procedure

1. Inventory the surface before changing anything:
   ```bash
   grep -rn "applicationVariants\|libraryVariants\|variantFilter\|variant\.outputs" --include=*.kts .
   grep -rn "lintOptions\|packagingOptions\|aaptOptions\|adbOptions" --include=*.kts .
   grep -rn "BuildConfig" --include=*.kt app/src/main | head
   grep -rn "package=" --include=AndroidManifest.xml . | head
   ```
2. Bump the Gradle wrapper only; run `./gradlew help`.
3. Bump AGP only (via `version-catalog`); run `./gradlew help` then `./gradlew tasks`.
4. Fix build scripts: `androidComponents`, block renames, `buildConfig` flag.
5. Bump Kotlin/Compose compiler; `./gradlew assembleDebug`.
6. Bump KSP (or remove kapt); `./gradlew assembleDebug`.
7. Run the full matrix:
   ```bash
   ./gradlew assembleDebug assembleRelease test lint --warning-mode all
   ```
8. Diff the release APK's dex/rule output against the pre-bump build (rule 8).

## Checklist

- [ ] Wrapper, AGP, Kotlin, KSP bumped as separate commits.
- [ ] Zero `applicationVariants`/`libraryVariants`/`variantFilter` remaining.
- [ ] All `*Options` blocks renamed and duplicates deleted.
- [ ] `buildConfig` enabled only where production code needs it.
- [ ] `namespace` set in every module; no manifest `package` reliance.
- [ ] kapt removed or documented per module.
- [ ] `assembleRelease` + `lint` run, not only debug.
- [ ] `--warning-mode all` output reviewed, no new deprecations introduced.
- [ ] Migration record written (versions + removed APIs replaced).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Green build, broken variant logic | delete the `applicationVariants` block | port it to `androidComponents.onVariants` | custom per-variant behaviour silently lost |
| Warning suppressed | `@Suppress("DEPRECATION")` | replace the API | removal happens in the next minor |
| Debug passes, release crashes | only `assembleDebug` | `assembleRelease` + check R8 rules | rules can stop applying |
| Two failures at once | bump AGP and `compileSdk` together | raise compileSdk first | ambiguous causality |
| kapt kept "just in case" | leave both kapt and KSP | remove kapt per module | double processing cost |
| Bump without record | "it works now" | write versions + replaced APIs | next upgrade repeats the work |

## Verify

```bash
./gradlew help tasks --warning-mode all
./gradlew assembleRelease test lint
grep -rn "applicationVariants\|libraryVariants\|variantFilter" --include=*.kts .   # must be empty
```

Expected: no removed-API references, `assembleRelease` succeeds, and `--warning-mode all` shows
no deprecation introduced by this change.

## References

- AGP release notes for the exact removed/renamed APIs in the target version — this skill gives
  the order and the checks; the API list belongs to the release notes.
- `androidComponents` DSL: `onVariants`, `selector()`
