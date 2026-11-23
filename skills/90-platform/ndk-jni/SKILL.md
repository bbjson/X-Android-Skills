---
name: ndk-jni
description: >-
  Ship native code that loads on every device and crashes readably: ABI selection, JNI reference
  and string discipline, symbol stripping with retained symbols, page-size alignment and tombstone
  triage. Use when adding a native library or CMake build, when JNI leaks or crashes, when
  UnsatisfiedLinkError appears only in release or on one ABI, or when a native crash has no Java
  stack.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - android-developers (NDK guides, JNI tips, re-expressed)
    - this-repo (gap analysis: NDK/JNI absent; only kernel modules existed)
---

# NDK and JNI

One decision: **what crosses the boundary, and who owns it on each side.** Every JNI bug in
production is an ownership bug: a reference not released, a string not freed, a thread not
attached, or a symbol not exported.

## Use when

- Adding a native library, CMake/`externalNativeBuild`, or a prebuilt `.so`.
- A build works on an emulator and fails on a device, or only in release.
- `UnsatisfiedLinkError`, `SIGSEGV` in native code, or a tombstone with only addresses.
- A JNI loop leaks memory, or a native thread crashes on first JNI call.
- Deciding ABI filters, STL linkage, or symbol stripping for a Play upload.

## Do not use when

- Kernel modules and GKI/vermagic constraints → `kernel-lkm`.
- Adding native symbols to crash reporting only → `crash-reporting`.
- Native code size/delivery decisions → `app-size`.
- Performance measurement of a native path → `benchmark-testing`.

## Rules

1. **Ship only the ABIs the device fleet uses** (`abiFilters`), and include the emulator ABI the team
   tests on. A missing ABI is an `UnsatisfiedLinkError` on a real device that no JVM test catches.
2. **One STL per app.** Mixing `c++_shared` and `c++_static` across libraries produces duplicate
   symbols and crashes that look random; choose one and apply it to every native dependency.
3. **Export deliberately.** Build with hidden visibility and mark entry points `JNIEXPORT`
   (`-fvisibility=hidden`), or register with `RegisterNatives` in `JNI_OnLoad`. Name mangling that
   silently stops matching after a package rename is a classic release-time break.
4. **Local references are freed in loops.** The local reference table is small and fixed; creating a
   reference per iteration without `DeleteLocalRef` (or a `PushLocalFrame`/`PopLocalFrame` pair) kills
   the process with a reference-table overflow.
5. **Strings are copied out and released in pairs.** `GetStringUTFChars` must be paired with
   `ReleaseStringUTFChars`; for read-only use, `GetStringRegion`/`GetStringUTFRegion` avoids the
   allocation entirely.
6. **A `JNIEnv*` belongs to one thread.** Native threads must `AttachCurrentThread` before any JNI
   call and `DetachCurrentThread` before exiting; using a cached `JNIEnv*` across threads is
   undefined behaviour that passes tests and crashes in production.
7. **Check for pending exceptions.** After any JNI call that can throw, `ExceptionCheck` and return;
   calling further JNI functions with a pending exception is invalid.
8. **Large data crosses as a buffer or a file descriptor, not as a Java array copy.** `GetPrimitiveArrayCritical`
   must not be held across JNI calls or blocking work.
9. **Strip in release, keep the unstripped symbols as a CI artefact.** Stripping without retaining
   symbols turns every native crash into an unreadable tombstone; both are required.
10. **Declare full debug-symbol level for the Play upload** where the project uses it, so native
    crashes are symbolicated on the platform side.
11. **Native libraries must satisfy the current page-size requirement.** Link with the appropriate
    maximum page size so the loader can map the library on devices with larger pages; a library
    built for the old alignment fails to load on those devices, not at build time.
12. **Measure before moving work to native.** A JNI transition plus argument copying is not free; a
    native rewrite of a cheap Kotlin function is slower and unhittable by the debugger.

## Procedure

1. Configure CMake/`externalNativeBuild`, ABI filters and one STL; build for device and emulator ABI.
2. Export entry points explicitly; add a `JNI_OnLoad` if using `RegisterNatives`.
3. Audit every JNI function for reference/string pairing and thread attachment.
4. Enable stripping in release and archive unstripped libraries.
5. Trigger a native crash in a debug build, symbolicate with `ndk-stack`, and confirm the release
   upload path keeps symbols.

## Checklist

- [ ] `abiFilters` covers the fleet and the emulator; no universal `.so` set.
- [ ] One STL across all native libraries.
- [ ] Exports explicit (hidden visibility + `JNIEXPORT`, or `RegisterNatives`).
- [ ] Local references deleted in loops or framed.
- [ ] `GetStringUTFChars`/`ReleaseStringUTFChars` paired; region calls where read-only.
- [ ] Native threads attach and detach.
- [ ] `ExceptionCheck` after throwing JNI calls.
- [ ] No `GetPrimitiveArrayCritical` held across calls.
- [ ] Release libraries stripped; unstripped symbols archived per build.
- [ ] Page-size alignment satisfied for the current target.
- [ ] Native path justified by a measurement.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| `UnsatisfiedLinkError` on one phone | single ABI build | `abiFilters` for the fleet | library absent for that ABI |
| Random crash in one library | mixed STL linkage | one STL everywhere | duplicate runtime symbols |
| Works in debug, fails in release | name-mangled export + R8 rename | `RegisterNatives`/`JNIEXPORT` | symbol no longer matches |
| Reference table overflow | refs created per iteration | `DeleteLocalRef`/frames | fixed local table |
| Crash on native thread | cached `JNIEnv*` | `AttachCurrentThread` | env is thread-local |
| Unreadable tombstone | stripped only | strip + archive symbols | no line information |
| Fails to load on new devices | old page alignment | link with required page size | loader cannot map |

## Verify

```bash
./gradlew :app:externalNativeBuildDebug
find app/build -name '*.so' | sed 's#.*/##' | sort -u
readelf -l app/build/intermediates/merged_native_libs/release/out/lib/arm64-v8a/lib*.so | grep LOAD
adb -s <serial> logcat -d | grep -iE 'UnsatisfiedLinkError|SIGSEGV|tombstone' | tail -20
ndk-stack -sym app/build/intermediates/merged_native_libs/debug/out/lib/arm64-v8a -dump /tmp/tombstone.txt
```

Expected: the release APK contains one `.so` per supported ABI, program headers satisfy the required
page alignment, and `ndk-stack` resolves a tombstone to file and line using the archived symbols.

## References

- NDK guides: JNI tips, `RegisterNatives`, `JNI_OnLoad`, `AttachCurrentThread`
- `externalNativeBuild`, `abiFilters`, `debugSymbolLevel`, `target_link_libraries`
- `ndk-stack`, `llvm-symbolizer`, tombstones
