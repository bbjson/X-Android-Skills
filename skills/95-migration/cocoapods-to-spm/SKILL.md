---
name: cocoapods-to-spm
description: >-
  Move a Kotlin Multiplatform iOS integration from CocoaPods to Swift Package Manager: replace the
  cocoapods plugin, produce a Package.swift or an XCFramework, wire the Xcode build, and keep cinterop
  working. Use when the KMP project uses kotlin("native.cocoapods"), when podspec maintenance is the
  bottleneck, when Xcode/CI must resolve dependencies without CocoaPods, or when a third-party Pod must
  be replaced.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - kotlin-agent-skills (kotlin-tooling-cocoapods-spm-migration)
    - kotlin-kmp-claude-agent-skills (kotlin-build-kmp-gradle-governance, kotlin-platform-kmp-bridges)
    - kmp-compose-multiplatform-skill
---

# CocoaPods to Swift Package Manager

CocoaPods asks you to maintain a `podspec` that describes Kotlin output. SPM asks you to produce a
**product (XCFramework or binary target)** and declare it in `Package.swift`. The migration is mostly
about who owns the framework build.

## Use when

- A KMP project uses `kotlin("native.cocoapods")` and a `.podspec`.
- Xcode/CI should resolve without CocoaPods (`pod install` in CI is the pain).
- A third-party Pod must be replaced by an SPM dependency.
- Considering the built-in SPM export in recent Kotlin versions.

## Do not use when

- The target is not iOS → `kmp`.
- The problem is cinterop declarations themselves → `kmp` (platform bridges).
- The problem is Android build config → `gradle-conventions`.

## Rules

1. **Decide the ownership model first:** (a) Kotlin produces an `XCFramework` and a `Package.swift` wraps
   it as a binary target, or (b) the framework is built by an Xcode build phase and SPM only declares the
   local package. (a) is reproducible in CI; (b) is faster locally. Pick one and write it down.
2. **One output product per consumer need.** A single `Shared` framework exporting everything couples
   every feature's link time; split by module boundary (`modularization`), not by convenience.
3. **Remove the CocoaPods plugin, the `podspec`, and `Podfile` in the same change that adds the SPM
   package** — leaving both means two build paths that will disagree.
4. **Framework search paths and the Xcode build phase must point at the produced artefact**, not at a
   developer's absolute path. A workspace that builds on one machine and not CI is this bug.
5. **Architectures: produce `iosArm64` + `iosSimulatorArm64` (+ `iosX64` only if Intel Macs are
   supported).** An XCFramework missing a simulator slice fails only on the CI runner's architecture.
6. **Third-party Pods become SPM dependencies or cinterop wrappers.** A Pod that is not on SPM needs a
   binary target or a cinterop definition; do not leave a mixed `Podfile` for "just one library".
7. **Swift API surface: use `@ObjCName`/`@HiddenFromObjC` deliberately** to keep the Swift-facing API
   small and readable; the generated ObjC header is a real API, not an implementation detail.
8. **Version the framework by the app's release, not by the Kotlin version.** A `Package.swift` pinned to
   a Kotlin release number couples two independent upgrade cycles.
9. **CI must build the framework before building the iOS app**, in the same job or via an artefact, and
   the app must not silently link a stale framework from a developer's cache.
10. **Verify on both a device and a simulator slice, from a clean checkout.** `xcodebuild` on the simulator
    is necessary but not sufficient: device builds catch missing arm64 slices and code-signing issues.

## Procedure

1. Inventory: `grep -rn "cocoapods\|podspec\|pod(" --include=*.kts --include=*.podspec --include=Podfile .`
2. Choose the ownership model (rule 1) and write it in the repo README.
3. Configure the framework binary: `binaries.framework { baseName = "Shared"; isStatic = … }` (or an
   XCFramework task), with the target list from rule 5.
4. Add `Package.swift` with the binary/local target; remove `cocoapods { }` from `build.gradle.kts`,
   delete the `.podspec` and `Podfile`/`Podfile.lock`.
5. Point Xcode at the package; remove the Pods project/workspace references.
6. Replace each Pod with an SPM dependency or a cinterop wrapper (rule 6).
7. Clean build: framework → simulator app → device app, from a fresh clone.

## Checklist

- [ ] Ownership model chosen and documented.
- [ ] One product per consumer need; no "Shared everything" framework.
- [ ] CocoaPods plugin, podspec, Podfile and lockfile removed in the same change.
- [ ] Framework search paths relative, no absolute developer paths.
- [ ] `iosArm64` + `iosSimulatorArm64` (and `iosX64` if needed) present in the artefact.
- [ ] All Pods replaced (SPM or cinterop); no leftover `Podfile`.
- [ ] Swift API surface reviewed (`@ObjCName`/`@HiddenFromObjC`).
- [ ] Framework versioning independent of the Kotlin version.
- [ ] CI builds framework before app; no stale linked artefact.
- [ ] Verified from a clean checkout on simulator **and** device.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Builds locally, fails CI | absolute framework path | relative/uniform paths | machine-specific |
| Simulator works, device fails | only simulator slice | add `iosArm64` | missing slice |
| Two build paths | keep Podfile "for now" | remove with the migration | divergence |
| Stale framework | link from build dir | CI builds framework first | silent old code |
| Coupled upgrades | package version = Kotlin version | app release versioning | forced lockstep |
| One giant framework | everything in `Shared` | module-scoped products | link time, coupling |

## Verify

```bash
./gradlew :shared:linkDebugFrameworkIosSimulatorArm64 :shared:linkDebugFrameworkIosArm64
xcodebuild -project iosApp/iosApp.xcodeproj -scheme iosApp -sdk iphonesimulator build
xcodebuild -project iosApp/iosApp.xcodeproj -scheme iosApp -sdk iphoneos build CODE_SIGNING_ALLOWED=NO
ls iosApp/iosApp/Frameworks 2>/dev/null; grep -rn "cocoapods" --include=*.kts .   # empty
```

Expected: both simulator and device builds succeed from a clean checkout without CocoaPods installed, and
no `cocoapods` reference remains in the Gradle files.

## References

- Kotlin/Native frameworks, `XCFramework` tasks, `binaries.framework { }`
- Swift Package Manager binary targets and local packages
