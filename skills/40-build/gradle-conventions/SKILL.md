---
name: gradle-conventions
description: >-
  Move duplicated build configuration into a build-logic project with convention plugins, so every
  module gets the same android/kotlin/compileSdk settings from one place. Use when creating build-logic,
  converting copy-pasted android blocks into a plugin, adding a new module type, applying a plugin by
  id in many modules, or when a change must be made in twelve build files.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - awesome-android-agent-skills (android-gradle-logic)
    - android-agent-engineering (gradle-build)
    - android-skill (modularize)
    - chrisbanes/skills (gradle-run)
    - kotlin-agent-skills (kotlin-tooling-kotlin-toolchain-plugin-authoring)
---

# Gradle Conventions

A convention plugin is **a name for a configuration shape**. If two modules would be configured
identically, the configuration belongs in a plugin, not in both files.

## Use when

- Creating `build-logic/` or the first convention plugin.
- The same `android { }` / `kotlin { }` block appears in ≥3 modules.
- Adding a new module type (feature, library, compose-library, test).
- A build setting change requires editing many files.
- Precompiled script plugins vs `Plugin<Project>` classes is unclear.

## Do not use when

- The problem is which version to use → `version-catalog`.
- The problem is AGP API removals → `agp9-migration`.
- The problem is build speed → `build-performance`.

## Rules

1. **`build-logic` is an included build, not a module of the app.** `includeBuild("build-logic")` in
   `settings.gradle.kts`, with its own `settings.gradle.kts`. This keeps build logic out of the app's
   dependency graph and out of the app's own configuration cache key.
2. **One plugin per module *type*, named for the type:** `android-library`, `android-feature`,
   `android-compose`, `android-test`. A plugin named after a module (`feed-plugin`) is a return to
   per-module files.
3. **Plugins read versions from the catalog, never from literals.** `libs.findVersion("agp")` /
   `libs.versions.agp.get()` inside the plugin. (See `version-catalog` rule 10 — the catalog is the
   only source.)
4. **Precompiled script plugins (`.gradle.kts` under `build-logic/convention/src/main/kotlin/`) are
   the default.** Use a `Plugin<Project>` class only when you need typed extensions, conditional
   configuration depending on other plugins, or logic that a script cannot express.
5. **`plugins { }` blocks in the consuming module stay one line.** The goal is
   `plugins { id("android-feature") }` and nothing else build-related in the module file.
6. **The plugin applies the plugins it needs, in order.** `com.android.library` → `org.jetbrains.kotlin.android`
   → compose compiler → KSP (only if the module uses it). Consumers must not re-apply them.
7. **`compileSdk`/`minSdk`/`targetSdk`/`jvmTarget` are declared once**, in the base plugin. A module
   that needs an override must be a deliberate, commented exception.
8. **Plugin ids are registered in `build-logic/convention/build.gradle.kts` via
   `gradlePlugin { plugins { register("androidFeature") { id = "android-feature" … } } }`.** String ids
   in consumer files must match exactly; there is no compile check, so keep them few.
9. **No `allprojects`/`subprojects` blocks.** They defeat configuration avoidance and configuration
   cache. Convention plugins replace them entirely.
10. **A convention plugin change is a project-wide change: build every module before merging.**
    `./gradlew assembleDebug test` on the main app plus `--dry-run` on the full task graph.
11. **Keep the plugin surface small.** Every parameter added to a plugin is a new configuration axis
    that must be tested against every consumer. Prefer a new plugin over a new boolean.

## Procedure

1. Create the included build:
   ```
   build-logic/settings.gradle.kts          (pluginManagement + dependencyResolutionManagement)
   build-logic/convention/build.gradle.kts  (kotlin-dsl plugin, gradlePlugin { } registrations)
   build-logic/convention/src/main/kotlin/<pkg>/AndroidLibraryConventionPlugin.kt
   ```
2. Register in the app's `settings.gradle.kts`: `includeBuild("build-logic")`.
3. Implement the base plugin: apply AGP/Kotlin, configure `android { }` and `kotlin { }` from the
   catalog.
4. Add a feature plugin that applies the base + compose + (optionally) KSP.
5. Convert one module; build it alone.
6. Convert the rest; build everything.
7. Delete the now-duplicated blocks and confirm `git diff` shows only deletions in modules.

## Checklist

- [ ] `build-logic` included as a build, with its own settings file.
- [ ] Plugins named by module type, not by feature.
- [ ] All versions read from the catalog inside the plugin.
- [ ] Precompiled script plugin unless a `Plugin<Project>` is justified.
- [ ] Consumer module's build file reduced to plugin ids + dependencies.
- [ ] `compileSdk`/`minSdk`/`jvmTarget` declared once.
- [ ] Plugin ids registered and matching exactly.
- [ ] No `allprojects`/`subprojects` blocks remain.
- [ ] All modules build after conversion.
- [ ] Duplicated blocks deleted, not left commented.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Per-module plugin | `id("feed-convention")` | `id("android-feature")` | one plugin per type |
| Literal version in plugin | `"com.android.library"` with a version string | catalog lookup | one source of truth |
| Logic in a script | 200-line `.gradle.kts` with `if`s | `Plugin<Project>` class | untyped, untestable |
| Configuration cache broken | `allprojects { }` | convention plugins | eager configuration |
| Silent breakage | consumer re-applies plugins | plugin applies what it needs | conflicting order |
| One-line change, 12 files | copy-paste | convention plugin | drift |

## Verify

```bash
./gradlew :build-logic:convention:build
./gradlew help --warning-mode all
./gradlew assembleDebug test
./gradlew --configuration-cache help     # must not report problems from convention plugins
```

Expected: modules' build files contain only plugin ids and dependencies, every module builds, and the
configuration cache reports no problems introduced by the plugins.

## References

- Gradle composite builds (`includeBuild`), precompiled script plugins
- `gradlePlugin { plugins { register(...) } }` registration DSL
