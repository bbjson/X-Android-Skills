---
name: version-catalog
description: >-
  Own every dependency version in one Gradle version catalog and read it from convention
  plugins, so no version literal ever appears in a module script or in an agent's instructions.
  Use when adding a dependency, bumping a version, migrating hardcoded versions into
  gradle/libs.versions.toml, defining bundles, or when a build breaks because two modules
  declared different versions of the same library.
license: Apache-2.0
metadata:
  domain: build
  level: core
  sources:
    - awesome-android-agent-skills (android-gradle-logic)
    - android-agent-engineering (gradle-build)
    - chrisbanes/skills (gradle-run)
    - original
---

# Version Catalog

One file decides every version. A version literal anywhere else is a defect.

This is the rule that fixes the most common failure in published Android skill bundles: they
embed a literal AGP/Kotlin version in prose, an agent copies it into a new project, and the build
breaks against the current Kotlin/Compose compiler. Here the *shape* is the instruction; the
numbers come from the project.

## Use when

- Adding/removing/upgrading any dependency.
- Two modules disagree about a library's version.
- Creating a new module or convention plugin.
- An agent (or a human) is about to write `implementation("group:artifact:<version>")`.

## Do not use when

- The problem is how to structure `build-logic` and plugin ids → `gradle-conventions`.
- The problem is processing-time performance (KSP/kapt/configuration cache) → `build-performance`.
- The migration subject is AGP itself → `agp9-migration`.

## Rules

1. **Every version lives in `gradle/libs.versions.toml` under `[versions]`.** Not in
   `build.gradle.kts`, not in a plugin's `defaults`, not in README prose, not in a SKILL.md.
2. **Modules consume aliases only:** `implementation(libs.androidx.compose.ui)`. A literal
   `group:artifact:version` in a module script is a defect to fix, not a style preference.
3. **One alias, one dependency.** Do not alias a coordinate that a BOM already manages unless
   you are deliberately overriding the BOM.
4. **BOMs are declared once and applied per module**: `implementation(platform(libs.androidx.compose.bom))`.
   Modules using a BOM must not state Compose library versions.
5. **Prefer `[bundles]` for co-released sets** (compose UI + foundation + material3, test
   triplets). A bundle is justified when the members must move together.
6. **Plugin versions live under `[plugins]` with an `id` and `version`**, and are applied with
   `alias(libs.plugins.x)` — never `id("...") version "..."` in a module.
7. **A version is bumped in exactly one commit**, and the commit message names the alias and
   from→to. Reverting a bump must be one revert, not a hunt.
8. **`-SNAPSHOT`/dynamic versions (`+`, `latest.release`) are forbidden** in application
   modules: they make builds non-reproducible. Explicit alpha/beta is allowed and must be
   written out.
9. **Catalog changes must come with a build of every module that uses the alias** — the
   catalog is not type-checked until resolution.
10. **The catalog is the single source an agent may quote for versions.** When a skill or a
    prompt needs a version, read the catalog; do not recall one.

## Procedure

1. Locate the catalog: `find . -name libs.versions.toml -not -path '*/build/*'`.
2. If absent, create `gradle/libs.versions.toml` and let Gradle pick it up automatically
   (Gradle ≥ 7.4; no settings entry needed).
3. Add entries in this order inside the file:
   ```toml
   [versions]
   # keep alphabetical by alias
   androidxComposeBom = "<read from the project or from maven-metadata.xml>"

   [libraries]
   androidx-compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "androidxComposeBom" }

   [bundles]
   compose = ["androidx-compose-ui", "androidx-compose-foundation", "androidx-compose-material3"]

   [plugins]
   android-application = { id = "com.android.application", version.ref = "agp" }
   ```
4. Replace every literal in module scripts with `libs.*` aliases.
5. Move shared config (`compileSdk`, `minSdk`, `jvmTarget`, compose compiler) into convention
   plugins that read `libs.versions.*.get()`.
6. Build all modules: `./gradlew build --warning-mode=all`.

## Checklist

- [ ] `grep -rn ':[0-9]\+\.[0-9]\+\.[0-9]\+"' --include=*.gradle.kts` returns only catalog-external
      cases (none inside `dependencies { }`).
- [ ] No `id("...") version "..."` outside the root `settings`/`plugins` block.
- [ ] BOM-managed libraries have no explicit version.
- [ ] No dynamic or `-SNAPSHOT` versions in app modules.
- [ ] `[versions]` keys are referenced by `version.ref` (no duplicated literal).
- [ ] All modules build after the change.
- [ ] Any skill/prompt quoting a version quotes a catalog key instead.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Agent bakes a version into a template | `compose-bom:2024.09.03` in prose | `libs.androidx.compose.bom` | rots in months |
| Two modules disagree | one uses catalog, other a literal | migrate the literal | resolution picks one silently |
| BOM ignored | explicit versions for ui/material3 | rely on the BOM | version skew across Compose artefacts |
| Plugin version in module | `id("com.google.devtools.ksp") version "2.x"` | `alias(libs.plugins.ksp)` | two sources of truth |
| "Quick fix" bump | edit one module only | bump the `[versions]` key | other modules stay stale |
| Dynamic version | `version = "1.+"` | exact version | unreproducible builds |

## Verify

```bash
./gradlew build --warning-mode=all
./gradlew :app:dependencies --configuration debugRuntimeClasspath | grep -c " -> "   # resolved conflicts
```

Expected: build succeeds, and the dependency report shows no `->` conflict resolution lines for
Compose/Kotlin artefacts (a conflict line means two declarations disagreed).

## References

- Gradle version catalog reference — TOML schema (`versions`, `libraries`, `bundles`, `plugins`)
- `maven-metadata.xml` for discovering a current version: `https://dl.google.com/dl/android/maven2/<path>/maven-metadata.xml`
