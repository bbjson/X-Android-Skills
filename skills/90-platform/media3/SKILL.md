---
name: media3
description: >-
  Play audio/video with Media3 ExoPlayer correctly: one player with an explicit owner, a MediaSessionService
  for background playback, audio focus, and a release path. Use when adding playback, when audio keeps
  playing after leaving the screen, when playback stops when the app is backgrounded, or when another
  app's audio does not resume.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - android-skill (media3-cast)
    - kotlin-footguns (media-playback-footguns)
    - agent-skills-standard (android-background-work)
    - android-agent-engineering (android-architecture)
---

# Media3 Playback

Playback has **an owner with a lifetime**, and that lifetime is almost never "the Activity". Getting
the owner right prevents both "audio after exit" and "stops on background".

## Use when

- Adding audio or video playback (ExoPlayer/Media3).
- Audio continues after leaving the screen, or stops when the app is backgrounded.
- Adding a media notification / lock-screen controls.
- Another app's audio does not resume after yours pauses.
- Adding Chromecast (CastPlayer) to an existing Media3 setup.

## Do not use when

- The task is capturing media → `camera`.
- The task is notifications unrelated to playback → `notifications-fcm`.
- The task is a short sound effect → `SoundPool`, not a media session.

## Rules

1. **One player instance per playback session, owned by something that outlives the UI.** For
   background playback the owner is a `MediaSessionService`; for foreground-only playback a
   `ViewModel` is acceptable. An `ExoPlayer` created in a Composable is created once per recomposition.
2. **Background playback requires a `MediaSessionService` with foreground service type `mediaPlayback`.**
   Without the service (and the manifest permission/type), playback stops when the app leaves the
   foreground — by design, not by bug.
3. **Always `release()` the player** in the owner's `onDestroy`/`onCleared`. A leaked ExoPlayer holds the
   audio device, the wakelock and the notification.
4. **Request audio focus and handle loss.** `AudioFocusRequest` with `AUDIOFOCUS_GAIN` for music;
   pause on `AUDIOFOCUS_LOSS`, duck or pause on transient loss. Not handling it means other apps'
   audio never resumes and the user blames them.
5. **The media notification comes from the session, not hand-built.** ExoPlayer + `MediaSession`
   + the Media3 notification provider gives correct actions, artwork and dismissal semantics; a custom
   notification drifts from player state.
6. **`MediaItem` metadata is what the notification and lock screen show.** `setMediaMetadata(title,
   artist, artworkUri)` — missing metadata is why the lock screen shows an empty card.
7. **Handle `PlaybackException` explicitly**: network loss, unsupported format, DRM failure. Map each to
   a UI state; an unhandled error is a silent stop.
8. **In Compose, host the player surface via `AndroidView`/`PlayerView` or `player.setVideoSurfaceView`**,
   and detach the surface when the composable leaves composition — a held surface prevents release.
9. **Do not play in `onCreate` unconditionally.** Resume only if the session/notification says so;
   otherwise the app starts playing from a cold notification tap in the wrong place.
10. **For Cast (optional), the `CastPlayer` replaces the local player in the same `MediaSessionService`**;
    switching the player type must not lose the queue or the session id.
11. **Test on a device with another audio app**: play music, start a call-like audio app, verify
    pause/duck/resume and focus behaviour; and verify the notification disappears on stop.

## Procedure

1. Decide the owner: service (background) or ViewModel (foreground only).
2. Create the player in the owner; build `MediaSession`; expose it to the UI.
3. Wire audio focus + becoming-noisy (headphone unplug) handling.
4. Enable the Media3 media notification; add metadata to every `MediaItem`.
5. In the UI, host the surface and observe player state; do not create players.
6. Release on owner destruction; clear the notification on stop.
7. Test background/foreground, focus loss, and another app's audio resuming.

## Checklist

- [ ] Player created in an owner that outlives the screen.
- [ ] Background playback uses a `MediaSessionService` with `mediaPlayback` foreground type.
- [ ] `release()` wired to the owner's destruction.
- [ ] Audio focus requested; loss/transient loss handled.
- [ ] Notification generated from the session, not hand-built.
- [ ] Every `MediaItem` has title/artist/artwork metadata.
- [ ] `PlaybackException` mapped to a UI state.
- [ ] Compose surface detached on disposal.
- [ ] Resume policy avoids playing on cold start.
- [ ] Verified: another app's audio resumes; notification clears on stop.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Audio after exit | player in Activity, no release | release in owner | leaked player |
| Stops on background | no `MediaSessionService` | service + foreground type | system stops it |
| Others never resume | no audio focus handling | request + handle loss | broken interop |
| Empty lock screen | no metadata | `MediaMetadata` per item | session shows nothing |
| Player per recomposition | `ExoPlayer` in Composable | owner-held player | resource churn |
| Silent stop | ignore `PlaybackException` | map to state | user sees nothing |
| Wrong start on tap | play in `onCreate` | resume per session state | plays unexpectedly |

## Verify

```bash
adb shell dumpsys media_session | grep -A5 "package=<pkg>"
adb shell dumpsys audio | head -40      # focus ownership
adb shell am force-stop <pkg> && adb shell dumpsys media.audio_flinger | head
```

Expected: the session is owned by the service, audio focus is held while playing, playback survives
backgrounding, and after `force-stop` no audio continues.

## References

- `androidx.media3:media3-exoplayer`, `media3-session`, `media3-ui`
- `AudioFocusRequest`, `MediaSessionService`, `MediaNotification`
