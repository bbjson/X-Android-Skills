---
name: ksp-processing
description: >-
  Configure KSP for Room, Hilt, Moshi and other processors — correct dependency scope, arguments,
  multi-module ordering and incremental builds — and get off kapt. Use when adding an annotation
  processor, when generated code is missing or stale, when a processor needs a schema directory,
  when a module still uses kapt, or when KSP breaks only in incremental builds.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - kotlin-agent-skills (kotlin-tooling-kotlin-toolchain)
    - agent-skills-standard (android-persistence)
    - awesome-android-agent-skills (gradle-build-performance)
    - android-skill (fix-build)
---

# KSP Processing

KSP is a **compiler-adjacent code generator with its own dependency configuration and its own
incremental model**. Almost every "KSP doesn't work" is one of: wrong scope, missing argument,
stale output, or a kapt-era habit.

## Use when

- Adding Room/Hilt/Moshi/KotterKnife-style generated code.
- `Cannot find implementation for …` or `Unresolved reference` on generated symbols.
- A processor needs a schema/options directory (`room.schemaLocation`).
- Migrating a module from kapt to KSP.
- Generated code works after `clean` but not incrementally.
- Multi-module project where one module's generated code is not visible to another.

## Do not use when

- The failure is Java/Kotlin version alignment → `kotlin-toolchain`.
- The failure is dependency resolution → `version-catalog` / `bug-fix`.
- The processor is only used in tests → still this skill, but note the `kspTest` scope.

## Rules

1. **The processor goes in `ksp(...)`, not `implementation(...)` or `kapt(...)`.**
   `ksp(libs.hilt.compiler)` — a processor on the compile classpath leaks into the APK and into
   other modules' compilation.
2. **The processor's version must match its runtime library.** `ksp(libs.room.compiler)` and
   `implementation(libs.room.runtime)` come from the same catalog key. A compiler newer than the
   runtime generates code the runtime cannot run; older silently misses features.
3. **Apply the KSP plugin where you apply the runtime dependency.** A module with `room-runtime` and
   no `ksp` plugin compiles but has no implementation class — the error appears at runtime, not build.
4. **Arguments are declared in the `ksp { }` block, per module, not globally.** Room's
   `room.schemaLocation` belongs in the module that owns the database; putting it in
   `allprojects` writes schemas from every module.
5. **Room schema output is committed and versioned.** `ksp { arg("room.schemaLocation", "$projectDir/schemas") }`
   and commit `schemas/` — this is what makes migration tests possible (`MigrationTestHelper`).
   Without it, a migration can only be tested against the current version.
6. **One processor per concern, and no kapt + KSP for the same processor.** Both will generate and
   the duplicate class error is confusing. Migrate fully, not partially.
7. **KSP-generated code is source, not an API.** Never reference it from a different module. If a
   generated type must cross a module boundary, the module is wrong (`layering`/`modularization`), or
   the generator is being used to avoid writing a real interface.
8. **Incrementality requires a compliant processor.** All first-party AndroidX/Hilt/Room processors
   are; a third-party one may not be. If only `clean` fixes it, the processor is the suspect — check
   its docs before adding `ksp.incremental=false` (which slows every build).
9. **Test sources use `kspTest` / `kspAndroidTest`, not the main configuration.** A processor applied
   to main that is only needed for tests adds build time to every module.
10. **Verify by looking at the generated file, not at the absence of errors.** KSP writes to
    `build/generated/ksp/<variant>/…`; a "warning: no sources" there means the processor ran on
    nothing (wrong scope or missing annotation).
11. **KSP args must not contain `${}` interpolations resolved at the wrong time.** In a
    `Plugin<Project>` use `layout.buildDirectory`, not a hardcoded `build/` path — otherwise
    `buildDir` overrides silently write to the wrong directory.

## Procedure

1. Apply the plugin (`alias(libs.plugins.ksp)` or via the convention plugin).
2. Add `ksp(libs.<processor>)` next to the runtime dependency; check versions share a catalog key.
3. Add module-scoped arguments:
   ```kotlin
   ksp { arg("room.schemaLocation", "$projectDir/schemas") }
   ```
4. Migrate any kapt usage in the same module: remove `kapt(...)`, add `ksp(...)`, remove the kapt
   plugin if it was its only consumer.
5. Build the module; open `build/generated/ksp/debug/` and confirm the expected file exists.
6. Rebuild incrementally (change one entity, rebuild) and confirm the generated file updates.
7. Commit the schema directory if Room.

## Checklist

- [ ] Processors in `ksp(...)`, runtime in `implementation(...)`, same version key.
- [ ] KSP plugin applied in every module that has generated code.
- [ ] Module-scoped `ksp { arg(...) }`, no global processor arguments.
- [ ] Room `schemaLocation` set and `schemas/` committed.
- [ ] No module uses both kapt and KSP for the same processor.
- [ ] No cross-module reference to generated types.
- [ ] Generated output inspected at `build/generated/ksp/<variant>/`.
- [ ] Incremental rebuild verified (no `clean` required).
- [ ] Test-only processors in `kspTest`/`kspAndroidTest`.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| No implementation class | `implementation(libs.hilt.compiler)` | `ksp(libs.hilt.compiler)` | processor on compile classpath |
| Runtime crash after upgrade | compiler and runtime from different keys | one catalog key | generated API mismatch |
| Needs `clean` always | `ksp.incremental=false` | find the non-compliant processor | every build full |
| Schema missing | no `schemaLocation` | commit `schemas/` | migrations untestable |
| Duplicate class | kapt + ksp both | migrate fully | double generation |
| Generated type used cross-module | import generated class | expose a real interface | build-order coupling |
| Processor ran on nothing | assume success from no errors | inspect `build/generated/ksp` | silent no-op |

## Verify

```bash
./gradlew :core:database:assembleDebug
ls build/generated/ksp/debug/kotlin/ | head
# incremental check
touch src/main/kotlin/.../SomeEntity.kt && ./gradlew :core:database:assembleDebug --info | grep -i ksp
```

Expected: the generated file exists for the annotated types, a one-file change regenerates only
affected output, and no `clean` is needed between builds.

## References

- KSP `ksp(...)` configuration, `ksp { arg(...) }`, `kspTest`
- Room `room.schemaLocation`, `MigrationTestHelper`
