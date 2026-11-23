---
name: remote-config
description: >-
  Ship behaviour flags whose defaults live in code, whose fetch never blocks startup, and whose
  kill switch has been tested. Use when adding a feature flag or kill switch, running a server-side
  experiment, when a flag change did not take effect, when the app is unusable offline because a
  fetch failed, or when nobody knows which flags are still read.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - firebase (Remote Config guidance, re-expressed)
    - this-repo (gap analysis: flag exists as a word in four skills, owned by none)
---

# Remote Config

One decision: **the code must be fully functional with every remote value absent.** Remote config
adjusts a working app; it does not supply the app's behaviour.

## Use when

- Adding a feature flag, a kill switch, a server-controlled limit or an experiment variant.
- A remote value did not take effect, or took effect only after a restart.
- The app crashes or blocks on startup when the config fetch fails.
- Deciding how to run an A/B test with sticky assignment.
- Cleaning up flags that nobody reads any more.

## Do not use when

- Entitlement, paywall state or anything a user paid for → `billing-and-subscriptions` and the
  server; a client flag is spoofable.
- Experiment measurement design and exposure events → `analytics-instrumentation`.
- Which release/track delivers the build → `release-flow`.
- Local build-time constants per environment → `build-variants`.

## Rules

1. **Every flag has a default in code, and the default is the safe value.** No default means a
   parsing crash or a silently disabled feature when the fetch fails; `false`/off is the default
   for anything that could lose data or money.
2. **Fetch never blocks first frame.** Read the last cached value synchronously, start the fetch in
   the background, and activate when it arrives. A splash screen waiting on the network is a
   self-inflicted outage.
3. **Fetch and activate are two steps, and the result of activation is checked.** Fetching without
   activating is the most common "my change did not take effect" bug.
4. **Read each flag once into a typed state object**, at a lifecycle boundary (startup, session,
   screen entry). Reading flags directly inside a Composable body re-reads per recomposition and
   makes the value non-deterministic within a frame.
5. **A flag is not a value type.** Parse once into a typed wrapper (`Int`, enum, duration) with a
   fallback to the default on malformed input, and log the fallback — never let a bad remote string
   reach `toInt()`.
6. **Assignment must be stable for the user across launches**, provided by the platform's
   experiment assignment or your own salted hash. A variant that flips between launches invalidates
   the experiment and confuses the user.
7. **A kill switch disables a code path, and it must be tested both ways.** A kill switch nobody has
   ever flipped is a hypothesis; verify "on" and "off" in a release build before the incident.
8. **Config never gates data safety, security or legal requirements.** Consent, crash reporting and
   privacy behaviour must not depend on a remote flag that an outage can reset.
9. **Server-side truth is authoritative for anything that must be consistent across devices**
   (limits, quotas, entitlements, moderation). Remote config is a broadcast cache with a delay, not
   a database.
10. **Every flag carries an owner and an expiry in the tracking table**, and expired flags are
    deleted with their branches. Flag debt is code that can never be removed because nobody knows
    what reads it.
11. **Two experiments never share one flag**, and an experiment flag is not reused after the test
    concludes. Reuse contaminates the next result with the previous population.
12. **A stale policy is chosen explicitly**: for a kill switch, stale-on (keep the feature off) is
    safer; for a promotional banner, stale values are acceptable. Write the choice down.

## Procedure

1. Add the default in code and the typed read at one injection point.
2. Register the flag name and type in the tracking table with owner and expiry.
3. Wire fetch + activate at startup, off the critical path; log activation success.
4. Add a test that reads with a fake config provider returning default, override, and malformed.
5. Before release, flip the kill switch in the console on a test build and confirm the path.

## Checklist

- [ ] Default in code, safe value, documented.
- [ ] Fetch off the critical path; cached value read first.
- [ ] Fetch and activate both called; activation checked/logged.
- [ ] Flags read once into a typed state, not per recomposition.
- [ ] Malformed values fall back to default and are logged.
- [ ] Assignment stable across launches.
- [ ] Kill switch exercised both ways in a release build.
- [ ] No consent/security/legal behaviour behind a flag.
- [ ] Multi-device consistency sourced from the server, not the flag.
- [ ] Owner and expiry recorded; expired flags deleted.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Change not applied | fetch without activate | fetch then activate, check | activation is required |
| Startup blocked offline | await fetch before UI | cached value + background fetch | network is not guaranteed |
| Crash on bad value | `toInt()` on remote string | typed parse with default | remote input unvalidated |
| Flipping variants | random assignment per launch | stable platform/hash assignment | invalid experiment |
| Kill switch failed | never tested | flipped on/off pre-release | untested path |
| Permanent flags | nobody owns cleanup | owner + expiry | unmovable branches |
| Security behind a flag | consent controlled remotely | hardcoded policy | outage changes compliance |

## Verify

```bash
./gradlew :app:testDebugUnitTest --tests '*Config*'
# with the vendor's debug mode / console override, flip the flag and relaunch
adb -s <serial> shell am force-stop <pkg> && adb -s <serial> shell monkey -p <pkg> 1
adb -s <serial> logcat -d | grep -iE 'remoteconfig|fetch|activate' | tail -20
```

Expected: with the network disabled the app starts on defaults, the log shows a fetch attempt and a
subsequent activation, and the console-flipped kill switch changes behaviour on the next launch
without a store update.

## References

- Firebase Remote Config: `fetchAndActivate`, `getBoolean`/`getInt`, `minimumFetchInterval`,
  parameter groups, personalisation
- A/B testing assignment stability and exposure logging
