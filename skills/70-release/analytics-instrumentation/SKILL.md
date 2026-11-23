---
name: analytics-instrumentation
description: >-
  Instrument product analytics as a reviewed schema — one event per user intent, no PII in
  parameters, consent before collection, and firing points that survive recomposition. Use when
  adding an event or funnel, when numbers disagree with the backend, when an experiment cannot be
  analysed, when a privacy review asks what is collected, or when events fire multiple times.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - android-developers (analytics + ads policy, re-expressed)
    - this-repo (gap analysis: no measurement/consent skill existed)
---

# Analytics Instrumentation

One decision: **the event schema is code, reviewed like code.** An event added from a marketing
request with no schema is a permanent, undocumented data source nobody can retire.

## Use when

- Adding, renaming or removing an analytics event, parameter, screen view or funnel step.
- An experiment's results cannot be attributed to a variant.
- Dashboard numbers do not match backend numbers.
- A privacy/Data Safety review asks which fields leave the device.
- An event fires twice per action, or zero times after a refactor.

## Do not use when

- Crash and error telemetry rather than product events → `crash-reporting`.
- The Data Safety form and policy text itself → `data-safety-compliance`.
- Choosing and wiring a remote flag for an experiment → `remote-config`.
- Reading Play vitals/metrics rather than collecting your own → `vitals-and-reports`.

## Rules

1. **The tracking plan lives in the repository** (one table: event name, trigger, parameters, owner,
   deprecated-on). An event that exists only in the SDK dashboard is undocumented data.
2. **Name by `object_action` in one case convention, and keep the name a noun+verb.** Renames are
   breaking changes: a dashboard comparing old and new names silently loses history.
3. **One event per user intent, fired where the intent is decided** — in the ViewModel or an
   app-level effect, not in a Composable body and not in a click lambda that also triggers the work.
   Composition runs many times; the intent runs once.
4. **Consent gates collection, not just persistence.** Nothing is sent (or queued) before consent;
   the wrapper must be a no-op implementation, not a flag checked after the SDK already started.
   Disabling collection must also clear what is queued.
5. **No personal data in parameters.** No email, phone, name, free text, precise location, full IP,
   or raw user id. Use an internal opaque id or a hash with a per-app salt, and record which fields
   are considered personal in the tracking plan.
6. **Advertising identifiers are not analytics identifiers.** Reading them requires the documented
   consent and declaration; a hashed advertising id is still personal data.
7. **Every screen view is emitted by the navigation layer once per destination,** keyed on the
   destination, not on recomposition or on `onResume` alone.
8. **Parameters are typed and bounded**: enum-like strings from a closed set, numerics bounded,
   strings truncated by the wrapper with a debug-build assertion — silently truncated names make
   funnel steps unmatchable.
9. **High-volume events are sampled deliberately** and the sample rate travels with the event, so a
   later analysis can un-weight it. Ad-hoc sampling in the wrapper destroys trend comparability.
10. **Experiment exposure is an event**, logged when the variant is applied and once per user per
    experiment. Without it the experiment has no denominator.
11. **Respect the vendor's reserved names and limits**; do not invent names that collide with its
    automatic events, and keep parameter counts and name lengths inside the documented limits.
12. **The wrapper is injectable and no-ops in tests**, so unit tests asserting "the event fired" do
    not need a network SDK, and UI tests never send production data.

## Procedure

1. Add the event to the tracking plan first; get the parameters reviewed (PII check, closed sets).
2. Add a typed method to the analytics interface; implement in the vendor adapter and in the test
   no-op.
3. Fire it from the decision point; add a unit test on the ViewModel asserting one call per intent.
4. Verify in the vendor's debug/validation mode on a real device.
5. Update the plan's deprecation column and remove dead events on a schedule.

## Checklist

- [ ] Event added to the tracking plan with owner and parameters.
- [ ] Name follows the convention; no breaking rename without a migration note.
- [ ] Fired once per intent from the decision point, not from composition.
- [ ] Consent gate is a no-op implementation before consent; queued data cleared on revoke.
- [ ] No PII in parameters; identifiers opaque or salted-hashed and listed as personal.
- [ ] No advertising id used as an analytics key.
- [ ] Screen views keyed to destinations, emitted once.
- [ ] Parameter types bounded; truncation asserted in debug.
- [ ] Sampling rate attached to sampled events.
- [ ] Exposure event for each experiment.
- [ ] Wrapper injectable; tests use the no-op.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Doubled event count | fire in composable body | fire from decision point | composition repeats |
| Funnel step missing | rename event in code | version the plan, emit both during migration | history unmatched |
| Data collected pre-consent | flag checked after SDK start | no-op implementation | SDK already queued data |
| PII in dashboard | log email as user property | opaque id / salted hash | policy violation |
| Experiment unanalysable | no exposure event | exposure once per user | no denominator |
| Truncated funnel | long free-text param | bounded enum/strings | silent truncation |
| Tests hit production | real SDK in tests | no-op wrapper | polluted data |

## Verify

```bash
./gradlew :app:testDebugUnitTest --tests '*Analytics*'
adb -s <serial> shell setprop debug.firebase.analytics.app <pkg>   # vendor debug/validation mode
adb -s <serial> logcat -d | grep -iE 'FA-SVC|analytics' | tail -40
grep -rn 'logEvent' --include=*.kt app core | grep -vi test | wc -l   # review: each hit is a decision point
```

Expected: the vendor debug output shows each event exactly once per action with the planned
parameters, and no personal data appears in the log of a real flow.

## References

- Vendor analytics event/parameter limits and debug mode
- `setAnalyticsCollectionEnabled`, consent-mode semantics
- Google Play Data Safety and ads policy (see `data-safety-compliance`)
