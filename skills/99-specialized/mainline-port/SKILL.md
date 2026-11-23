---
name: mainline-port
description: >-
  Plan and execute a port of mainline Linux to an Android device: identifying SoC support, adapting
  device tree, boot image and partition constraints, and staging bring-up from initramfs to display,
  touch and power. Use when porting Linux to a phone/tablet, when a device tree must be written or fixed,
  when the boot chain (vbmeta/A-B/dynamic partitions) blocks a non-Android image, or when deciding whether
  a device is worth porting.
license: Apache-2.0
metadata:
  domain: specialized
  level: specialized
  sources:
    - yzddmr6/android-mainline-port
    - Yunnijian/android-kernel-lkm (kernel-side constraints)
    - original
---

# Mainline Linux Port

A port is a **staged bring-up with a bootable checkpoint at every step**. Work that is not bootable at
step N cannot be debugged at step N+1.

## Use when

- Porting mainline Linux (or another OS) to an Android phone/tablet.
- Writing/fixing a device tree for a device whose vendor tree exists but mainline does not.
- Boot chain problems: unlocked bootloader, `vbmeta`, A/B slots, dynamic partitions (`super`).
- Deciding whether a device is a viable port candidate.

## Do not use when

- The goal is a kernel module on the stock kernel → `kernel-lkm`.
- The goal is Android app/OS behaviour → other skills.
- You have no unlockable bootloader and no test device — the port is blocked at step 0.

## Rules

1. **Pick the device by SoC support in mainline, not by popularity.** Check whether the SoC has a
   mainline platform (clock, pinctrl, PMIC, display) and whether *any* device on it boots mainline. A
   device whose SoC has no mainline support is a multi-month project, not a port.
2. **Find the vendor device tree first; derive, do not invent.** The downstream DTS (from the vendor
   kernel fork) gives memory map, GPIOs, regulators, panel and touch wiring. Without it you are
   guessing; with it you are translating.
3. **Stage the bring-up, and stop at each gate:**
   (1) bootloader unlocks and accepts a custom boot image;
   (2) kernel boots to an initramfs with serial/`pstore` output;
   (3) storage (`UFS`/`eMMC`) mounts a rootfs;
   (4) display shows a console;
   (5) touch input works;
   (6) Wi-Fi/USB networking;
       (7) power management (suspend/resume, thermal).
   Do not attempt (5) before (4), or (6) before (3).
4. **Get an early console before anything else.** A port without serial (or a working `pstore`/ramoops)
   is blind: every failure becomes guesswork, and a wrong regulator/pinctrl can damage hardware.
5. **Boot chain first, kernel second, userspace third.** Identify slot layout (`A/B`), `vbmeta`
   verification, and dynamic partitions before writing any DTS. Forcing a `boot.img` into a
   `super`-managed device or ignoring `vbmeta` produces a hard brick or a silent boot loop.
6. **Keep the stock image and a recovery path identified before flashing anything.** Note how to reach
   EDL/fastboot, and whether the device can be recovered without vendor tools.
7. **One change per boot test, and keep a boot log per change.** DTS edits are high-variance: a wrong
   `reg`/`interrupt`/`supply` yields a hang with no message, so isolating the change is the only way to
   learn.
8. **Do not guess numeric values.** Clock rates, regulator voltages, GPIO numbers and panel timings come
   from the vendor tree or datasheets. A guessed voltage can damage hardware; a guessed panel timing
   gives a black screen indistinguishable from a driver bug.
9. **Document what is unsupported.** Modem, cameras, fingerprint and sensors are commonly absent. A port
   report that omits these reads as "fully working" and misleads the next person.
10. **Licensing and redistribution: kernel GPL obligations apply to your DTS/driver patches.** Publish
    what you must, and keep vendor blobs out of the tree.

## Procedure

1. Research: SoC mainline status, existing device ports on that SoC, vendor kernel source and DTS
   availability, bootloader unlockability.
2. Establish the boot chain: unlock, identify slots/`vbmeta`, confirm a custom `boot.img` will boot
   (test with a trivial initramfs).
3. Build a minimal mainline kernel for the SoC with your device's DTS (translated from the vendor tree),
   plus an initramfs that prints to the console.
4. Verify gate (2) with a boot log; fix memory map/pinctrl/UART before anything else.
5. Add storage, then rootfs, then display, then input — one gate per boot test.
6. Add networking, then power management; measure suspend/resume.
7. Write the port report: gates reached, unsupported hardware, known bugs, how to reproduce the build.

## Checklist

- [ ] Device chosen on mainline SoC support, not popularity.
- [ ] Vendor DTS/kernel source located; values derived from it.
- [ ] Bootloader unlocked; slot layout, `vbmeta`, dynamic partitions understood.
- [ ] Recovery/EDL path identified before flashing.
- [ ] Early console (serial or ramoops) working.
- [ ] Minimal initramfs boots (gate 2) with a saved boot log.
- [ ] Only exported/vendor-documented values used for regulators, clocks, GPIOs, panel timings.
- [ ] One change per boot test, log kept.
- [ ] Unsupported hardware documented.
- [ ] Build steps and kernel branch/commit recorded for reproduction.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Unbootable device, no output | no console setup | serial/ramoops first | blindness |
| Brick | flash without knowing vbmeta/slots | map boot chain first | hard brick |
| Random hangs | many DTS changes at once | one change per boot | no attribution |
| Damaged hardware | guessed regulator voltage | vendor value from DTS | physical risk |
| "It's ported" | display works, no modem | state unsupported list | misleading |
| Multi-month surprise | port an unsupported SoC | check mainline first | wrong project |

## Verify

Each gate is verified by an artefact, not by memory:

```bash
# gate 2: kernel + initramfs
fastboot boot boot.img            # or flash per slot
# console output captured (serial cable / pstore)
ls /sys/firmware/devicetree/base/ | head    # after boot: DT actually applied
cat /proc/device-tree/model
```

Expected: at each gate, a boot log or shell response proves the gate; the DT model string matches the
device, and the port report lists exactly which gates were reached.

## References

- Mainline kernel `Documentation/devicetree/bindings/` for the SoC families involved
- postmarketOS / lk2nd / U-Boot device documentation for the same device family
