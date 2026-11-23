---
name: release-flow
description: >-
  Take an Android build from a green CI commit to a published Play release with the correct
  signing, track, staged rollout, and rollback path. Use when preparing a release candidate,
  choosing between internal/closed/open tracks, deciding staged rollout percentages, recovering
  from a bad release, wiring Play Developer API automation, or auditing a release checklist
  before submission.
license: Apache-2.0
metadata:
  domain: release
  level: core
  sources:
    - google-play-cli-skills (gplay-release-flow, gplay-tracks, gplay-signing, gplay-recovery)
    - store-ready (store-review-audit)
    - app-store-compliance (skill)
    - mobile-agent-skillpack (android-release-checklist, mobile-ci-release-flow)
---

# Release Flow

A release is a sequence of irreversible steps. The decision this skill makes: **which step may
be automated, which requires a human gate, and what the rollback is at each point.**

## Use when

- Cutting a release candidate or promoting a build between tracks.
- Choosing rollout percentage or user track.
- Automating upload/spans via the Play Developer API (`gplay` or another client).
- A bad release is live and must be halted or rolled back.
- Auditing whether a build is releasable at all.

## Do not use when

- The blocker is signing key configuration → `signing-and-play-signing`.
- Store listing text, screenshots, Data Safety form → `play-metadata` / `data-safety-compliance`.
- Crash/ANR rates must be interpreted after release → `vitals-and-reports`.
- Server-controlled rollout, kill switches after release → `remote-config`.
- Purchase or subscription mechanics inside the release → `billing-and-subscriptions`.

## Rules

1. **Version code is assigned by CI, monotonically, and never reused.** No manual bumps in a PR
   that can be merged twice; derive from a counter or the CI run, and record it in the build log.
2. **Same artifact promotes through tracks.** Build once (signed AAB), upload to `internal`, then
   promote the *identical* artifact to `closed`→`open`→`production`. Rebuilding per track is how
   "works in beta, crashes in prod" happens.
3. **Production is always staged.** Start at 5% or less, hold long enough to read crash/ANR
   (`vitals-and-reports`), then step. A 100% first push is only acceptable for a hotfix of an
   outage.
4. **Every release has a written halt condition.** Numeric, not vibes: e.g. "crash-free < 99.0%
   over 2h" or "ANR > 0.5%". Without it nobody escalates.
5. **Uploading and releasing are two separate acts.** Uploading an AAB to a track must not
   auto-release; a human or an explicit pipeline job promotes the rollout status.
6. **Pre-submission audit before every production push**: target API level, Data Safety form,
   permissions justified, signing certificate, `debuggable=false`, no test-only keys obfuscated.
7. **Rollback is "halt rollout + re-promote previous version code"**, not a new build, whenever
   the previous version code is still installable. Rebuilding to roll back loses the audit trail.
8. **Staged rollout does not roll back installed users.** Users on 20% keep the bad version.
   Mitigate in-app (feature flag / remote kill switch) if the fix requires a new build to reach them.
9. **Every release has release notes for the track's audience.** Internal = technical, production
   = user-facing; Play rejects or under-delivers releases with empty notes.
10. **Never release from a dirty tree or an unmerged branch.** The commit → CI artefact → Play
    chain must be reproducible from a tag.

## Procedure

1. Verify readiness:
   ```bash
   ./gradlew :app:bundleRelease
   unzip -p app/build/outputs/bundle/release/app-release.aab base/manifest/AndroidManifest.xml | \
     grep -o 'android:debuggable="[^"]*"'   # must be false or absent
   ```
2. Upload internal, then verify the artifact digest equals the built one.
3. Promote to closed/open; attach release notes.
4. Promote to production at ≤5%; record the halt condition and the watch window.
5. After the window, step 20→50→100, each step gated on the same metric.
6. If halt condition trips: halt rollout, decide rollback vs hotfix, then notify with numbers.

## Checklist

- [ ] Version code from CI, monotonic, logged.
- [ ] One AAB promoted across tracks (digest verified at each step).
- [ ] `debuggable=false`, no test credentials in the artefact.
- [ ] Data Safety form and metadata unchanged or updated for this release.
- [ ] Production rollout starts staged with a numeric halt condition.
- [ ] Release notes present for the target audience.
- [ ] Rollback path written down before the rollout starts.
- [ ] Release built from a tag, clean tree.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Beta works, prod crashes | rebuild per track | promote one artifact | builds differ |
| Rollout stuck at 20% | wait | step per the gate metric | users never reach the fix |
| Bad release spreads | push new build over the bad one | halt + re-promote previous | faster, auditable |
| Cannot reproduce prod | release from a branch | release from a tag | no provenance |
| Empty release notes | "bug fixes" | audience-appropriate notes | users cannot decide to update |
| Debug build hidden check | trust the build type name | inspect the manifest in the AAB | variants can be misconfigured |

## Verify

```bash
./gradlew :app:bundleRelease && ./gradlew :app:signingReport
# Play: compare uploaded artifact digest with local
keytool -printcert -jarfile app/build/outputs/bundle/release/app-release.aab | head -5
```

Expected: signing certificate matches Play App Signing config, artifact digest matches what was
uploaded, and the track shows the intended version code with a non-100% rollout.

## References

- Play Console track docs; Play Developer API `edits.tracks`
- `gplay releases` / `gplay tracks` — command surface for the same operations
