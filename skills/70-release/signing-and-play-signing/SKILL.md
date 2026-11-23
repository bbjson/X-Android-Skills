---
name: signing-and-play-signing
description: >-
  Configure release signing correctly with an upload key and Play App Signing, keep keys out of the
  repository and out of logs, and plan rotation before it is urgent. Use when setting up signingConfigs,
  when a build is signed with a debug key, when Play rejects an upload for a certificate mismatch,
  when deciding whether to enroll in Play App Signing, or when a key must be rotated.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - google-play-cli-skills (gplay-signing)
    - agent-skills-standard (android-deployment)
    - android-skill (release-check)
    - mobile-agent-skillpack (android-release-checklist)
---

# Signing and Play App Signing

There are two different keys in a modern Play app, and confusing them is the usual cause of
"cannot upload update/new APK".

| Key | Who holds it | Signs | Can be lost? |
|---|---|---|---|
| **Upload key** | you / CI | the AAB you upload | yes, can be reset with Play support |
| **App signing key** | Google (Play App Signing) | the APK delivered to devices | effectively never |

## Use when

- Setting up `signingConfigs` for the first time.
- A release build installs but Play rejects the upload.
- Deciding whether to enrol in Play App Signing (default for new apps).
- Configuring a CI release job with a keystore secret.
- Planning key rotation or a compromised upload key.

## Do not use when

- The sequence of tracks/rollout → `release-flow`.
- The build fails before signing (R8, resources) → `r8-for-compose` / `bug-fix`.
- Store listing/content → `play-metadata`.

## Rules

1. **Never commit a keystore or its passwords.** Not in the repo, not in `gradle.properties`
   (that file is committed by default), not in a build script. CI injects it as a secret; locally it
   comes from `~/.gradle/gradle.properties` in the user's home, outside the repo.
2. **Signing config reads from properties, and fails loudly when they are missing** — but only for
   release builds. A missing key locally must break `assembleRelease`, not silently produce an
   unsigned artefact that "installs" because of a fallback to debug.
3. **Debug and release use different keystores, and release never uses the debug key.** The debug key
   is `~/.android/debug.keystore` with a public password — signing a release with it means any APK
   can impersonate your app's updates.
4. **Enrol in Play App Signing and upload AABs, not APKs.** Play re-signs with the app signing key you
   no longer control; losing your upload key is recoverable, losing the app signing key is not.
5. **Verify what you built, not what you configured:** `./gradlew :app:signingReport` and
   `keytool -printcert -jarfile`/`apksigner verify` on the artefact. A green build with
   `signingConfig = signingConfigs.getByName("debug")` is a real defect.
6. **`v1`/`v2`/`v3` are not all needed** — for modern `minSdk`, v2/v3 suffice; only keep v1 for very
   old devices. Do not disable v2 to "fix" an installer issue; that is a different bug.
7. **The upload key password and the keystore password are separate secrets** and must be handled as
   two values. Storing them in one base64 blob is convenient but means rotating one forces rotating both.
8. **Back the upload key up in two offline places, with an owner named.** A lost upload key is a
   support ticket; a lost app signing key (self-managed, not Play-managed) is a new app.
9. **Rotation is planned, not reactive.** If you use Play App Signing, key upgrade/rotation is possible
   without breaking updates; if you self-manage, design the rotation path before you need it.
10. **CI must never print the keystore or password, and must delete the temp file.** `set +x` around
    secret export; `$RUNNER_TEMP` with `chmod 600`; cleanup step that always runs.

## Procedure

1. Decide the model: Play App Signing (recommended) + upload key.
2. Generate an upload keystore **outside** the repo:
   ```bash
   keytool -genkeypair -v -keystore upload.jks -keyalg RSA -keysize 4096 \
     -validity 10000 -alias upload
   ```
3. Store the keystore + two passwords as CI secrets; base64 the file.
4. Configure signing from properties:
   ```kotlin
   signingConfigs {
     create("release") {
       storeFile = file(providers.gradleProperty("RELEASE_STORE_FILE").get())
       storePassword = providers.gradleProperty("RELEASE_STORE_PASSWORD").get()
       keyAlias = providers.gradleProperty("RELEASE_KEY_ALIAS").get()
       keyPassword = providers.gradleProperty("RELEASE_KEY_PASSWORD").get()
     }
   }
   ```
5. Attach it only to the `release` build type.
6. Verify with `signingReport` and `apksigner verify --print-certs`.
7. First upload: enrol in Play App Signing, upload the AAB, confirm the certificate fingerprint in
   Play Console matches the upload key.

## Checklist

- [ ] No keystore or password in the repository (checked with `git log -p -- '*.jks'`).
- [ ] Signing properties read from user/CI properties; release fails loudly when absent.
- [ ] Release never falls back to the debug keystore.
- [ ] `signingReport` and `apksigner verify` confirm the release certificate.
- [ ] Play App Signing enrolled; app signing fingerprint recorded.
- [ ] Upload key backed up offline in two places with an owner.
- [ ] CI writes the keystore to a temp file, `chmod 600`, deletes it in an always-run step.
- [ ] Password and keystore password stored as separate secrets.
- [ ] Rotation path documented.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Any APK can update your app | release signed with debug key | dedicated upload key | debug key is public |
| Key committed | `upload.jks` in repo | CI secret | irrevocable leak |
| Silent unsigned release | fallback to debug config | fail on missing properties | undetectable |
| Play rejects update | APK signed with a new key | keep the upload key; use Play App Signing | certificate mismatch |
| Lost key, app dead | self-managed signing key | Play-managed app signing | unrecoverable |
| Secret in CI log | `echo`/`set -x` around export | `set +x`, temp file | leak |

## Verify

```bash
./gradlew :app:signingReport | grep -A4 "Variant: release"
apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
keytool -printcert -jarfile app/build/outputs/bundle/release/app-release.aab | head -8
git log --all --oneline -- '*.jks' '*.keystore'    # must be empty
```

Expected: the release certificate is the upload key (not `CN=Android Debug`), its SHA-256 matches
Play Console's upload certificate, and no keystore has ever been committed.

## References

- Play App Signing, upload key reset procedure
- `apksigner verify --print-certs`, `keytool -printcert -jarfile`
