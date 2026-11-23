---
name: build-variants
description: >-
  Design the buildType × flavor matrix so environments, application ids, secrets, resources and
  source sets are declared once and every variant is buildable and installable side by side. Use
  when adding an environment (dev/staging/prod), a white-label or channel flavor, per-variant
  base URLs or icons, a debug-only source set, or when two variants cannot be installed together
  or a backend URL ends up in the wrong build.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - android-developers (build variants + build configuration, re-expressed)
    - this-repo (gap analysis: only version/gradle config skills existed)
---

# Build Variants

One decision: **the matrix has two axes with different meanings — `buildType` is how the code is
optimised, `productFlavor` is which product it is.** Conflating them (a "releaseDev" type) is where
variant explosions start.

## Use when

- Adding an environment, a channel/white-label flavor, or a per-variant application id.
- A base URL, API key, icon, app name or manifest value must differ per variant.
- Variants overwrite each other on the device, or cannot be installed together.
- Deciding where a debug-only class, resource or dependency lives.
- A dependency is only needed by one flavor.

## Do not use when

- Version declarations and catalog structure → `version-catalog`.
- Shared configuration across modules, convention plugins → `gradle-conventions`.
- Signing keys per build type → `signing-and-play-signing`.
- Splitting modules for build-time reasons → `modularization`.

## Rules

1. **Environments are flavors; optimisation is build types.** `debug`/`release` stay the two build
   types; `dev`/`staging`/`prod` are flavors in one dimension. A `releaseDev` build type doubles the
   matrix for no reason.
2. **Every flavor declares its `dimension` explicitly**, and there is exactly one dimension unless a
   second axis is genuinely orthogonal (e.g. environment × white-label). Two dimensions multiply:
   N × M variants must all build.
3. **All flavors must be installable side by side when they coexist:** distinct `applicationId` per
   environment (`applicationIdSuffix = ".dev"` for non-prod), distinct app name/icon.
4. **Configuration values are injected, not branched on.** Base URL, API key and feature defaults
   arrive as `buildConfigField`/`resValue` (with `buildFeatures { buildConfig = true }` where the
   project has it off). Domain code never reads `BuildConfig.DEBUG` to decide behaviour.
5. **Secrets come from the environment or an untracked properties file, never from a committed
   `buildConfigField`.** The build fails loudly when a required secret is absent, instead of
   shipping an empty string.
6. **Variant-specific code lives in the variant source set** (`src/debug/kotlin`, `src/dev/res`),
   not behind `if (BuildConfig.FLAVOR == ...)` in shared code. A branch on flavor in `main` is a
   missing source set.
7. **`manifestPlaceholders` are used for per-variant manifest values** instead of editing the
   manifest per flavor; every placeholder must have a default in `defaultConfig`.
8. **Library modules keep a neutral variant set:** if a library exposes flavors, consumers declare
   `matchingFallbacks` (or `missingDimensionStrategy`) rather than every app recreating the axis.
9. **Use the variant API (`androidComponents.onVariants`) for per-variant wiring**, not the
   deprecated `variantFilter` or `applicationVariants` collections.
10. **Test against the variant that ships.** Instrumented tests run on the debug variant by default;
    if release differs by shrinker or by injected config, run at least the smoke flow against a
    minified build (`testBuildType`).
11. **The matrix is documented and small.** List variants in one table in the module README; if the
    count exceeds what you can name from memory, the dimensions are wrong.

## Procedure

1. Write the dimension(s) and flavors; give each a distinct `applicationId`, name and icon.
2. Add `buildConfigField`/`resValue` defaults in `defaultConfig`, override per flavor.
3. Move variant-only code into `src/<variant>/`, delete flavor branches from `main`.
4. Wire per-variant dependencies with the variant API.
5. Build every combination; install two of them together on one device.

## Checklist

- [ ] Two axes only: buildType for optimisation, flavor for product/environment.
- [ ] Each flavor has a `dimension`; no orphan flavor.
- [ ] Distinct `applicationId` per environment; both installable together.
- [ ] Values injected via `buildConfigField`/`resValue`; no flavor branching in `main`.
- [ ] Secrets from env/untracked file; missing secret fails the build.
- [ ] Variant-specific code/resources in variant source sets.
- [ ] `manifestPlaceholders` have defaults in `defaultConfig`.
- [ ] Library flavors consumed via `matchingFallbacks`/`missingDimensionStrategy`.
- [ ] Per-variant wiring via `androidComponents.onVariants`.
- [ ] Smoke flow run against the minified variant, not only debug.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| 12 variants to maintain | `releaseDev`-style build types | flavors for environment | matrix doubles |
| Two builds collide on device | same `applicationId` | `applicationIdSuffix` | installer replaces the other |
| Prod URL in a dev build | one literal in `main` | injected per flavor | wrong backend from a stale branch |
| Key committed to git | `buildConfigField` secret | env/untracked properties | leaked credential |
| Flavor checks everywhere | `if (BuildConfig.FLAVOR == "dev")` | variant source set | untestable branches |
| Manifest conflicts | edited per flavor | `manifestPlaceholders` | drift between flavors |
| Release crash untested | tests only on debug | `testBuildType`/smoke on minified | shrinker differences |

## Verify

```bash
./gradlew :app:assembleDebug :app:assembleRelease --dry-run
./gradlew :app:assemble<flavor>Debug           # every flavor in the matrix
find app/build/generated -name BuildConfig.java -path '*dev*' | head -3
grep -rn 'BuildConfig.FLAVOR' --include=*.kt app core domain | grep -v BuildConfig.kt | wc -l   # expected: 0
```

Expected: every flavor in the matrix assembles; each non-prod variant has its own
`applicationId` and can be installed next to the prod build; no flavor branch remains in shared
code.

## References

- `productFlavors`, `flavorDimensions`, `matchingFallbacks`, `missingDimensionStrategy`
- `buildConfigField`, `resValue`, `buildFeatures.buildConfig`, `manifestPlaceholders`
- `androidComponents.onVariants`, `testBuildType`
