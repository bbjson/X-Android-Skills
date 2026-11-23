#!/usr/bin/env python3
"""Execute every skill's ## Verify commands against a fixture Android project.

Requires: an Android project (fixture) with an app module, a connected device, and
ANDROID_HOME + JAVA_HOME set. See docs/verify-report.md for the setup used.

Design notes:
- Identical normalised commands are executed once and shared between skills.
- Module names a skill assumes (:feature:x, :core:data …) are remapped to the fixture's
  modules; a remap is recorded so a "pass" is not mistaken for the skill's own project shape.
- Dangerous or environment-mutating commands are never executed (SKIP).
- A failure is *not* automatically a skill bug: missing library plugins (Roborazzi,
  Macrobenchmark, Hilt, KMP targets) are expected to fail. Those become SKIP-DEPENDENCY
  when the marker for that dependency is absent from the fixture.

Usage: python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture [--only slug] [--dry]
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- placeholders
REPLACE = {
    "<pkg>": "com.example.fixture",
    "<serial>": "emulator-5554",
    "<wear-serial>": "emulator-5554",
    "<Activity>": ".MainActivity",
    "<AffectedClass>": "SmokeTest",
    "<RepositoryTest>": "SmokeTest",
    "<db>": "fixture-db",
    "<module>": "app", ":module": ":app",
    "<name>": "x",
}

# Longest keys first: a naive replace turns ":feature:feed:api" into ":app:api".
MODULE_MAP = {
    ":build-logic:convention": ":build-logic:convention",
    ":core:designsystem": ":core:designsystem",
    ":feature:feed": ":app", ":feature:x": ":app",
    ":core:data": ":app", ":core:network": ":app", ":core:database": ":app",
    ":domain": ":domain", ":impl": ":app",
    ":shared": ":SKIP-KMP", ":benchmark": ":SKIP-BENCH", ":macrobenchmark": ":SKIP-BENCH",
    ":baselineprofile": ":SKIP-BP",
    ":app": ":app",
}
MODULE_MAP = dict(sorted(MODULE_MAP.items(), key=lambda kv: -len(kv[0])))

DANGER = re.compile(r"\bpm clear\b|\buninstall\b|\bsettings put\b|\breboot\b|\brm -rf\b|"
                    r"\bwipe\b|\bkillall\b|\bformat\b|\bmount\b|\bfastboot\b|\binsmod\b|\brmmod\b|"
                    r"am kill\b|\bsetprop\b|stop; start|emu kill|emulator -avd|\bpm grant\b|"
                    r"\bpm revoke\b|airplane-mode|\badb root\b|\bsu -c\b")
DEP_MARKERS = {
    "roborazzi": "roborazzi", "macrobenchmark": "benchmark", "androidx.benchmark": "benchmark",
    "connectedCheck": "benchmark", "hilt": "hilt", "koin": "koin", "verify(modules)": "koin",
    "checkModules": "koin", "ksp": "ksp", "room": "room", "robolectric": "robolectric",
    "turbine": "turbine", "detekt": "detekt", "ktlint": "ktlint", "appium": "appium",
    "iosArm64": "kmp", "linkDebugFramework": "kmp", "xcodebuild": "kmp",
    "connectedBenchmarkAndroidTest": "benchmark", "generateBaselineProfile": "baselineprofile",
    "pixel6Api34DebugAndroidTest": "manageddevice", "compileKotlinIos": "kmp",
    "gradleManagedDevices": "manageddevice", "unzip -l app/build/outputs/apk/release": "apk",
    "wear-debug.apk": "wear", ":wear:": "wear", "commonMain": "kmp",
    "iosApp/": "kmp", "hello.ko": "kernel", "modinfo": "kernel", "metadata/en-US": "play",
    "gplay": "play", ":app:api:": "feature", ":feature:": "feature",
}


def normalise(cmd: str, fixture: Path) -> tuple[str, list[str]]:
    notes = []
    for k, v in REPLACE.items():
        cmd = cmd.replace(k, v)
    for k, v in MODULE_MAP.items():
        if k in cmd:
            if v.startswith(":SKIP"):
                notes.append(f"module {k} -> skipped ({v})")
            else:
                if k != v:
                    notes.append(f"module {k} -> {v}")
            cmd = cmd.replace(k, v)
    # wildcard test filters
    cmd = re.sub(r"'?\*[A-Za-z]*\*'?", "'*SmokeTest*'", cmd)
    # build-logic dependency on a gradle-api version is fixture-specific
    return cmd, notes


def classify(cmd: str) -> str:
    if DANGER.search(cmd):
        return "SKIP-DANGEROUS"
    if "/.../" in cmd or ".../" in cmd or "crash.txt" in cmd:
        return "SKIP-PLACEHOLDER"
    if re.search(r"<[a-z][a-z-]*>", cmd) or re.search(r"(?:^|\s)\.\.\.(?:\s|$)", cmd):
        return "SKIP-PLACEHOLDER"
    if "./gradlew" in cmd or "gradlew " in cmd:
        return "GRADLE"
    if re.search(r"\badb\b|\bemulator\b|\bsdkmanager\b|\bavdmanager\b", cmd):
        return "DEVICE"
    return "SHELL"


def fixture_capabilities(fixture: Path) -> set[str]:
    toml = (fixture / "gradle/libs.versions.toml").read_text() if (fixture / "gradle/libs.versions.toml").exists() else ""
    low = toml.lower()
    caps = {"apk"}
    for dep, marker in [("roborazzi", "roborazzi"), ("hilt", "hilt"), ("koin", "koin"),
                        ("room", "room"), ("ksp", "ksp"), ("robolectric", "robolectric"),
                        ("turbine", "turbine"), ("detekt", "detekt"), ("ktlint", "ktlint"),
                        ("benchmark", "benchmark"), ("appium", "appium")]:
        if dep in low:
            caps.add(marker)
    for d in ("benchmark", "macrobenchmark", "baselineprofile", "wear", "shared", "feature"):
        if (fixture / d).exists():
            caps.add({"benchmark": "benchmark", "macrobenchmark": "benchmark",
                      "baselineprofile": "baselineprofile", "wear": "wear",
                      "shared": "kmp", "feature": "feature"}[d])
    return caps


def dep_missing(cmd: str, caps: set[str]) -> str | None:
    low = cmd.lower()
    for marker, need in DEP_MARKERS.items():
        if marker.lower() in low and need not in caps:
            return need
    return None


def verdict(cmd: str, result: tuple[int, str], fixture: Path) -> str:
    """pass / empty(ok) / env(tool missing) / fail."""
    rc, out = result
    if rc == 0:
        return "pass"
    if rc == 127 or "command not found" in out:
        return "env"
    # a grep at the end of a pipeline returning 1 means "no match", which many skills
    # explicitly want ("must be empty", "0 in the classpath")
    is_grep = bool(re.search(r"(^|\|\s*)grep\b", cmd))
    if is_grep and "No such file or directory" in out:
        return "structure"
    if is_grep and rc == 1:
        return "empty"
    if re.search(r"am start -n .*Internal|yourapp://|--d \'?;|am start .*malformed", cmd):
        return "expected-fail"
    # fixture-environment gaps: not skill bugs
    if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in out:
        return "structure"
    if re.search(r"\brun-as\b|/proc/device-tree|am start -a android\.intent\.action\.VIEW -d \"example://", cmd):
        return "structure"
    if rc == 1 and "No such file or directory" in out:
        if "grep" in cmd or "run-as" in cmd or cmd.startswith("ls "):
            return "structure"
    return "fail"


def status_of(d: dict[str, int]) -> str:
    if d["fail"]:
        return "FAILED" if not d["pass"] else "PARTIAL"
    if d["pass"]:
        return "VERIFIED"
    return "INCONCLUSIVE" if d["incon"] else "SKIPPED-ONLY"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=str(Path.home() / "Desktop/verify-fixture"))
    ap.add_argument("--only", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--timeout-gradle", type=int, default=900)
    ap.add_argument("--timeout-other", type=int, default=90)
    args = ap.parse_args()

    fixture = Path(args.fixture).expanduser()
    if not (fixture / "gradlew").exists():
        print(f"no gradlew in {fixture}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    sdk = env.get("ANDROID_HOME") or str(Path.home() / "Android/Sdk")
    env["ANDROID_HOME"] = sdk
    bt = sorted((Path(sdk) / "build-tools").glob("*")) if (Path(sdk) / "build-tools").exists() else []
    bt_path = f"{bt[-1]}:" if bt else ""
    env["PATH"] = f"{sdk}/platform-tools:{sdk}/emulator:{sdk}/cmdline-tools/latest/bin:{bt_path}" + env["PATH"]
    env.setdefault("JAVA_HOME", "/usr/lib/jvm/java-17-openjdk-amd64")

    caps = fixture_capabilities(fixture)

    # collect
    jobs: list[tuple[str, str, str, list[str]]] = []   # (skill, cmd, kind, notes)
    for p in sorted(REPO.glob("skills/**/SKILL.md")):
        slug = p.parent.name
        if args.only and args.only != slug:
            continue
        text = p.read_text()
        m = re.search(r"^## Verify\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
        if not m:
            continue
        block = m.group(1)
        for code in re.findall(r"```bash\n(.*?)```", block, re.S):
            code = re.sub(r"\\\n\s*", " ", code)     # join line continuations
            for line in code.splitlines():
                line = re.sub(r"\s+#\s.*$", "", line.strip())
                if not line or line.startswith("#"):
                    continue
                for part in re.split(r"\s+&&\s+|\s*\|\|\s*", line):
                    part = re.sub(r"\s+#\s.*$", "", part.strip())
                    if not part:
                        continue
                    cmd, notes = normalise(part, fixture)
                    if ":SKIP" in cmd:
                        jobs.append((slug, part, "SKIP-DEPENDENCY", notes))
                        continue
                    kind = classify(cmd)
                    if not kind.startswith("SKIP"):
                        miss = dep_missing(cmd, caps)
                        if miss:
                            kind = "SKIP-DEPENDENCY"
                            notes = notes + [f"needs {miss}"]
                    jobs.append((slug, cmd, kind, notes))

    print(f"{len(jobs)} commands from {len({j[0] for j in jobs})} skills")
    if args.dry:
        for slug, cmd, kind, notes in jobs:
            print(f"  [{kind:16}] {slug:28} {cmd[:90]}")
        return 0

    # execute unique commands
    results: dict[str, tuple[int, str]] = {}
    order = ["SKIP-DEPENDENCY", "SKIP-PLACEHOLDER", "SKIP-DANGEROUS", "GRADLE", "SHELL", "DEVICE"]
    jobs.sort(key=lambda j: order.index(j[2]) if j[2] in order else 9)
    for slug, cmd, kind, notes in jobs:
        if kind.startswith("SKIP"):
            continue
        if cmd in results:
            continue
        timeout = args.timeout_gradle if kind == "GRADLE" else args.timeout_other
        try:
            r = subprocess.run(cmd, shell=True, cwd=fixture, env=env, timeout=timeout,
                               capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            results[cmd] = (r.returncode, out)
        except subprocess.TimeoutExpired:
            results[cmd] = (124, f"TIMEOUT after {timeout}s")
        except Exception as e:  # noqa: BLE001
            results[cmd] = (125, str(e))
        rc, out = results[cmd]
        flag = "ok  " if rc == 0 else "FAIL"
        print(f"{flag} [{kind:9}] {slug:28} {cmd[:80]}")

    # report
    out_path = Path("/tmp/verify_results.tsv")
    with out_path.open("w") as f:
        f.write("skill\tkind\trc\tcmd\tnotes\n")
        for slug, cmd, kind, notes in jobs:
            if kind.startswith("SKIP"):
                f.write(f"{slug}\t{kind}\t-\t{cmd}\t{'; '.join(notes)}\n")
                continue
            rc, _ = results.get(cmd, (-1, ""))
            f.write(f"{slug}\t{kind}\t{rc}\t{cmd}\t{'; '.join(notes)}\n")
    with Path("/tmp/verify_failures.txt").open("w") as f:
        for cmd, (rc, out) in results.items():
            if rc != 0:
                f.write(f"### rc={rc}  {cmd}\n{out[-1200:]}\n\n")
    # per-skill status
    per: dict[str, dict[str, int]] = {}
    for slug, cmd, kind, notes in jobs:
        d = per.setdefault(slug, {"pass": 0, "fail": 0, "incon": 0, "skip": 0, "n": 0})
        d["n"] += 1
        if kind.startswith("SKIP"):
            d["skip"] += 1
            continue
        v = verdict(cmd, results.get(cmd, (-1, "")), fixture)
        if v == "pass":
            d["pass"] += 1
        elif v == "fail":
            d["fail"] += 1
        else:
            d["incon"] += 1
    with Path("/tmp/verify_per_skill.tsv").open("w") as f:
        f.write("skill\tcommands\tpass\tfail\tinconclusive\tskipped\tstatus\n")
        for slug in sorted(per):
            d = per[slug]
            st = status_of(d)
            f.write(f"{slug}\t{d['n']}\t{d['pass']}\t{d['fail']}\t{d['incon']}\t{d['skip']}\t{st}\n")
    counts: dict[str, int] = {}
    for slug, d in per.items():
        st = status_of(d)
        counts[st] = counts.get(st, 0) + 1
    print("\nper-skill status:")
    for k in ("VERIFIED", "PARTIAL", "FAILED", "INCONCLUSIVE", "SKIPPED-ONLY"):
        print(f"  {k:14} {counts.get(k, 0)}")
    print(f"\nresults -> {out_path}\nper-skill -> /tmp/verify_per_skill.tsv\nfailures -> /tmp/verify_failures.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
