---
name: vitals-and-reports
description: >-
  Read Android vitals and bulk reports as decision inputs: crash and ANR rates against Play's
  thresholds, frozen frames, wakeups, per-version and per-device slices, and what to do when a rollout
  trips a threshold. Use when a crash/ANR rate is high, when comparing two versions,
  when deciding whether to halt a rollout, or when someone quotes an aggregate rate that hides a
  device cluster.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - google-play-cli-skills (gplay-vitals, gplay-reports)
    - google-play-cli-skills (gplay-recovery)
    - agent-skills-standard (android-performance)
    - android-skill (release-check)
---

# Vitals and Reports

Vitals are **slices, not scores**. An aggregate 1% crash rate has a 0.1% cluster and a 12% cluster
inside it; only the slices tell you whether to halt, hotfix, or ignore.

## Use when

- Deciding whether a rollout is healthy.
- A crash/ANR rate crosses a Play threshold.
- Comparing the current version against the previous one.
- Someone quotes an aggregate metric to justify a decision.
- Setting the numeric halt condition for a release (see `release-flow` rule 4).

## Do not use when

- The cause of a specific crash is unknown → `bug-fix` (with the stack trace + mapping).
- The release mechanics (tracks, rollout steps) → `release-flow`.
- Startup/render performance in your own measurements → `startup-and-perfetto`.

## Rules

1. **Never read a rate without its slice.** Always at minimum: version code, device model class, OS
   version, and time window. Vitals only shows slices above a minimum user count — a missing slice is
   "too few users", not "no problem".
2. **Know the two thresholds that affect visibility:** Play surfaces warnings when crash rate or ANR
   rate exceeds its bad-behaviour levels, and demotes listing quality when they persist. Treat crossing
   them as a release event, not a metric to watch.
3. **Crash rate and ANR rate are different failures with different owners.** Crash → exception in code
   (mapping + `bug-fix`). ANR → main-thread blocking (startup work, I/O, lock, binder) — fix the
   blocking call, not the symptom.
4. **Compare like with like.** A new version at 5% rollout always looks better or worse than one at
   100% because the population differs. Compare the same slice across versions, or wait for comparable
   coverage.
5. **Frozen frames and slow rendering are experience metrics, not crash metrics.** They explain ratings
   and retention but do not trip crash thresholds. Report them with the frame budget (16.6 ms at 60 Hz,
   8.3 ms at 120 Hz).
6. **Wakeups and stuck wake locks are battery regressions.** A spike after a release usually means a
   new background job, a WorkManager misconfiguration, or a location/analytics SDK. Check the version
   where it changed, not the aggregate.
7. **Every alert has a pre-written response.** Halt the rollout, hotfix, or accept — decided before the
   number arrives. Deciding during the incident produces different answers from different people.
8. **Do not chase a rate you cannot reproduce.** A crash cluster without a stack trace and a device is
   not actionable; collect the trace (deobfuscated with `mapping.txt`) before assigning work.
9. **Bulk reports are for trends, vitals for incidents.** Monthly install/crash/rating reports answer
   "is the app getting worse", vitals answer "is this release bad right now". Using one for the other
   leads to wrong decisions.
10. **Record the decision and the evidence** (version, slice, numbers, action) in the release notes or
    an incident log. The next release repeats the analysis otherwise.

## Procedure

1. Pull the current numbers with slices (console, Play Developer API, or `gplay vitals`):
   crash rate, ANR rate, per version code, per device/OS where the app is materially used.
2. Compare against the halt condition written in `release-flow` before the rollout.
3. If crossed: identify the top cluster (version + device + OS + trace), decide halt vs hotfix per the
   pre-written response (rule 7).
4. If not crossed: record the numbers next to the rollout step and continue.
5. For battery/render regressions: bisect by version, then attribute to a new job/SDK/screen.

## Checklist

- [ ] Every quoted rate includes version, device class, OS and window.
- [ ] Crash and ANR treated as separate investigations.
- [ ] Comparison uses comparable rollout coverage or the same slice.
- [ ] Halt condition from `release-flow` checked, with its numbers.
- [ ] Battery/render metrics reported with the frame budget.
- [ ] Responding action (halt/hotfix/accept) chosen from a pre-written list.
- [ ] Stack traces deobfuscated with the release `mapping.txt`.
- [ ] Decision + evidence recorded.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Ignored cluster | "overall 1%, fine" | slice by device/version | 12% cluster inside |
| Wrong fix | ANR → add retries | find main-thread blocking | symptom not cause |
| Misleading comparison | 5% rollout vs 100% previous | same slice or wait | population differs |
| Unreproducible work | assign "fix crashes" | get trace + device first | no actionable input |
| Battery regression ignored | crash rate is fine | check wakeups/wakelocks per version | retention damage |
| Deciding live | debate during incident | pre-written response | inconsistent, slow |

## Verify

```bash
# Play Developer API / gplay equivalents
gplay vitals --package <pkg> --version <code>
gplay reports --package <pkg> --from <date> --to <date>
```

Expected: numbers reported per version and device slice, and the halt-condition comparison written down
with the action taken.

## References

- Play bad-behaviour thresholds (crash rate, ANR rate) — current values in Play Console help
- Play Developer API: vitals, bulk reports
