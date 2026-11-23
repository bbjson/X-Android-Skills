---
name: component-exposure
description: >-
  Close the app's inbound attack surface: exported components, intent redirection, PendingIntent
  mutability, FileProvider paths, WebView bridges, deep-link parameters and task hijacking. Use
  when declaring a component in the manifest, receiving an Intent from another app, sharing a file,
  embedding a WebView, adding a deep link, or auditing an app against MASVS-PLATFORM.
license: Apache-2.0
metadata:
  domain: security
  level: advanced
  sources:
    - agent-skills-standard (android-legacy-security, android-security)
    - android-skill (android-security-review)
    - mobile-agent-skillpack (security-threat-model)
    - phone-spyware-check (attack-surface framing)
---

# Component Exposure

Every `exported="true"` is a **public API with no version negotiation**. Any app on the device can
call it with any Intent it can construct.

## Use when

- Adding/changing `exported`, intent filters, `PendingIntent`, `ContentProvider`, or `FileProvider`.
- Receiving data from another app (share sheet, `ACTION_VIEW`, deep link, custom scheme).
- Using a `WebView` with JS or file access.
- Auditing the app's attack surface (MASVS-PLATFORM).
- A security scanner reports `ExportedReceiver` / `ExportedService` / `WebView` findings.

## Do not use when

- The secret is stored locally (Keystore, files) → `keystore-and-crypto`.
- The concern is the network payload → `network-dto-safety`.
- You need the full MASVS taxonomy → `masvs-audit` (roadmap).

## Rules

1. **`android:exported` is always explicit** on any component with an intent filter, and defaults to
   `false` everywhere else. Implicit-by-default is removed, but omission still hides intent — write it.
2. **An exported component validates everything it receives.** Null/absent extras, wrong types
   (`getStringExtra` on an `Int`), oversized payloads, unexpected `Uri` schemes/hosts. Treat the
   Intent as untrusted input, not as an internal call.
3. **Intent redirection is a vulnerability, not a feature.** If a component extracts
   `intent.getParcelableExtra<Intent>("next")` and starts it, an attacker can launch any
   non-exported component of yours. If you must proxy, allow-list the target package/component and
   strip the extras.
4. **`PendingIntent` is `FLAG_IMMUTABLE` unless mutation is genuinely required.** Mutable +
   implicit is a hijack vector: the receiver can fill in the empty `Intent`. If mutable is unavoidable,
   set an explicit `setPackage()`/component and no empty implicit Intent.
5. **`FileProvider` shares the narrowest path possible.** `android:pathPrefix` limited to an export
   subdirectory; never `path="/"` or the app root. Share with `FLAG_GRANT_READ_URI_PERMISSION` and
   revoke with `revokeUriPermission` when the transfer completes.
6. **`ContentProvider` is `exported="false"` unless it is an intended public interface**, in which
   case it needs `android:permission` *and* `path-permission` per table. A provider with only
   `readPermission` still leaks if the caller can construct paths.
7. **`WebView` gets the minimum capability set:** `javaScriptEnabled` only if the page needs it;
   `allowFileAccess = false`; `allowContentAccess = false`; `allowFileAccessFromFileURLs = false`;
   `allowUniversalAccessFromFileURLs = false`. Never `loadUrl("file://…")` with attacker-influenced
   paths.
8. **`addJavascriptInterface` exposes a callable surface to page JS.** Only add it for a page you
   control (bundled asset or a pinned origin), annotate exposed methods with `@JavascriptInterface`,
   and never expose a token, file read, or arbitrary URL fetch through the bridge.
9. **Load only `https` and pin the origin.** Intercept `shouldOverrideUrlLoading`, reject non-https,
   and do not let the page navigate to `intent://` / `file://` / `javascript:`.
10. **Deep-link parameters are untrusted and are mapped, never concatenated.** Validate scheme/host/
    path against the declared route; parse ids as typed values; never build a file path, SQL query,
    or reflection target from a URI segment.
11. **Do not combine `launchMode="singleTask"`/`singleInstance` with a default `taskAffinity`** unless
    you intend it: an external app can start your task and receive your back stack (task hijacking).
    Set `android:taskAffinity=""` or keep the default launch mode.
12. **Exported receivers are not a broadcast bus.** Prefer `LocalBroadcastManager`-style in-process
    channels or explicit Intents; an exported receiver accepts forged broadcasts.

## Procedure

1. Dump the surface:
   ```bash
   adb shell dumpsys package <pkg> | grep -A3 -E "Activity|Service|Receiver|Provider" | grep -E "exported|permission"
   aapt2 dump xmltree app-release.apk --file AndroidManifest.xml | grep -i exported
   ```
2. For each exported component: write the intended caller and what it validates.
3. Fix `exported`, permissions, and validation per rules 1–2, 6, 12.
4. Grep for redirection and mutability:
   ```bash
   grep -rn "getParcelableExtra(\"next\|startActivity(.*getParcelable\|FLAG_MUTABLE\|addJavascriptInterface\|setAllowFileAccess\|path=\"/\"" --include=*.kt --include=*.xml .
   ```
5. Fix `PendingIntent`, `FileProvider`, `WebView`, deep links per rules 3–5, 7–11.
6. Re-dump the surface and diff against the previous manifest.

## Checklist

- [ ] `android:exported` explicit on every component; `false` unless intended.
- [ ] Exported components validate extras, types, sizes, and Uri scheme/host.
- [ ] No Intent redirection without an allow-list.
- [ ] All `PendingIntent`s immutable, or package-scoped if mutable.
- [ ] `FileProvider` path limited to an export directory; grant revoked after use.
- [ ] `ContentProvider` not exported, or permission + `path-permission` per table.
- [ ] `WebView`: file/content access disabled, JS minimal, bridge only on trusted content.
- [ ] Only `https` loads; navigation override rejects `intent://`/`file://`/`javascript:`.
- [ ] Deep-link params typed and validated; no path/SQL/reflection construction.
- [ ] No `singleTask` + default affinity combination.
- [ ] Exported receivers reviewed or converted to in-process channels.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Any app starts your private screen | `exported="true"` for convenience | `false` + explicit component Intent | public API with no contract |
| Proxy launcher | `startActivity(intent.getParcelableExtra("next")!!)` | allow-list package/component | launches anything, incl. non-exported |
| Notification hijack | `PendingIntent.getActivity(..., 0, i, FLAG_MUTABLE)` | `FLAG_IMMUTABLE` | receiver fills the blank Intent |
| File leak | `FileProvider` `path="/"` | `pathPrefix="exports/"` | grants read to app internals |
| XSS → native | `addJavascriptInterface(this, "app")` on any page | bridge only for bundled/pinned origin | JS reads tokens |
| Local file read | `setAllowFileAccess(true)` + `file://` | disabled + `https` only | `file://` reads arbitrary paths |
| Deep-link path build | `File(getCacheDir(), uri.getQueryParameter("f"))` | validated id, mapped to fixed path | path traversal |

## Verify

```bash
adb shell dumpsys package <pkg> | grep -E "exported=true" -B2
adb shell am start -n <pkg>/.InternalActivity        # must fail: not exported
adb shell am start -a android.intent.action.VIEW -d "yourapp://detail/';--"   # must be rejected
```

Expected: only intended components appear as exported; direct starts of internal components fail
with `Permission Denial`; malformed deep links land on an error state, not a path lookup.

## References

- MASVS-PLATFORM control text (taxonomy only)
- `Intent.FLAG_IMMUTABLE`, `FileProvider.getUriForFile`, `WebSettings` file-access flags
