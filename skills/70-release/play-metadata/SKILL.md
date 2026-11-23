---
name: play-metadata
description: >-
  Keep the store listing in version control and inside Play's real limits — title/short/full
  description character counts, graphic and screenshot specifications, per-locale variants — so a
  release ships accurate content instead of a hand-edited console. Use when writing or updating a
  listing, when uploading graphics/screenshots, adding a locale, or when content drifts from what the
  app actually does (a policy risk).
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - google-play-cli-skills (gplay-metadata-sync, gplay-apps)
    - store-ready (store-review-audit)
    - app-store-compliance (skill)
    - agent-skills-standard (android-deployment)
---

# Play Metadata

Listing content is **release artefact number two**. It ships with the build, it is reviewed by Play,
and it is the only thing a user reads before installing.

## Use when

- Writing or editing title, short description, full description, or "what's new".
- Producing screenshots, feature graphic, or icon.
- Adding a locale or localised listing.
- Automating listing upload/sync from a repository tree.
- A listing claim might not match the app (policy/rejection risk).

## Do not use when

- The release sequence and rollout → `release-flow`.
- The Data Safety form and privacy policy → `data-safety-compliance`.
- Post-release metrics → `vitals-and-reports`.
- Product, price and subscription configuration in the console → `billing-and-subscriptions`.

## Rules

1. **The listing lives in the repository as a per-locale tree**, synced by CI, not edited by hand in
   the console. A console-only edit is invisible in review and lost at the next sync.
   ```
   metadata/
     en-US/{title.txt,short_description.txt,full_description.txt,changelogs/1234.txt,images/}
     de-DE/…
   ```
2. **Respect the hard limits, and verify them mechanically:** title ≤30, short description ≤80,
   full description ≤4000 characters, "what's new" ≤500 per locale. A truncated upload is a silent
   content loss.
3. **Screenshots are real captures of the shipped build**, at the required sizes (phone: min 320px on
   the short side, 2–8 images, 16:9 or 9:16). No fabricated features, no mocked data implying
   functionality that does not exist — that is a rejection and a refund vector.
4. **Icon is 512×512 32-bit PNG; feature graphic is 1024×500** — separate assets from the launcher
   icon, and both are required.
5. **Every claim in the description must be verifiable in the app.** "Works offline", "no ads",
   "encrypted" — Play enforces truthfulness, and users file refunds. If a claim is aspirational,
   remove it or gate it behind a feature flag you actually ship.
6. **No keyword stuffing, no competitor names, no incentive language** ("install to win"). These are
   policy violations, not SEO.
7. **Per-locale content is reviewed together with the release that changes the feature.** A shipping
   feature with a stale German description is an inconsistency users report.
8. **"What's new" is per version code and user-facing**, not "bug fixes and improvements" for every
   release. It is the one text users read before updating.
9. **Diffs are reviewed like code.** Listing changes go through a pull request; the reviewer sees the
   text and image change, not a console audit log nobody reads.
10. **Sync is idempotent and never deletes unexpectedly.** An upload script that removes locales not
    present locally will delete live translations the first time it runs from an incomplete checkout.

## Procedure

1. Create `metadata/<locale>/...` for the default locale first (rules 1, 2).
2. Validate limits locally:
   ```bash
   for f in metadata/*/title.txt; do printf "%s %s\n" "$(wc -m < "$f")" "$f"; done   # ≤30
   ```
3. Capture screenshots from the actual build on a video (avoid dev/debug overlays), crop per spec.
4. Write "what's new" for the target version code.
5. Sync via API (`gplay` or a script); diff the console against the repo afterwards.
6. Review the PR; the PR is the audit trail.

## Checklist

- [ ] Listing lives in `metadata/<locale>/`, synced by CI.
- [ ] Character limits verified for every locale.
- [ ] Screenshots captured from the release build, correct sizes/count.
- [ ] Icon 512×512 and feature graphic 1024×500 exist and differ from launcher icon.
- [ ] Every claim is verifiable in the app.
- [ ] No keyword stuffing / competitor names / incentive language.
- [ ] "What's new" written for the version code being shipped.
- [ ] Locales reviewed with the feature change that affects them.
- [ ] Sync does not delete locales absent from an incomplete checkout.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Lost translation | console-only edit + sync | repo tree is the source | overwritten |
| Truncated title | 42 characters | ≤30 verified | silent cut |
| Rejected build | mocked screenshot of a feature | real capture | policy violation |
| Stale locale | feature shipped, text unchanged | update locale with the feature | user confusion |
| Deleted locales | sync from partial checkout | explicit delete list | live translations lost |
| Empty changelog | "bug fixes" every time | per-version user-facing notes | users cannot decide |

## Verify

```bash
# after sync, pull back and diff
diff -r metadata/en-US /tmp/play-listing/en-US
for f in metadata/*/short_description.txt; do echo "$(wc -m <"$f") $(basename $(dirname $f))"; done
```

Expected: the pulled listing matches the repository character-for-character, every locale is within
its limits, and the screenshot set for the shipped version code is present.

## References

- Play Console listing character limits and graphic specifications
- Play Developer API `edits.listings`, `edits.images`
