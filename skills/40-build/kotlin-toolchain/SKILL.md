---
name: kotlin-toolchain
description: >-
  Align the JDK toolchain, Kotlin language/API version, JVM target and Compose compiler plugin so
  every module compiles against the same Kotlin, without relying on the machine's JDK. Use when
  modules disagree about Kotlin or JVM target, when a "Kotlin version mismatch" or
  "unsupported class file major version" error appears, when migrating to the Compose compiler
  Gradle plugin, or when CI's JDK differs from a developer's.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - kotlin-agent-skills (kotlin-tooling-kotlin-toolchain, kotlin-tooling-gradle-to-kotlin-toolchain-project)
    - agent-skills-standard (android-tooling)
    - awesome-android-agent-skills (android-gradle-logic)
    - claude-android-ninja
---

# Kotlin Toolchain

Three separate version axes are usually conflated: **JDK** (runs the compiler), **Kotlin** (language
+ stdlib), and **JVM target** (bytecode). Each is declared in exactly one place.

## Use when

- `Unsupported class file major version`, `Module was compiled with an incompatible version of Kotlin`,
  or `Cannot inline bytecode built with JVM target 21`.
- Adding a module that must compile for the same target as the rest.
- Migrating from `composeOptions.kotlinCompilerExtensionVersion` to the Compose compiler plugin.
- CI and local builds produce different results.
- Deciding between `jvmToolchain(n)` and `compilerOptions.jvmTarget`.

## Do not use when

- The migration subject is AGP itself → `agp9-migration`.
- The problem is annotation processing → `ksp-processing`.
- The problem is dependency versions (not Kotlin/JDK) → `version-catalog`.

## Rules

1. **Declare a JDK toolchain, not a `jvmTarget` string, for the compiler.** `kotlin { jvmToolchain(17) }`
   makes Gradle *select* a JDK 17 for compilation regardless of `JAVA_HOME`. It does **not**
   download one: without a toolchain resolver plugin (or an installed JDK 17) the build fails with
   `Cannot find a Java installation ... matching: {languageVersion=17}`. Setting only
   `compilerOptions.jvmTarget` produces code for a target the compiler cannot guarantee exists.
   A **JRE-only installation is not a toolchain**: Ubuntu's `openjdk-21-jre` has no `javac`, and
   Gradle reports `Toolchain installation '...' does not provide the required capabilities:
   [JAVA_COMPILER]`. Check `ls /usr/lib/jvm/*/bin/javac` before blaming the build script.
2. **`jvmTarget` and the Java toolchain's `sourceCompatibility` must agree.** A Kotlin/Java mismatch
   shows up as `Cannot inline bytecode built with JVM target` at compile time in one module only.
3. **One declaration point.** The `kotlin { }` block belongs in the base convention plugin
   (`gradle-conventions`), not in each module. Two modules with different `jvmToolchain` values is the
   defect this skill exists to prevent.
4. **Kotlin version comes from the catalog** and the Kotlin Gradle plugin version must equal the
   Kotlin stdlib version the modules resolve. A `kotlin-stdlib` bumped independently of the plugin is
   a compile/runtime split.
5. **The Compose compiler is a Gradle plugin now.** `org.jetbrains.kotlin.plugin.compose` applied with
   the Kotlin version — no separate `kotlinCompilerExtensionVersion` number to keep in sync. Any
   remaining `composeOptions { kotlinCompilerExtensionVersion = … }` is legacy that should be removed
   during the next touch.
6. **Kotlin language version may lag the compiler; the API version may not exceed it.**
   `languageVersion` (syntax) and `apiVersion` (stdlib surface) are separate knobs. Lowering
   `languageVersion` for compatibility is legitimate; lowering `apiVersion` below what dependencies
   were compiled with causes `NoSuchMethodError` at runtime.
7. **`freeCompilerArgs` must not disable warnings project-wide.** `-Xsuppress-warnings` is a
   build-wide debt; opt-in annotations (`@OptIn`) are per-use. Warnings-as-errors is preferable for
   new code.
8. **Incremental compilation stays on, and K2 is the default.** Do not set
   `kotlin.incremental=false` to work around a bug — that turns a 3s compile into a 3min one. Fix the
   cause or pin the version.
9. **The same toolchain on CI and locally.** CI must run `./gradlew` with the toolchain provisioned
   (or a matching JDK); a different `JAVA_HOME` on CI is a build that only fails there.
10. **Verify with the class file version, not by trust.** `javap -verbose` on one compiled class shows
    the major version; a mismatch between modules is visible in the build output, not at runtime.
11. **On AGP 9+, a pure-Kotlin module must declare the Kotlin JVM plugin without a version.** AGP
    puts Kotlin on the build classpath, so `alias(libs.plugins.kotlin.jvm)` in a `java-library`
    module fails with `The request for this plugin could not be satisfied because the plugin is
    already on the classpath with an unknown version`. Declare the version once in the root
    (`alias(libs.plugins.kotlin.jvm) apply false`) and apply it as `id("org.jetbrains.kotlin.jvm")`
    in the module.

## Procedure

1. Inventory current settings:
   ```bash
   grep -rn "jvmToolchain\|jvmTarget\|languageVersion\|apiVersion\|kotlinCompilerExtensionVersion\|org.jetbrains.kotlin.plugin.compose" --include=*.kts .
   ./gradlew buildEnvironment | grep -i "kotlin-"
   ```
2. Set the toolchain once in the base convention plugin (rule 3).
3. Align `jvmTarget` with the toolchain (rule 2).
4. Read the Kotlin version from the catalog in the plugin (rule 4).
5. Replace `composeOptions` with the Compose compiler plugin (rule 5).
6. Rebuild everything, then `javap -verbose` one class per module (rule 10).

## Checklist

- [ ] `jvmToolchain(n)` declared once, in the base convention plugin.
- [ ] `jvmTarget` matches the toolchain; Java compatibility matches too.
- [ ] Kotlin Gradle plugin and stdlib versions come from the same catalog key.
- [ ] No `composeOptions.kotlinCompilerExtensionVersion` remaining.
- [ ] `languageVersion`/`apiVersion` not lowered below dependency requirements.
- [ ] No project-wide `-Xsuppress-warnings`.
- [ ] Incremental compilation enabled.
- [ ] CI JDK matches the declared toolchain.
- [ ] Compiled class file major version identical across modules.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Compiles locally, fails on CI | rely on `JAVA_HOME` | `jvmToolchain(17)` | toolchain provisioned |
| Inline bytecode error | Kotlin target 17, Java 11 | one aligned target | mixed targets |
| Runtime `NoSuchMethodError` | lower `apiVersion` | keep API ≥ deps | stdlib surface removed |
| Compose mismatch | manual extension version | compose compiler plugin | version coupling |
| Slow builds | `kotlin.incremental=false` | fix the cause | full recompiles |
| Hidden warnings | `-Xsuppress-warnings` | opt-in per use | debt accumulates |
| Two modules disagree | per-module `kotlin { }` | convention plugin | drift |

## Verify

```bash
./gradlew buildEnvironment | grep -E "kotlin-(gradle-plugin|stdlib)"
./gradlew assembleDebug test
javap -verbose app/build/tmp/kotlin-classes/debug/<pkg>/MainActivity.class | grep "major version"
```

Expected: one Kotlin plugin version, one stdlib version, identical `major version` across modules, and
no `composeOptions` in any build script.

## References

- Kotlin Gradle plugin `jvmToolchain`, `compilerOptions.jvmTarget`, `languageVersion`/`apiVersion`
- Compose compiler Gradle plugin (`org.jetbrains.kotlin.plugin.compose`)
