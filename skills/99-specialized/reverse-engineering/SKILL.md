---
name: reverse-engineering
description: >-
  Analyse an Android APK you are authorised to inspect: static structure, manifest and permissions,
  embedded secrets, third-party SDKs, then dynamic confirmation with hooks and traffic capture. Use when
  auditing your own app's release build, investigating a reported vulnerability in your app, analysing a
  protocol for interoperability, or documenting how a bundled SDK behaves.
license: Apache-2.0
metadata:
  domain: specialized
  level: specialized
  sources:
    - CreditTone-android-reverse-engineering-skill
    - android-reverse-engineering-skill
    - android-rea
    - masvs-audit
---

# Android Reverse Engineering

Static analysis produces **hypotheses**; only a runtime observation proves one.

## Use when

- Auditing your own release APK (what is actually shipped, what a decompiler sees).
- Investigating a vulnerability report against your app.
- Documenting a bundled third-party SDK's real behaviour.
- Understanding a protocol for a legitimate interoperability requirement.

## Do not use when

- You do not have authorisation for the app → **stop**. Analysing someone else's app or circumventing
  licensing/DRM is out of scope and may be illegal in your jurisdiction.
- The goal is a security audit of *your* app → `masvs-audit` (broader control coverage).
- The question is about an exported component → `component-exposure`.

## Rules

1. **Authorisation is the first artefact.** Write down who owns the app, what you may do (static,
   dynamic, network interception), and what is excluded. Without it, stop.
2. **Static first, and exhaust it before running anything.** `apktool` for manifest/resources/smali,
   `jadx` for Java-level reading, `aapt2 dump` for the exact manifest. Runtime work on an unread
   binary is guesswork.
3. **Every static finding is a hypothesis until reproduced.** A hardcoded string may be unused; an
   exported component may be guarded at runtime. Mark `static` vs `dynamic-proven` per finding.
4. **`jadx` output is not source.** Inlined lambdas, synthetic classes and renamed identifiers make
   control flow misleading; verify a security-relevant path in smali or at runtime before reporting it.
5. **Read the manifest before the code.** Exported components, permissions, `allowBackup`,
   `usesCleartextTraffic`, `debuggable`, backup rules, and intent filters tell you the attack surface
   more cheaply than any decompilation.
6. **Secrets: distinguish identifier from secret.** Anything in the APK is readable by anyone. An API key
   in `BuildConfig`/resources is public by definition; a signing key or private key is a genuine
   finding. Classify before ranking.
7. **Dynamic confirmation needs a device you control, and a build you may instrument.** Frida/objection
   hooks on a `debuggable` or root image; traffic capture with a proxy on a test account. Never on a
   production account holding real user data.
8. **Packed/protected apps are a different workflow.** DEX packing, native integrity checks and
   anti-debugging mean static tools see a stub. Attempting to defeat protection is a legal/scope question
   first, a technical one second.
9. **Capture evidence per finding:** tool, command, offset/class/method, observed output. "The app is
   insecure" is not a finding.
10. **Report by impact, and include what you could not determine.** Unknowns (obfuscated native code,
    server-side behaviour) matter to the reader more than a false-positive list.
11. **Do not redistribute decompiled code or extracted assets.** Quote the minimum needed to support a
    finding.

## Procedure

1. Write the authorisation/scope note.
2. Static pass:
   ```bash
   apktool d -f app.apk -o /tmp/apk
   aapt2 dump xmltree app.apk --file AndroidManifest.xml | head -80
   aapt2 dump permissions app.apk
   jadx -d /tmp/src app.apk
   grep -rniE "api[_-]?key|secret|token|password|http://" /tmp/apk/res /tmp/apk/assets /tmp/src 2>/dev/null | head -40
   ```
3. Map third-party SDKs: package prefixes + `libs/*.so` names; each is a behaviour you inherit.
4. Pick the 2–3 findings worth confirming; design the runtime observation for each.
5. Confirm with a controlled device (hook/дebug build/proxy) and record the output.
6. Write findings: id, severity, static/dynamic, evidence, impact, recommendation.
7. List what remains unknown and why.

## Checklist

- [ ] Authorisation and scope recorded.
- [ ] Manifest surface read (exported, permissions, cleartext, backup, debuggable).
- [ ] Static findings labelled as hypotheses.
- [ ] Secrets classified (identifier vs real secret).
- [ ] Third-party SDKs enumerated.
- [ ] Security-relevant paths confirmed dynamically where claimed.
- [ ] Each finding has tool + command + evidence.
- [ ] Unknowns listed explicitly.
- [ ] No decompiled code or assets redistributed.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Illegal analysis | "public APK, so fair game" | written authorisation | legal risk |
| Unverified claim | report a `jadx` string | reproduce at runtime | false positive |
| Secret mis-ranked | flag analytics key as critical | classify first | credibility |
| Tool dump as report | paste jadx output | findings with evidence | unactionable |
| Packed app misread | trust the stub | note the protection | wrong conclusion |
| Unknowns omitted | imply full coverage | list unknowns | misleading |

## Verify

A finding is reportable when: the command that produced it is in the document, the output is quoted, and
(if claimed as exploitable) a runtime observation confirms it. Re-running the documented commands on the
same APK reproduces the same output.

Expected: each finding carries its command, its output, and a static-vs-dynamic label; rerunning the commands reproduces the same output.

## References

- `apktool`, `jadx`, `aapt2`, `frida`, `objection`, `mitmproxy` — tool docs
- `masvs-audit` for control-based auditing of your own app
