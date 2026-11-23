---
name: data-safety-compliance
description: >-
  Make the Data Safety declaration, privacy policy, manifest permissions and SDK behaviour agree with
  each other, and prepare for Play's policy review. Use when filling the Data Safety form, adding an
  SDK that collects data, adding a sensitive permission, when Play requests a policy fix, or before a
  production submission.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - google-play-cli-skills (gplay-compliance)
    - store-ready (store-review-audit)
    - app-store-compliance (skill)
    - mobile-agent-skillpack (security-best-practices)
---

# Data Safety and Compliance

Play reviews **three documents for consistency**: the Data Safety form, the privacy policy, and the
APK's actual behaviour (Permissions + SDK traffic). Any disagreement is a rejection, and later a
suspension.

## Use when

- Filling or updating the Data Safety form.
- Adding an SDK (analytics, crash, ads, attribution, push).
- Adding a permission (location, contacts, SMS, call log, `QUERY_ALL_PACKAGES`,
  `MANAGE_EXTERNAL_STORAGE`, `AD_ID`).
- Play sent a policy notice or a Data Safety warning.
- Pre-submission audit for a production release.

## Do not use when

- The concern is on-device secret storage → `keystore-and-crypto`.
- The concern is exported components/intents → `component-exposure`.
- The release sequence itself → `release-flow`.

## Rules

1. **The form describes actual data flows, not intentions.** For every SDK, answer: what data type
   does it collect, is it shared with a third party, is it optional, is it encrypted in transit, can
   the user request deletion. If you cannot answer for an SDK, it does not belong in the app.
2. **Third-party SDKs collect on your behalf and are your responsibility.** Crash SDK (device id,
   stack traces), analytics (events, ids), ads (advertising id), attribution (install referrer) — each
   changes the form. "The SDK handles it" is not a valid position with Play.
3. **The privacy policy must be reachable, in the app, and cover every data type in the form.** A dead
   URL or a policy missing "advertising id" is the most common rejection cause.
4. **Every sensitive permission needs a declared, user-visible purpose.** Background location, SMS,
   call log, `QUERY_ALL_PACKAGES` and `MANAGE_EXTERNAL_STORAGE` require a Play *declaration* with a
   justification; a permission without it is removed or the app rejected.
5. **Advertise ID: declare it and gate its use.** If you use the advertising id, declare it and honour
   the user's reset/limit-ad-tracking; if you do not, remove `AD_ID` — its presence contradicts a
   "no advertising" claim.
6. **Target API level is a compliance requirement, not a preference.** Each year Play raises the
   minimum for updates and then for visibility; keeping current is cheaper than an emergency upgrade.
7. **Account deletion and data-deletion requests must be honoured in-app or via a URL**, and the
   mechanism must match what the form promises.
8. **Families/children policy changes everything.** If the app targets children, ad and data rules
   tighten (no personalised ads, restricted identifiers). Decide the target audience before filling
   the form, not after.
9. **Declare data as "collected" even when it stays on-device**, if the form's definition covers
   on-device processing for the listed types — read the current definitions rather than assuming
   "collected = sent to a server".
10. **Audit all three artefacts in one pass, and keep the evidence.** A checklist run with the merged
    manifest, the form export, and the privacy policy diff attached to the release PR is what survives
    an appeal.

## Procedure

1. Extract the actual surface:
   ```bash
   ./gradlew :app:processReleaseManifest
   grep -oE "uses-permission[^/]*" app/build/intermediates/merged_manifests/release/AndroidManifest.xml | sort -u
   ./gradlew :app:dependencies --configuration releaseRuntimeClasspath | grep -iE "analytics|ads|crash|attribution|firebase" 
   ```
2. List each SDK and the data types it touches (from its own docs/Data Safety guidance).
3. Draft the form per data type: collected? shared? purpose? optional? encrypted? deletable?
4. Update the privacy policy to match, verbatim in coverage.
5. Declare purposes for sensitive permissions in Console.
6. Cross-check: every permission has a visible use; every SDK appears in the form; every form item is
   in the policy.
7. Attach the three-way diff to the release PR.

## Checklist

- [ ] Merged release manifest permissions enumerated and each justified.
- [ ] Every third-party SDK mapped to data types in the form.
- [ ] Form fields: collected / shared / purpose / optional / encrypted / deletion.
- [ ] Privacy policy live, in-app reachable, covers every form data type.
- [ ] Sensitive permissions have Play declarations.
- [ ] `AD_ID` present only if advertising is declared and used.
- [ ] Account/data deletion mechanism matches the form.
- [ ] Target audience (children) decision made and policy applied.
- [ ] Target API level meets current Play requirement.
- [ ] Three-way audit evidence attached to the release PR.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Rejection for crashing SDK data | "we don't collect anything" | declare crash + device id | SDK collects on your behalf |
| Dead policy link | 404 after site migration | in-app reachable page | automatic rejection |
| Permission without purpose | `QUERY_ALL_PACKAGES` for convenience | declare + justify, or remove | removal/rejection |
| Ad id contradiction | `AD_ID` + "no ads" claim | remove permission or the claim | inconsistency |
| Deletion promise | form says deletable, no path | in-app or URL flow | policy violation |
| Stale target API | defer upgrade | upgrade yearly | visibility loss |
| Children app, personalised ads | treat as adult app | restricted ad config | policy + legal |

## Verify

```bash
grep -oE 'uses-permission[^/]*' app/build/intermediates/merged_manifests/release/AndroidManifest.xml | sort -u
adb shell dumpsys package <pkg> | grep -A2 "requested permissions"
curl -sI "$(grep -o 'https://[^"]*privacy[^"]*' README.md | head -1)" | head -1
```

Expected: every granted permission has a user-visible feature and a form entry; the policy URL returns
200 and names each data type; the form, policy and manifest have no item present in only one of them.

## References

- Play Data Safety definitions (data types, "collected" vs "shared")
- Sensitive permission declarations (location, SMS, packages visibility, all-files access)
