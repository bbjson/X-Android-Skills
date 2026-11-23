---
name: permissions-and-pickers
description: >-
  Ask for the minimum access at the moment it is needed, distinguish "not asked" from "permanently
  denied", and pick content with Photo Picker or the Storage Access Framework instead of a broad
  permission. Use when adding camera/location/notification/media/file access, when the app is
  denied and dead-ends, when a file URI works once and then fails, or when a targetSdk upgrade
  changed what a permission means.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - android-developers (runtime permissions, photo picker, SAF, re-expressed)
    - this-repo (gap analysis: permissions were one line inside two platform skills)
---

# Permissions and Pickers

One decision: **do you need the permission at all?** Most "file access" and "photo access" needs are
satisfied by a picker that returns one URI and requires no permission.

## Use when

- Adding camera, microphone, location, notification, body-sensor or media access.
- A screen must choose a photo, video, document or directory.
- A user denies access and the screen has nowhere to go.
- A saved URI stops working after a process restart or a reboot.
- A targetSdk bump changed media or notification permission behaviour.

## Do not use when

- The permission is a symptom of a wrong design (share a file, don't read the whole store) —
  see `component-exposure` for the inbound side.
- Notification channels, importance and tap behaviour → `notifications-fcm`.
- Camera preview/capture lifecycle itself → `camera`.
- Deciding what the Data Safety form must declare → `data-safety-compliance`.

## Rules

1. **Prefer a picker to a permission.** `PickVisualMedia` returns the user's chosen items with no
   media permission; `OpenDocument`/`CreateDocument` gives per-file access with no storage
   permission. A broad permission is a fallback, not a default.
2. **Ask at the point of use, with a pre-ask explanation.** Requesting at first launch trains users
   to deny; a one-line rationale before the system dialog raises grant rates and satisfies
   "explain why" requirements.
3. **Distinguish the three states explicitly**: not yet asked, denied (can ask again), permanently
   denied (system dialog will not appear). `shouldShowRequestPermissionRationale` is false in both
   the first and the permanent case, so persist "we have asked" and route the permanent case to app
   settings.
4. **Every denial path has a working alternative.** Deny location → manual location entry; deny
   photos → picker limited to selection; deny notifications → in-app inbox. A dead-end screen is a
   defect.
5. **Never persist a decision as "granted forever".** Permissions can be revoked, auto-reset for
   unused apps, and granted only for one session; check at use time every time.
6. **Handle partial and one-time grants.** Media visual access can be "selected photos only", and
   location can be approximate or granted until the app leaves the foreground; the code path for
   "some access" is not the full-access path.
7. **Background location is a separate, later request** with its own rationale and, on modern
   targets, its own settings flow. Bundling it with foreground location gets the whole request
   denied.
8. **Persistable URI access is taken explicitly and revalidated on read.** `takePersistableUriPermission`
   at pick time, then handle a `SecurityException` on later reads (the grant can be revoked, the
   file deleted, or the provider changed) and ask the user to re-pick.
9. **Declare only the permissions the app uses, with the narrowest variant** (coarse location before
   fine, no `WRITE_EXTERNAL_STORAGE` for app-private files, no `MANAGE_EXTERNAL_STORAGE` unless the
   product genuinely is a file manager). Extra declarations are a policy risk, not a safety margin.
10. **Notification permission is part of the feature, not a launch step.** Ask where notifications
    are meaningful, and use a channel that the user would recognise.
11. **Test the refusal paths, not just the grant path**: deny once, deny permanently, revoke in
    settings while the app is running, one-time grant expiry, partial media access.

## Procedure

1. Decide the minimum capability: picker, per-file grant, or runtime permission.
2. Add the launcher contract (`RequestPermission`, `PickVisualMedia`, `OpenDocument`) in the screen's
   owner, not in a random callback.
3. Implement the three-state handling plus the degraded path.
4. Persist URI grants where the access must outlive the screen; wrap reads in `try/catch`.
5. Test each refusal path with `pm revoke` and the settings screen.

## Checklist

- [ ] Picker used where a picker suffices; no broad storage permission.
- [ ] Request happens at point of use, after a rationale.
- [ ] Three states distinguished; permanently denied routes to settings.
- [ ] Every denial has a working alternative.
- [ ] Permission checked at use time, not cached as a boolean.
- [ ] Partial/one-time/approximate grants handled as distinct paths.
- [ ] Background location requested separately, later.
- [ ] Persistable URI permission taken and revalidated; `SecurityException` handled.
- [ ] Manifest declares only used permissions, narrowest variant.
- [ ] Notification permission requested in context.
- [ ] Refusal paths covered by a test or a manual matrix.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| User stuck | dialog dismissed, screen empty | degraded path + settings link | dead end |
| Request ignored forever | check only `shouldShow...` | track "asked" separately | false for never-asked |
| URI works once | `content://` kept without grant | `takePersistableUriPermission` | grant is per-session |
| Whole gallery access | `READ_MEDIA_IMAGES` | `PickVisualMedia` | no permission needed |
| Crash after revoke | assume granted | check at use, catch `SecurityException` | permissions change |
| Background location denied | request all at once | foreground first, background later | bundled request denied |
| Play policy flag | `MANAGE_EXTERNAL_STORAGE` "just in case" | app-scoped storage / SAF | restricted permission |

## Verify

```bash
adb -s <serial> shell pm revoke <pkg> android.permission.POST_NOTIFICATIONS
adb -s <serial> shell pm revoke <pkg> android.permission.ACCESS_FINE_LOCATION
adb -s <serial> shell dumpsys package <pkg> | grep -A12 'runtime permissions'
adb -s <serial> shell am start -n <pkg>/.MainActivity
```

Expected: after each revoke the app opens the affected screen with a rationale and a working
alternative instead of a dead end, and the permanent-denial path opens app settings.

## References

- `ActivityResultContracts.RequestPermission`, `RequestMultiplePermissions`
- `PickVisualMedia`, `PickMultipleVisualMedia`, `OpenDocument`, `CreateDocument`
- `takePersistableUriPermission`, `MediaStore`, scoped storage
- `shouldShowRequestPermissionRationale`, one-time permissions, permission auto-reset
