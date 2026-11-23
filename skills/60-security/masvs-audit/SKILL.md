---
name: masvs-audit
description: >-
  Run a structured mobile security audit against MASVS categories and produce findings with evidence
  instead of a scanner dump. Use when auditing an app before release, responding to a security review,
  triaging a scanner report, deciding which hardening work matters, or verifying that a mitigation
  actually closed a finding.
license: Apache-2.0
metadata:
  domain: security
  level: specialized
  sources:
    - android-skill (android-security-review)
    - android-agent-engineering (android-security)
    - mobile-agent-skillpack (security-best-practices, security-threat-model)
    - phone-spyware-check (evidence-first framing)
---

# MASVS Audit

An audit is **a table of controls, each with evidence and a verdict**. "We ran MobSF and it looked
okay" is not an audit; it is a tool invocation.

## Use when

- Pre-release security review, or a customer/partner security questionnaire.
- Triaging a scanner (MobSF/OSTIG/nowsecure) report into real findings.
- Deciding where to spend hardening effort.
- Verifying a fix actually closed a finding (re-test, not "we changed the code").

## Do not use when

- The subject is one specific control (storage, exposure) → `keystore-and-crypto` /
  `component-exposure` / `network-dto-safety`.
- The request is a penetration test with active exploitation — that needs an authorised tester and a
  scope document, not a skill.
- The app is not yours — do not test it.

## Rules

1. **Scope first, in writing.** Which app variant, which version code, which accounts, which
   environment, what is out of scope (backend, social engineering, physical). An unbounded audit
   produces unbounded findings.
2. **Every finding needs reproducible evidence:** command + output, file + line, or steps + screen.
   "Insecure crypto possible" without a location is noise that will be argued about and dropped.
3. **Organise by MASVS category**, and cover all of them even if the answer is "not applicable,
   because …". Missing categories read as "not checked".
   - **STORAGE** — secrets at rest, backups, logs, external storage, clipboard.
   - **CRYPTO** — key management, modes, IVs, randomness, pinning.
   - **AUTH** — session lifetime, re-auth on sensitive actions, biometric binding, logout.
   - **NETWORK** — cleartext, TLS config, certificate validation, pinning + backup pins.
   - **PLATFORM** — exported components, intents, WebView, deep links, permissions.
   - **CODE** — hardening, debuggability, tamper checks, obfuscation of *secrets* (not code).
   - **RESILIENCE** — root/debugger detection is *not* a security control; treat as friction only.
   - **PRIVACY** — collected data vs Data Safety declaration (`data-safety-compliance`).
4. **Severity by impact × exploitability, not by scanner label.** A hardcoded analytics key is not the
   same as a hardcoded signing key. Write both, rank them.
5. **Static and dynamic evidence are different claims.** `jadx`/`apktool` show what could happen at
   runtime; only an actual run (logcat, traffic, `adb shell`) proves it does. Mark which you have.
6. **Hardening is not security.** Obfuscation, root detection and anti-debugging raise attacker cost
   and break nothing real; they never substitute for a control in STORAGE/PLATFORM.
7. **Assume the APK is public.** Anything in `BuildConfig`, resources, or strings is readable with
   `strings`/`apktool` — an "API key" there is an identifier, not a secret.
8. **Re-test closed findings with the same evidence method.** A finding is closed when the original
   reproduction no longer works, not when the code changed.
9. **Record residual risk explicitly.** Leaving a finding open is a decision, and it needs an owner and
   a date. Silent acceptance is how a known issue ships for years.
10. **Never claim "secure".** Claim a verdict per control, with the evidence and the date. The app is a
    moving target; the audit is a snapshot.

## Procedure

1. Write the scope document.
2. Static surface:
   ```bash
   apktool d -f app-release.apk -o /tmp/apk
   grep -rn "https\?://\|api[_-]key\|secret\|password" /tmp/apk/res /tmp/apk/assets /tmp/apk/smali 2>/dev/null | head -40
   aapt2 dump xmltree app-release.apk --file AndroidManifest.xml | grep -E "exported|permission|cleartext"
   jadx -d /tmp/src app-release.apk      # when source-level reasoning is needed
   ```
3. Storage/crypto: `adb shell run-as <pkg> ls -R .` on a rooted/`debuggable` test build; check
   `shared_prefs`, `databases`, files for tokens.
4. Network: `adb shell settings get global http_proxy`; capture with mitmproxy on a test build and
   confirm which endpoints reject invalid certs / whether pinning exists.
5. Platform: `dumpsys package` exported components; try starting internals (`component-exposure`).
6. Fill the control table with evidence and verdict per category.
7. Rank findings, assign owner/date, then re-test after fixes.

## Checklist

- [ ] Scope documented (variant, version, accounts, environment, exclusions).
- [ ] All eight MASVS categories covered, including "not applicable, because …".
- [ ] Every finding has reproducible evidence (command/output or steps).
- [ ] Findings marked static-only or dynamic-proven.
- [ ] Severity by impact × exploitability, with secrets ranked above identifiers.
- [ ] Hardening claims separated from access-control claims.
- [ ] Residual risks have an owner and a date.
- [ ] Closed findings re-tested with the original method.
- [ ] Privacy findings cross-checked with the Data Safety declaration.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Scanner dump as report | attach MobSF PDF | control table with evidence | unactionable |
| "Looks secure" | no scope, no table | per-category verdicts | unfalsifiable |
| False positive shipped | "insecure crypto possible" | file+line+proof | gets dropped |
| Hardening as fix | add root detection | fix the storage control | cosmetic |
| APK secret ignored | "it's obfuscated" | treat as public | decompilable |
| Re-test skipped | code changed = fixed | reproduce the original | regression risk |
| Silent acceptance | finding disappears | owner + date | ships forever |

## Verify

The audit is complete when, for each category, there is at least one line of evidence (command and
output, or steps and screen) and a verdict of `pass` / `fail` / `not applicable`. Re-running the
documented commands on the same build reproduces the same verdicts.

## References

- MASVS control catalogue (taxonomy; the control set changes — read the current version)
- `component-exposure`, `keystore-and-crypto`, `network-dto-safety` — per-control depth
