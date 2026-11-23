---
name: emulator-management
description: >-
  Create, reset and drive Android emulators reproducibly — hardware acceleration, GPU mode, snapshots,
  clean state per run, parallel AVDs and managed devices — so device tests and ADB automation are
  repeatable. Use when an emulator will not boot or is unusably slow, when tests need a clean device,
  when several AVDs must run at once, or when CI needs a reproducible API level.
license: Apache-2.0
metadata:
  domain: device
  level: advanced
  sources:
    - android-adb-skill (android-device)
    - android-skill (android-cli, artemis)
    - awesome-android-agent-skills (android-emulator-skill)
    - mobile-agent-skillpack (mobile-ci-release-flow)
---

# Emulator Management

An emulator is a **stateful machine with a lock file, a snapshot and a GPU mode**. Most "emulator is
broken" is one of those three.

## Use when

- Creating an AVD for a specific API level/image.
- An AVD will not start, boots slowly, or shows a black/blank screen.
- Tests need a known-clean device state.
- Multiple devices must run in parallel (matrix tests, several flows).
- CI needs a reproducible managed device.

## Do not use when

- The task is driving the app on a device → `adb-automation`.
- Benchmarks are needed → `benchmark-testing` (emulators are invalid for those).
- The task is on a physical device only → `adb-automation`.
- Verifying a layout across window sizes on a device → `adaptive-layout`.

## Rules

1. **Hardware acceleration is mandatory.** On Linux, `/dev/kvm` must be accessible to the user
   (`ls -l /dev/kvm`, group membership). Without KVM, boot time goes from ~15 s to minutes and
   instrumented tests time out.
2. **Choose the image deliberately:** `google_apis` vs `google_apis_playstore` (the latter cannot be
   rooted but includes Play services), and `aosp` for a clean platform. API level must match the
   feature you test.
3. **GPU mode matters for UI tests.** `-gpu host` is fastest and may differ from real rendering;
   `-gpu swiftshader_indirect` is slow but deterministic/headless-safe. Pick per purpose and record it.
4. **Reset state per run, not per session.** `-wipe-data` (full reset) or `adb emu avd wipe-data`;
   `-no-snapshot-load` avoids resuming a corrupted snapshot. A "clean" device with a stale snapshot is
   not clean.
5. **Cold boot is a debugging tool, not the default.** `-no-snapshot` costs boot time; use it when a
   snapshot is suspected corrupt, then re-create a good snapshot.
6. **One AVD per purpose, named for it:** `pixel6_api34_aosp`, `pixel_tablet_api34`. Shared AVDs
   accumulate state and produce phantom failures.
7. **Parallelise by port, not by hope.** `-port 5554 -port 5556` (even ports); each AVD needs its own
   data dir. Two emulators started with the same port is the classic "device offline" loop.
8. **Kill cleanly, and clean the lock files.** `adb -s emulator-5554 emu kill`; a killed process leaves
   `*.lock` in the AVD directory and the next start fails with "AVD already running".
9. **In CI, prefer Gradle Managed Devices** over a hand-started emulator: they define the image,
   API level and lifecycle in the build script and clean up after themselves.
10. **Never trust emulator numbers for performance** (`benchmark-testing`), and never trust an emulator
    for biometrics/Bluetooth/camera hardware behaviour — use faked system state or a physical device.

## Procedure

1. List and verify:
   ```bash
   sdkmanager --list_installed | grep system-images
   avdmanager list avd
   ls -l /dev/kvm && groups | grep -o kvm
   emulator -list-avds
   ```
2. Create an AVD for the target image (or via Gradle Managed Devices in CI).
3. Start with explicit flags:
   ```bash
   emulator -avd pixel6_api34_aosp -no-snapshot-load -gpu swiftshader_indirect -no-audio -port 5554 &
   adb -s emulator-5554 wait-for-device
   adb -s emulator-5554 shell 'while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 1; done'
   ```
4. Reset per run (`-wipe-data` or managed devices).
5. Shut down with `emu kill`; verify no stale lock/processes (`pgrep -af qemu-system`).
6. For parallel runs, repeat with distinct ports and distinct `-datadir`.

## Checklist

- [ ] KVM accessible (Linux) / acceleration enabled.
- [ ] Image variant chosen deliberately (`google_apis` vs playstore vs aosp).
- [ ] GPU mode chosen for the purpose and recorded.
- [ ] State reset per run (`-wipe-data` / managed device).
- [ ] Snapshot use is intentional; `-no-snapshot-load` when suspect.
- [ ] One AVD per purpose, named.
- [ ] Parallel AVDs have unique ports and data dirs.
- [ ] Shutdown via `emu kill`; no stale locks or `qemu-system` processes.
- [ ] CI uses Gradle Managed Devices or equivalent reproducible setup.
- [ ] No performance conclusions drawn from emulators.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Minutes to boot | no KVM / wrong image | fix `/dev/kvm` access | 10–50x slower |
| "AVD already running" | start again | `emu kill`, remove stale lock | leftover process |
| Flaky UI tests | shared AVD with old state | `-wipe-data` per run | accumulated state |
| Black screen in CI | `-gpu host` on headless | `swiftshader_indirect` | no display |
| Port confusion | two AVDs same port | `-port 5554`, `-port 5556` | device offline loops |
| Phantom failures | resumed corrupted snapshot | `-no-snapshot` then re-save | snapshot rot |
| Trusted perf numbers | emulator benchmark | physical device | invalid |

## Verify

```bash
adb devices -l
adb -s emulator-5554 shell getprop sys.boot_completed   # 1
adb -s emulator-5554 shell getprop ro.build.version.sdk # expected API
adb -s emulator-5554 emu kill
pgrep -af "qemu-system" | wc -l                          # 0
```

Expected: boot completes, the SDK level matches the requested image, and shutting down leaves no
processes or lock files behind; a second identical run behaves the same.

## References

- `emulator -help-*` (gpu, snapshot, datadir), `avdmanager`, `sdkmanager`
- Gradle Managed Devices for CI
