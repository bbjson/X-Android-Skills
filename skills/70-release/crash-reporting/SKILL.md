---
name: crash-reporting
description: >-
  Make production failures readable: upload the R8 mapping and native symbols, keep ANR and
  startup crashes in scope, log non-fatals with breadcrumbs instead of PII, and pick a metric that
  survives deobfuscation. Use when wiring a crash SDK, when a release stack trace is unreadable
  obfuscated frames, when ANRs never show up, when crash-free rate jumps after a release, or when
  designing what telemetry a failure should carry.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - android-developers (R8 retrace, ANR, ApplicationExitInfo, re-expressed)
    - this-repo (gap analysis: vitals skill reads reports but nothing produces them)
---

# Crash Reporting

One decision: **a crash you cannot symbolicate or reproduce is not reported.** Symbolication,
grouping and PII policy are part of shipping, not afterthoughts.

## Use when

- Adding or replacing a crash/error SDK (Crashlytics, Sentry, Bugly, or an in-house endpoint).
- A release stack trace shows `a.a.a(Unknown Source:12)`.
- ANRs, native crashes or startup crashes do not appear in the dashboard.
- Deciding what a non-fatal report and its breadcrumbs may contain.
- Crash-free rate dropped and the report does not identify the regression.

## Do not use when

- Reading Play vitals thresholds, rollout halt decisions → `vitals-and-reports`.
- R8 rules that broke runtime behaviour rather than symbols → `r8-for-compose`.
- Native build/ABI/symbol bundling decisions → `ndk-jni`.
- Ad-hoc reproduction of a single bug → `bug-fix`.

## Rules

1. **Upload the mapping in CI, from the same build that is published.** A locally built release
   without its mapping produces readable traces and a dashboard that will never be fixed
   retroactively.
2. **Keep `SourceFile` and `LineNumberTable`, and rename the source file attribute.** Without both,
   retrace yields a class and no line. `-renamesourcefileattribute SourceFile` keeps the original
   filename out of the artefact while preserving inlining metadata.
3. **Native crashes need symbols, not just a mapping.** Build with full debug symbols, keep them as
   a CI artefact, and configure symbol upload with the native build (`ndk-jni`).
4. **Initialise the SDK as early as possible and synchronously in `Application`**, and never wrap
   `Application.onCreate` in a catch-all that swallows the failure — that is how a startup crash
   becomes a blank screen with no report.
5. **ANRs are a separate stream with a separate cause set** (main-thread I/O, lock contention,
   broadcast overrun, binder stall). If the SDK does not collect them, pull them from
   `dumpsys dropbox` and `ApplicationExitInfo`; an ANR-free dashboard usually means nothing is
   collecting, not that there are none.
6. **`ApplicationExitInfo` closes the historical gap** for crashes and kills that happened before or
   without the SDK: read exit reasons at next start, map `REASON_CRASH`/`REASON_ANR`/`REASON_LOW_MEMORY`,
   and report them as session-scoped events. Guard the call by API level — the API does not exist on
   older devices, so an unguarded call crashes the app on exactly the devices it was meant to fix.
7. **Non-fatals are for recoverable failures with an action attached.** Log a handled exception when
   a retry, fallback or user-visible error happened; do not log every `Result.failure` — that
   converts an outage into a quota bill.
8. **Reports carry breadcrumbs, not payloads.** Screen names, state transitions, request ids, HTTP
   status, feature flags. Never bodies, tokens, emails, phone numbers, free text or user ids in the
   clear — hash identifiers if correlation is required.
9. **Grouping keys are a design decision.** A custom key that varies per request (a URL with an id,
   a timestamp) splits one issue into thousands. Keep grouping on exception type + top frame; put
   variance in keys, not in the grouping field.
10. **Report only in release, plus an explicit debug trigger** behind a developer screen or a debug
    build flag. Shipping a hidden "crash now" entry point in release is an abuse vector.
11. **The metric you track is stated in advance**: crash-free users (not sessions), ANR rate, and the
    per-version slice. A single aggregate hides the cluster that matters (`vitals-and-reports`).
12. **The SDK must not be on the startup critical path beyond initialisation.** Uploads happen on
    their own thread and persist across process death; nothing in the crash path may block first
    frame.

## Procedure

1. Add the SDK, initialise in `Application`, verify a debug-triggered crash arrives with a readable
   stack in a release build.
2. Add the mapping/symbol upload step to the release pipeline and assert it fails when the artefact
   is missing.
3. Verify retrace locally on the uploaded mapping.
4. Add breadcrumbs and keys at the three most important flows; run the PII check.
5. Verify ANRs and historical exits are captured (`ApplicationExitInfo`, `dumpsys dropbox`).

## Checklist

- [ ] Mapping uploaded by CI for the published build; step fails if missing.
- [ ] `SourceFile`/`LineNumberTable` kept; source file attribute renamed.
- [ ] Native symbols built, retained and uploaded.
- [ ] SDK initialised early; no catch-all around startup.
- [ ] ANR collection verified; `ApplicationExitInfo` read for pre-SDK exits.
- [ ] Non-fatals only for actionable handled failures.
- [ ] Breadcrumbs contain no PII, tokens or free text; ids hashed if needed.
- [ ] Grouping key stable; varying data in custom keys.
- [ ] Release has no crash-trigger entry point.
- [ ] Metric and slices defined before the release, not after.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Unreadable stack | no mapping upload | CI uploads mapping per build | retrace needs the exact mapping |
| One issue, 10k groups | URL with id as grouping key | stable type+frame grouping | split reporting |
| Blank screen, no report | `try { onCreate } catch {}` | let it crash, report early | swallowed startup crash |
| No ANRs in dashboard | assume SDK covers it | add explicit ANR capture | different collection path |
| Quota exhausted | log every failed request | log actionable non-fatals | volume without signal |
| Token in dashboard | log the request body | status + request id | credential leak |
| Crash-free rate ambiguous | sessions metric | users metric, per version | sessions over-weight flaky users |

## Verify

```bash
./gradlew :app:assembleRelease
# mapping exists for this exact build
find app/build/outputs/mapping -name 'mapping.txt' -newer app/build.gradle.kts | head -3
# deobfuscate a stack trace locally
$ANDROID_HOME/cmdline-tools/latest/bin/retrace app/build/outputs/mapping/release/mapping.txt /tmp/obfuscated.txt | head -20
adb -s <serial> shell dumpsys dropbox --print data_app_anr | head -20
adb -s <serial> shell dumpsys activity exit-info <pkg> | head -30
```

Expected: retrace resolves class, method and line for a release stack trace; the same build's
mapping is a CI artefact; ANR and exit-info output show the app's recorded failures.

## References

- R8 `retrace`, `-keepattributes SourceFile,LineNumberTable`, `-renamesourcefileattribute`
- `ActivityManager.getHistoricalProcessExitReasons`, `ApplicationExitInfo`
- `adb shell dumpsys dropbox --print data_app_anr`
