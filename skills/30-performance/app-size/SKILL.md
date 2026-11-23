---
name: app-size
description: >-
  Reduce download and installed size with measured numbers: App Bundle splits, R8 and resource
  shrinking, native library packaging, asset and feature delivery, and format choices. Use when
  the APK/AAB is too large, before a Play upload that trips a size warning, when deciding between
  bundled and downloaded assets, or when someone claims a size win without a before/after number.
license: Apache-2.0
metadata:
  domain: performance
  level: advanced
  sources:
    - android-developers (reduce app size, Play delivery, re-expressed)
    - this-repo (gap analysis: performance domain had no size skill)
---

# App Size

One decision: **which bytes the user must download versus which bytes can arrive later.** There is
no "size optimisation" in the abstract — only that split, plus removing what nobody executes.

## Use when

- The AAB or installed size is growing, or Play warns about it.
- Deciding whether an asset set ships inside the app, in an install-time pack, or on demand.
- Enabling minification/resource shrinking, or an R8 rule set that is disabling shrinking.
- The native library set is large, or an ABI split question comes up.
- Someone reports a size improvement without a measured before/after.

## Do not use when

- APK size is irrelevant and the problem is startup or scroll jank → `startup-and-perfetto`,
  `recomposition`.
- R8 breaking code at runtime rather than shrinking size → `r8-for-compose`.
- Build wall-clock time → `build-performance`.
- What ships in the bundle per variant/flavor → `build-variants`.

## Rules

1. **Measure the installed size for a specific device spec, not the AAB size.** An app bundle is a
   container; the number users feel is base + the matching ABI/density/language splits. Record
   `bundletool get-size total` with a device spec, before and after.
2. **Ship an AAB, not a universal APK, and let Play split by ABI, density and language.** A
   universal APK contains every ABI and every density — usually several times the installed size.
3. **Filter locales and densities explicitly** (`androidResources.localeFilters`, density splits)
   when the app ships more translations or bitmaps than it needs; leaving them implicit means the
   bundle carries dead translations forever.
4. **Code shrinking and resource shrinking are enabled together in release.** `isShrinkResources`
   without `isMinifyEnabled` does nothing, and an over-broad `-keep` rule set silently disables
   shrinking; audit the rules before blaming R8.
5. **Native libraries: ship the ABIs you support, nothing else** (`abiFilters`), and decide
   `useLegacyPackaging` deliberately — compressed libraries shrink the download and cost install
   time, uncompressed ones load faster and occupy more disk.
6. **Assets are delivered by policy:** in-app only if needed on first launch; install-time pack for
   content required by the first session; fast-follow or on-demand for media, tutorials and
   optional features. An install-time pack that is only opened from settings is wasted download.
7. **Never ship both a raster and a vector version of the same icon**, and prefer vector for icons
   and WebP for photographic assets. A PNG placed in five density buckets is five copies of the
   same picture.
8. **Do not vendor a library you use for one call.** A dependency's transitive graph is the usual
   source of multi-megabyte growth; check the dependency tree before adding a "small" SDK.
9. **Remove licence/`META-INF` duplicates deliberately, never blanket-exclude `*.kotlin_module`.**
   Excluding metadata files breaks reflection-based libraries in ways that only appear in release.
10. **Baseline profiles and startup libraries are worth their bytes** — the size cost is small and
    the startup win is measured (`baseline-profiles`). Do not trade a startup regression for a size
    win without a number for both.
11. **A size claim needs the same device spec on both sides.** Comparing a debug APK to a release
    AAB is not a measurement.

## Procedure

1. Get a device spec: `bundletool get-device-spec`, keep it in the repo (`docs/` or `tools/`).
2. Baseline: build the release bundle, run `bundletool get-size total` with that spec, record it.
3. Identify the largest contributors: `apkanalyzer files list` / Android Studio *Analyze APK*.
4. Apply one change (split config, R8 rules, ABI filter, asset delivery, format swap).
5. Re-measure with the same spec and record the delta next to the change.
6. Repeat for smoke-testing: install the `.apks` on a real device and run the first-launch flow.

## Checklist

- [ ] Device spec saved; both measurements use it.
- [ ] Release ships an AAB; no universal APK.
- [ ] Locale and density filters set to what the app actually supports.
- [ ] `isMinifyEnabled` and `isShrinkResources` both on in release.
- [ ] `-keep` rules audited (no `-keep class ** { *; }` catch-all).
- [ ] `abiFilters` lists only supported ABIs; `useLegacyPackaging` decided.
- [ ] Each large asset assigned to app / install-time / fast-follow / on-demand.
- [ ] No duplicate raster+vector icons; photographic assets in WebP.
- [ ] New dependency justified by its transitive size.
- [ ] Before/after numbers recorded in the PR description.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| "We saved 40%" | APK → AAB comparison | same device spec, both sides | different artefacts |
| Shrinking does nothing | `isShrinkResources` alone | both flags on | resource shrink needs code shrink |
| Release-only breakage | blanket `-keep`/exclude `kotlin_module` | targeted rules | reflection metadata removed |
| Huge download | universal APK | bundle + splits | every ABI/density shipped |
| Slow install, fast start | compress native libs | decide per `useLegacyPackaging` | trade download for mmap |
| Unused tutorials on install | install-time pack | on-demand pack | user pays for unused bytes |
| Multi-MB "small" SDK | added for one helper | dependency tree review | transitive growth |

## Verify

```bash
./gradlew :app:bundleRelease
bundletool build-apks --bundle=app/build/outputs/bundle/release/app-release.aab --output=/tmp/app.apks
bundletool get-size total --apks=/tmp/app.apks --device-spec=device-spec.json
$ANDROID_HOME/cmdline-tools/latest/bin/apkanalyzer files list app/build/outputs/apk/release/app-release.apk | head -30
```

Expected: `get-size total` reports the min and max download size for the saved device spec, and the
number is recorded in the change description with the same spec used for the "before" value.

## References

- Play App Bundle splits, Play Feature Delivery, Play Asset Delivery
- `bundletool get-size`, `get-device-spec`, `install-apks`
- `apkanalyzer` file-size/download-size; Android Studio *Analyze APK*
