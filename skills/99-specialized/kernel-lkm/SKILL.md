---
name: kernel-lkm
description: >-
  Build, load and debug an Android kernel module (LKM/KO) against a specific kernel tree, including
  vermagic/ABI constraints, GKI boundaries, kprobe hooks and crash triage. Use when writing a kernel
  module for an Android device you control, when insmod fails with a version or signature error, when a
  module oopses the device, or when deciding whether the work is possible on a GKI kernel at all.
license: Apache-2.0
metadata:
  domain: specialized
  level: specialized
  sources:
    - Yunnijian/android-kernel-lkm
    - yzddmr6/android-mainline-port
    - original
---

# Android Kernel Modules

A kernel module is **compiled against one exact kernel build**. There is no ABI compatibility story
across Android versions, and on GKI the answer to "can I write a module for this?" is often "not like
that".

## Use when

- Writing/debugging a module for a device you own and have root on.
- `insmod` fails: `Unknown symbol`, `invalid module format`, `version magic … should be …`.
- A module loads then oopses (`dmesg` shows a trace, device reboots).
- Deciding whether a hook/trace is possible on a GKI kernel or requires a vendor path.

## Do not use when

- The problem is userspace (ADB, app behaviour) → `adb-automation` / `bug-fix`.
- The goal is porting a whole kernel/OS → `mainline-port`.
- You do not have the device's kernel source or the ability to flash a signed boot image — then the
  module route is blocked; say so instead of proceeding.

## Rules

1. **Get the exact kernel tree first: version, `CONFIG_LOCALVERSION`, and the compiler used.** A module
   built from "a similar tree" fails with vermagic or crashes on load. Sources: the vendor's kernel
   release, the GKI `android*` branch, or the device's `/proc/version` + `/proc/config.gz` for reference.
2. **`vermagic` must match exactly** (`uname -r`, vermagic string, `MODULE_VERMAGIC_*` flags). Mismatch is
   the most common failure and is not fixable by editing the string if module signature/CRC checks are on.
3. **`CONFIG_MODVERSIONS` means symbols carry CRCs.** A module built against a different config fails with
   a CRC mismatch, not a clean error. Verify config parity before debugging code.
4. **On GKI, do not modify core kernel ABI.** GKI provides a stable symbol list for vendor modules
   (`Module.symvers` from the GKI build); any symbol not exported is unavailable. Hooking a core function
   requires `kprobe`/`kretprobe`/ftrace, not a patch — and some configurations disable kprobes.
5. **Module signing/verification may reject your KO.** `CONFIG_MODULE_SIG_FORCE` / Android's
   verified-boot chain can refuse unsigned modules. Confirm whether the target allows unsigned modules and
   whether unlocking/changing `vbmeta` is required (which itself may be out of scope).
6. **Never assume the API. Read the headers of *that* tree.** Kernel internal APIs change between
   versions with no compatibility layer (`file_operations` fields, `proc_ops` vs `file_operations`,
   `class_create` signature, `copy_from_user` variants). Compile errors from a copied snippet are the
   expected outcome of using another version's example.
7. **`obj-m` + Kbuild, cross-compiled with the device's toolchain and `ARCH=arm64`.** Out-of-tree builds
   must point `-C` at the exact kernel tree (`make -C <kernel> M=$PWD modules`), and the produced `.ko`
   must match the kernel's `ARCH`/`CROSS_COMPILE`.
8. **Hooks must be minimal and reversible.** A `kprobe` handler runs in kernel context on a hot path:
   no sleeping, no allocations without `GFP_ATOMIC`, no user-memory access without the proper helpers,
   and always unregister in module exit.
9. **A kernel bug takes the whole device.** Develop on a device you can reflash, keep a working boot image
   and a recovery path, and prefer testing in a VM/emulator kernel when the hook logic allows.
10. **Triage with `dmesg`, not guesses.** An oops reports the faulting address, the module and the call
    trace; read the first line and the module name. Panics on load are usually an init-order or
    wrong-structure-layout issue, i.e. mixing headers from another tree.
11. **Report the constraints you found.** "Works on kernel X built from Y with config Z, and requires
    root + unlocked bootloader" is the deliverable; a `.ko` without that context is unusable.

## Procedure

1. Record the target: `/proc/version`, `uname -r`, `cat /proc/config.gz | zcat | head` (if available),
   bootloader state, SELinux mode, whether modules are allowed at all.
2. Obtain the exact tree/toolchain; build a trivial module first (`hello world`) and load it — proving the
   pipeline before writing logic.
3. Implement the module with `obj-m`, cross-compile, and compare `modinfo <ko>` vermagic to `uname -r`.
4. Load with `insmod`, watch `dmesg -w`; on failure read the first error line (symbol vs vermagic vs sig).
5. Add the real logic; test one hook at a time, unloading between attempts.
6. For a crash: capture the oops, map the faulting address to your module with `faddr2line`/`addr2line`
   against the module's vmlinux symbols, and check for struct-layout mismatch first.
7. Write down kernel version, config, signing state and the reflash/recovery procedure used.

## Checklist

- [ ] Exact kernel tree/version/toolchain identified and recorded.
- [ ] Trivial module builds and loads (pipeline proven).
- [ ] `modinfo` vermagic matches `uname -r`; config/`MODVERSIONS` parity checked.
- [ ] GKI constraints respected (exported symbols only; kprobe instead of patching core).
- [ ] Module signing requirement determined; unsigned-load path confirmed or blocked.
- [ ] APIs taken from the target tree's headers, not from examples for another version.
- [ ] Hooks are atomic-safe, minimal, and unregistered on exit.
- [ ] Reflash/recovery path available before loading a module that can panic.
- [ ] Constraints (root, unlocked bootloader, kernel version) written into the deliverable.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| `invalid module format` | edit vermagic string | rebuild against the exact tree | CRC/signature checks |
| `Unknown symbol` | assume the symbol exists | use the GKI `Module.symvers` list or kprobe | not exported |
| Oops on load | debug logic | check struct layout/headers version | ABI mismatch |
| Module allowed then rejected | ignore signing | determine `MODULE_SIG_FORCE`/vbmeta | verified boot |
| Dead device | load untested module on daily driver | reflashable test device | panic = brick |
| Copied snippet fails | "the API changed?" | read that tree's headers | kernel APIs drift |

## Verify

```bash
make -C <kernel-tree> M=$PWD ARCH=arm64 CROSS_COMPILE=aarch64-linux-android- modules
modinfo ./hello.ko | grep vermagic
adb push hello.ko /data/local/tmp/ && adb shell "su -c 'insmod /data/local/tmp/hello.ko'"
adb shell "su -c 'dmesg | tail -20'"
adb shell "su -c 'rmmod hello'"
```

Expected: `modinfo` vermagic equals `uname -r`, `insmod` succeeds, `dmesg` shows the module's init message,
and `rmmod` unloads cleanly with no trace in `dmesg`.

## References

- Kernel `Documentation/kbuild/modules.rst`; `kprobe`/`kretprobe` and ftrace docs from **your** kernel tree
- GKI module ABI/symbol list for the target release
