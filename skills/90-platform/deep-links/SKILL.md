---
name: deep-links
description: >-
  Wire Android App Links and custom-scheme deep links that actually open the app, resolve to one route
  definition, validate their parameters, and degrade predictably when the app is not installed or
  verified. Use when adding a link target, when a link opens the browser instead of the app, when two
  apps claim the same scheme, or when a link crashes or lands on the wrong screen after an app update.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - kotlin-kmp-claude-agent-skills (kotlin-platform-app-links-and-deep-links)
    - agent-skills-standard (android-navigation, android-navigation-type-safe)
    - awesome-android-agent-skills (compose-navigation)
    - component-exposure (parameter validation rules reused)
---

# Deep Links

A deep link is **a public entry point defined outside your app**. It has three parts that must agree:
the manifest filter, the verification artefact, and the route parser.

## Use when

- Adding a link that opens a specific screen (email, web, QR, push).
- A link opens the browser or the Play Store instead of the app.
- Two apps claim the same custom scheme.
- A link works in debug but not in release (or vice versa).
- A link must survive the app not being installed yet.

## Do not use when

- The concern is an exported Activity receiving an arbitrary Intent → `component-exposure`.
- The concern is navigation graph shape → `compose-navigation`.
- The concern is push payload → `notifications-fcm`.

## Rules

1. **Prefer `https` App Links over custom schemes.** A web URL works before install (browser → Play
   Store), is unambiguous, and is verifiable. Custom schemes are unowned, can be claimed by any app, and
   cannot be verified.
2. **App Links require `autoVerify="true"` plus a reachable `/.well-known/assetlinks.json`** on the exact
   host, served over `https` with the release certificate's SHA-256 fingerprint. Without verification,
   Android shows a chooser and the browser may win.
3. **One host/path pattern, one route, defined once.** The manifest filter, the link mapping function, and
   the navigation route must all derive from the same declaration; three copies drift within one release.
4. **Parse, then validate, then navigate — never concatenate.** Extract typed values (`id`, `tab`,
   `slug`), validate against the allowed shape/range, and pass the typed route. No file paths, no SQL,
   no reflection from URI segments (`component-exposure` rule 10).
5. **Unknown/unparseable links land on a defined fallback** (home screen or an error state), not a crash
   and not silently nothing. Cold-start links arrive before the UI exists — buffer and deliver after the
   nav graph is ready.
6. **Handle cold start and warm start identically.** `onCreate` intent handling and
   `onNewIntent`/`singleTop` are two code paths that must produce the same result; a link that works
   only when the app is already running is a common regression.
7. **Custom scheme links need a fallback.** If the app is not installed, the link does nothing (or
   errors); provide a web URL or a Play Store link alongside, and never rely on the scheme alone.
8. **Do not put secrets or long state in a URL.** Links appear in logs, browsers, and referrers; use an
   id and fetch the content.
9. **Preserve the back stack.** A deep link into a detail screen must synthesise the parent stack (or
   define the intended Back behaviour) so Back does not exit the app.
10. **Test with `adb am start` for every pattern, on a release build** (with verification) and a debug
    build (without). Release-only failures come from the certificate fingerprint in `assetlinks.json`.

## Procedure

1. Choose the model: `https` App Link (default) or custom scheme (only when no domain exists).
2. Declare one `intent-filter` with the exact host/path; add `autoVerify` for `https`.
3. Publish `assetlinks.json` with the **release** certificate SHA-256; wait for propagation; verify on
   device.
4. Write the single `Uri → Route` mapper with validation and an explicit fallback.
5. Wire cold start + `onNewIntent` to the same mapper; buffer until the nav graph exists.
6. Synthesise the parent back stack for deep entries.
7. Test all patterns on release + debug, app installed and not installed.

## Checklist

- [ ] `https` App Links preferred; custom scheme only if unavoidable.
- [ ] `autoVerify` set and `assetlinks.json` reachable with the release fingerprint.
- [ ] One declaration drives manifest + mapper + route.
- [ ] Parameters parsed to typed values and validated; no concatenation into paths/queries.
- [ ] Unknown link → defined fallback, no crash.
- [ ] Cold start and warm start produce identical results.
- [ ] Back stack for deep entries defined.
- [ ] No secrets/state in the URL.
- [ ] Custom scheme (if used) has a web/Play Store fallback.
- [ ] Tested on release and debug builds.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Opens browser not app | custom scheme or unverified https | verified App Link | verification required |
| Claimed by another app | custom scheme only | https App Link | schemes are unowned |
| Works warm, not cold | only `onNewIntent` | cold start + buffer | nav graph not ready |
| Crash on bad link | `uri.lastPathSegment!!` | validate + fallback | untrusted input |
| Back exits app | no parent stack | synthesise parents | broken UX |
| Release-only failure | fingerprint of debug cert | release cert SHA-256 | assetlinks mismatch |
| Three definitions | manifest + mapper + route separately | single source | drift |

## Verify

```bash
# App Link
adb shell am start -a android.intent.action.VIEW -d "https://example.com/detail/42"
# custom scheme
adb shell am start -a android.intent.action.VIEW -d "example://detail/42"
# verification state
adb shell pm get-app-links <pkg>          # verified / unverified domains
# malformed link must not crash
adb shell am start -a android.intent.action.VIEW -d "https://example.com/detail/%00"
adb shell dumpsys window | grep -m1 mCurrentFocus
```

Expected: the app (not the browser) receives the link, lands on the intended screen with a sane back
stack, and a malformed link shows a fallback instead of crashing.

## References

- App Links verification (`assetlinks.json`, `fingerprints`), `android:autoVerify`
- `NavController.handleDeepLink` / Navigation 3 `NavKey` mapping
