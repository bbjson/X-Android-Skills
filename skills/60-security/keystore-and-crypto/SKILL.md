---
name: keystore-and-crypto
description: >-
  Protect authentication tokens, user secrets and local files with the Android Keystore and
  correct crypto primitives, and detect the common ways apps leak them. Use when storing a
  token, encrypting a file or preference, choosing between EncryptedSharedPreferences and a
  Keystore-backed cipher, handling biometric-gated keys, or reviewing code that keeps secrets in
  plain SharedPreferences, logs, or hardcoded strings.
license: Apache-2.0
metadata:
  domain: security
  level: advanced
  sources:
    - agent-skills-standard (android-security)
    - android-agent-engineering (android-security)
    - android-skill (android-security-review)
    - awesome-android-agent-skills (android-accessibility is separate; rules from MASVS)
---

# Keystore and Crypto

The Keystore exists so that a key never leaves secure hardware. Any design where your code holds
raw key bytes has already lost the property the Keystore provides.

## Use when

- Storing a session token, refresh token, API key, or user PIN.
- Encrypting local files, Room fields, or DataStore values.
- Gating an operation behind biometric or device-credential authentication.
- Reviewing code for `SharedPreferences` secrets, `Log.d(token)`, hardcoded keys, or ECB mode.

## Do not use when

- The exposure is via an exported component, `PendingIntent`, or WebView → `component-exposure`.
- The trust boundary is the network payload (DTO/null-safety) → `network-dto-safety`.
- You need the full audit taxonomy across MASVS categories → `masvs-audit`.

## Rules

1. **Never store raw key material in app storage.** Keys are generated *inside* the Keystore
   (`KeyGenParameterSpec`) and referenced by alias. If you have a `ByteArray` key in memory that
   persists, the design is wrong.
2. **Never log or serialise a secret.** No `Log.*` with token/PIN/keystore output; no
   `toString()` on a credential holder (override it); no secrets in crash reports or analytics.
3. **Never hardcode a key, IV, or password** in source, `gradle.properties`, or `BuildConfig`.
   An API key shipped in an APK is public — treat it as an identifier, not a secret.
4. **Use AES-GCM (AEAD) with a random 12-byte IV per encryption.** ECB is forbidden; CBC
   without a MAC is forbidden. Store the IV alongside the ciphertext; never reuse an IV with
   the same key.
5. **Prefer `EncryptedSharedPreferences` / `EncryptedFile` (androidx.security) when the API
   level allows**; drop to raw `Cipher` + Keystore only when you need key properties those
   wrappers do not expose (e.g. biometric binding, `setUserAuthenticationRequired`).
6. **A biometric-gated key must set `setUserAuthenticationRequired(true)` and
   `setInvalidatedByBiometricEnrollment(true)`** — otherwise re-enrolling a fingerprint keeps
   the old key usable, defeating the point.
7. **Handle `KeyPermanentlyInvalidatedException` and `UserNotAuthenticatedException`
   explicitly** with a recovery path (re-auth and re-provision). An uncaught one is a crash on
   the exact device state where security matters.
8. **Do not encrypt what the OS already protects without a threat model.** App-private
   internal storage is already inaccessible to other apps; adding crypto without a clear
   adversary (backup extraction, rooted device, cloud sync) adds failure modes, not security.
   If you encrypt, also set `android:allowBackup="false"` or exclude the file — otherwise the
   ciphertext is backed up and cannot be decrypted after restore.
9. **Minimise secret lifetime.** Session token in memory for the request, refresh token in
   Keystore-backed storage, nothing else persisted. Clear on logout *and* on
   `ACTION_MANAGE_ACCOUNTS`/account removal.
10. **Certificate pinning, if used, must have a backup pin and a rotation plan.** Pinning
    without a backup brick the app when the leaf certificate rotates; pin the SPKI of a CA or
    an intermediate, and document the expiry.

## Procedure

1. Inventory secrets: `grep -rnE "token|apiKey|secret|password" --include=*.kt app/src | grep -v test`.
2. Classify each: needs-Keystore / can-be-memory-only / public-by-design.
3. For Keystore-protected values:
   ```kotlin
   val kg = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
   kg.init(KeyGenParameterSpec.Builder(alias, PURPOSE_ENCRYPT or PURPOSE_DECRYPT)
       .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
       .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
       .setUserAuthenticationRequired(needsBiometric)
       .setInvalidatedByBiometricEnrollment(true)
       .build())
   ```
4. Store `iv + ciphertext` together; version the blob so a future rotation can migrate.
5. Add backup exclusion for anything crypto-protected.
6. Add tests for the three failure modes: key invalidated, user not authenticated, corrupted blob.

## Checklist

- [ ] No `ByteArray` key persisted outside the Keystore.
- [ ] AES-GCM with per-encryption random IV; no ECB/CBC-only code in the diff.
- [ ] No secret in `Log`, `toString`, analytics, or `BuildConfig`.
- [ ] Biometric keys set `setUserAuthenticationRequired` + `setInvalidatedByBiometricEnrollment`.
- [ ] `KeyPermanentlyInvalidatedException` and `UserNotAuthenticatedException` handled.
- [ ] `allowBackup` policy consistent with encryption (no undecryptable backups).
- [ ] Logout clears every stored credential.
- [ ] Pinning (if present) has a backup pin and documented rotation.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Token readable after `adb backup` | plain `SharedPreferences` | Keystore-backed / EncryptedSharedPreferences + backup exclusion | backup extracts plaintext |
| Key in APK | `API_KEY = "sk-..."` in code | server-side proxy or Play Integrity check | APK is a public artefact |
| Deterministic ciphertext | fixed IV | random IV per encryption | identical plaintexts leak equality |
| Silent crash on new fingerprint | no invalidation handling | catch and re-provision | the "secure" path crashes |
| App uninstallable after restore | encrypted file + backup enabled | exclude from backup or handle undecryptable | restore yields undecryptable data |
| Reused key across devices | shipped key blob | per-device Keystore key | cloning the blob clones the secret |

## Verify

```bash
adb -s <serial> shell run-as <pkg> ls shared_prefs            # secrets must not appear in plaintext
adb -s <serial> shell run-as <pkg> grep -rl "eyJ" . 2>/dev/null   # JWT-like strings in app storage
./gradlew :app:lintDebug                              # HardcodedText/Keystore lint ids
```

Expected: no plaintext token in `shared_prefs` or app files, and uninstalling/reinstalling
produces a new key rather than reusing a stored one.

## References

- MASVS-STORAGE / MASVS-CRYPTO control text (taxonomy only)
- `androidx.security:security-crypto` — `EncryptedSharedPreferences`, `EncryptedFile`
