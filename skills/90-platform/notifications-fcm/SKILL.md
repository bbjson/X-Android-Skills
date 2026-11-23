---
name: notifications-fcm
description: >-
  Deliver push and local notifications that users do not disable: one channel per intent, runtime
  permission, immutable tap intents, grouped summaries, and FCM token/message handling that works when
  the app is backgrounded. Use when adding push, when notifications never appear, when they appear on
  the wrong channel, when tapping opens the wrong screen, or when a token stops working after reinstall.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - agent-skills-standard (android-notifications)
    - agent-skills-standard (android-background-work)
    - pushengage-skills (pushengage-android)
    - component-exposure (intent safety rules reused)
---

# Notifications and FCM

A notification is **a channel id, an importance, and an intent**. All three are set by the app and by
nobody else; the platform will not fix a wrong channel.

## Use when

- Adding FCM push or local notifications.
- Notifications never appear, or appear silently (no heads-up).
- A notification lands on the wrong channel, or the channel settings cannot be changed.
- Tapping a notification opens the wrong screen, or a duplicate.
- FCM token stops working after reinstall/restore.

## Do not use when

- The notification is media playback → `media3` (session-provided notification).
- The concern is the deep link target/validation → `deep-links` / `component-exposure`.
- The concern is background work scheduling (WorkManager, long-running jobs) — not here; see the
  platform docs for `WorkManager`.

## Rules

1. **One channel per user-facing intent**, created at startup, with a stable id and an importance that
   matches the intent. Types: messages (high), reminders (default), promotions (low). A single
   "Default" channel means users can only mute everything.
2. **Channel importance cannot be changed after creation.** Changing `IMPORTANCE_HIGH` to `LOW` on an
   existing id silently does nothing; to change behaviour you must create a *new* channel id.
3. **Request `POST_NOTIFICATIONS` at a moment the user understands**, not on first launch. Denial is
   permanent-ish; a denied app that keeps prompting is uninstalled.
4. **FCM `notification` payload vs `data` payload have different behaviour.** A `notification` message is
   displayed by the system when the app is backgrounded (your code does not run); a `data` message
   always goes to `onMessageReceived` and you build the notification yourself. Mixed payloads are the
   usual cause of "works in foreground, not in background".
5. **Build data-message notifications with a channel id that exists**, otherwise the notification is
   dropped silently on newer API levels.
6. **The tap `PendingIntent` must be `FLAG_IMMUTABLE` and target an explicit component or a validated
   deep link.** A mutable/implicit tap intent is a hijack vector (`component-exposure` rule 4).
7. **One notification per logical item, updated in place, not a new id each time.** Use a stable
   `notify(id)` with the same id to update; a per-message random id floods the shade.
8. **Group related notifications** with `setGroup(key)` and a `setGroupSummary(true)` summary; without
   the summary, the group is not collapsible on all versions.
9. **Refresh and re-register the FCM token.** `onNewToken` plus a refresh on app start; token can change
   after reinstall, restore, or data clear. A stale token on the server means silent non-delivery.
10. **Respect the user's choices**: a notification dismissed by the user must not reappear from a
    stale local retry, and a channel the user disabled must not be worked around by another channel.
11. **Never put a secret in the payload.** FCM payloads travel through Google and appear in logs; send an
    id and fetch content authenticated.

## Procedure

1. Define channels (id, name, importance) and create them in `Application.onCreate` (idempotent).
2. Add `POST_NOTIFICATIONS` request at a contextual moment; handle denial without nagging.
3. Implement `FirebaseMessagingService.onMessageReceived` + `onNewToken`; log and register the token.
4. Build notifications with rule 5–8 (channel, stable id, immutable PendingIntent, group).
5. Handle the tap: explicit component or validated route; verify with `adb shell am start` equivalent.
6. Test: foreground, background, killed app (`force-stop`), doze, and channel-disabled.

## Checklist

- [ ] One channel per intent, created idempotently.
- [ ] Importance matches intent; no reuse of a channel with a changed importance.
- [ ] `POST_NOTIFICATIONS` requested contextually; denial handled.
- [ ] Foreground/background/killed behaviour understood for the payload type used.
- [ ] Data-message notifications use an existing channel id.
- [ ] Tap `PendingIntent` immutable with an explicit/validated target.
- [ ] Stable notification id per item; updates replace, not duplicate.
- [ ] Group + summary set for related notifications.
- [ ] Token refreshed (`onNewToken` + startup) and re-registered.
- [ ] No secrets in the payload.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Users mute everything | one "Default" channel | one per intent | granular control lost |
| Importance change ignored | reuse channel id | new channel id | platform ignores change |
| Silent in background | `notification` payload + in-app logic | data payload + own notification | system displays it |
| Dropped on Android 13+ | data message, no channel | existing channel id | silently discarded |
| Flooded shade | new id per message | stable id | unreadable notification list |
| Wrong screen on tap | implicit intent, no validation | explicit component / validated link | hijack + wrong target |
| Push stops after reinstall | cached token | refresh on start + `onNewToken` | stale token |

## Verify

```bash
adb shell dumpsys notification --noredact | grep -A6 "<pkg>"
adb shell dumpsys notification --noredact | grep -A6 "<pkg>"   # channel ids + importance
adb shell pm revoke <pkg> android.permission.POST_NOTIFICATIONS   # denial path
adb shell am force-stop <pkg>   # then send a test push
```

Expected: each channel appears with its intended importance, background/killed delivery works with the
declared payload type, and a disabled channel results in no notification rather than a fallback.

## References

- Notification channels, `POST_NOTIFICATIONS`, `NotificationCompat`
- `FirebaseMessagingService` (`onMessageReceived`, `onNewToken`), payload types
