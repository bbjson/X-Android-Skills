---
name: app-hardening
description: >-
  Add tamper and abuse resistance that survives Play re-signing: integrity verdicts, installer and
  debuggable checks, secret placement, and a failure policy that does not brick honest users. Use
  when shipping a paid, gated or high-value feature, when a build must detect repackaging or
  instrumentation, when deciding what belongs on the client versus the server, or when hardening
  breaks the Play-signed build.
license: Apache-2.0
metadata:
  domain: security
  level: advanced
  sources:
    - android-developers (Play Integrity, app security best practices, re-expressed)
    - this-repo (gap analysis: only audit workflow existed, no implementation skill)
---

# App Hardening

One decision: **what the server is willing to believe, and what the client does when it is
disbelieved.** Every client-side check is a hint to the server; none of them is a boundary.

## Use when

- A paid tier, entitlement, anti-abuse rule or account action depends on "is this the real app".
- A build must resist repackaging, instrumentation or a rooted/debuggable environment.
- Deciding where an API key, secret or gating rule lives.
- Hardening code broke the Play-signed build, or blocks honest users on some devices.
- Reviewing whether a "security" check is actually protecting anything.

## Do not use when

- Storing keys, tokens or files safely on device → `keystore-and-crypto`.
- Inbound surface: exported components, intents, WebView bridges → `component-exposure`.
- Running the audit itself and writing findings → `masvs-audit`.
- Reading an APK to see what is exposed → `reverse-engineering`.

## Rules

1. **Every client check is advisory; the server decides.** The client reports evidence (integrity
   token, signature digest, install source) and the server enforces the entitlement. A local
   `if (isGenuine) unlock()` is a string patch away from free.
2. **Use Play Integrity verdicts, not a hand-rolled root check, as the primary signal.** Request a
   token, verify it server-side, and act on the verdict fields (device integrity, app recognition,
   licensing) separately — they answer different questions.
3. **Do not compare the on-device signing certificate against your local keystore when Play App
   Signing is enabled.** Google re-signs uploads; compare against the certificate Play uses (from the
   console) or rely on the integrity verdict, otherwise every production install looks tampered.
4. **Verify signatures from `getSigningCertificates`/`GET_SIGNING_CERTIFICATES`, and hash the
   certificate, not the APK** — the APK digest changes with every build, the signer does not.
5. **Check `FLAG_DEBUGGABLE` and the installer, and treat both as signals with false positives.**
   Sideloaded testers, enterprise distribution and some vendor stores produce "unexpected installer"
   without malice.
6. **Root, emulator and hooking detection are cost, not proof.** They are bypassed by anyone who
   cares and fire on legitimate power users; never use them to deny access to data the user already
   owns. Use them to raise friction on abuse-sensitive actions and report to the server.
7. **Secrets never ship in the client**, in `BuildConfig`, in resources, in `strings` of a native
   library, or in an obfuscated string table. If it must be on device, it is public; move the
   authorised operation to the server.
8. **Instrumentation detection (debugger, injected agent, hooking framework) is a report, not a
   crash.** Crashing on detection hands an attacker a one-line DoS against real users.
9. **Obfuscation (R8) is the baseline; string encryption and packers buy little and cost startup,
   size and crash symbolication.** Keep the mapping, and never let a packer prevent Play from
   scanning or the mapping from being uploaded (`crash-reporting`).
10. **The failure policy is explicit per feature:** fail-open with a server report, fail-closed with
    a retry, or degrade to a limited experience. Choose in writing, implement exactly that, and log
    which branch fired.
11. **Hardening must not break accessibility, older API levels, or non-Play installs the product
    actually supports.** Test the release build on a low-end device, an emulator, and a
    Play-internal-track install before shipping the check.

## Procedure

1. List the assets worth protecting and who can legitimately reach them.
2. For each, decide the server-side enforcement point; the client only supplies evidence.
3. Integrate the integrity request; send the token to your backend on the sensitive action.
4. Add local checks (debuggable, installer, signer) as telemetry, not as gates.
5. Define and implement the failure policy per feature; log the branch.
6. Test: debug build, Play internal-track build, sideloaded build, emulator.

## Checklist

- [ ] Each protected asset has a server-side enforcement point.
- [ ] Integrity verdict verified server-side, fields interpreted separately.
- [ ] Signature comparison uses Play's certificate, not the local keystore.
- [ ] Certificate digest hashed, not the APK.
- [ ] Root/emulator/hook checks treated as telemetry, never as a hard gate.
- [ ] No secret in `BuildConfig`, resources, native strings or asset files.
- [ ] Detection paths report; they do not crash the app.
- [ ] R8 enabled, mapping retained and uploaded.
- [ ] Failure policy written per feature and logged.
- [ ] Release tested on device, emulator, sideload and Play track install.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Every prod install "tampered" | compare to local keystore | Play cert / integrity verdict | Play re-signs the app |
| Free premium tier | local `isGenuine` gate | server checks token | patchable in minutes |
| Real users locked out | `finish()` on root detection | telemetry + server policy | false positives, one-line DoS |
| Key in the APK | `buildConfigField` secret | server-side call | public by definition |
| Crash on debugger attach | crash on detection | report and continue | attacker controls the trigger |
| Startup regression | string-encryption packer | R8 + keep mapping | CPU and size cost |

## Verify

```bash
./gradlew :app:assembleRelease
# confirm the release APK is not debuggable and is signed by the expected certificate
$ANDROID_HOME/build-tools/$(ls $ANDROID_HOME/build-tools | tail -1)/apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
adb -s <serial> shell dumpsys package <pkg> | grep -E 'pkgFlags|installerPackageName'
grep -rn "BuildConfig\..*KEY\|SECRET" --include=*.kt app core domain | wc -l   # expected: 0
```

Expected: the release APK verifies against the certificate Play uses, is not debuggable, the
installer is reported for a Play install, and no secret literal is found in client code.

## References

- Play Integrity API verdicts and server-side verification
- `PackageManager.GET_SIGNING_CERTIFICATES`, `ApplicationInfo.FLAG_DEBUGGABLE`,
  `InstallSourceInfo`
- `apksigner verify --print-certs`
