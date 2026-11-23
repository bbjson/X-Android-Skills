---
name: ipc-and-multiprocess
description: >-
  Add a second process or a Binder interface deliberately: what re-initialises per process, which
  state cannot be shared, how large payloads cross, and how a remote service is unbound when it
  dies. Use when adding android:process, a bound service, AIDL/Messenger, a ContentProvider, or when
  a feature works in the main process and silently fails in the remote one.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - android-developers (processes and app lifecycles, bound services, AIDL, re-expressed)
    - this-repo (gap analysis: no IPC skill; multiprocess pitfalls unrecorded)
---

# IPC and Multiple Processes

One decision: **whether a second process is justified at all.** It buys isolation and crash
containment, and costs you every assumption your app makes about shared state.

## Use when

- Adding `android:process` to a component (WebView isolation, a large native library, a plugin host).
- Exposing or consuming a bound service (`Messenger`, AIDL) or a custom `ContentProvider`.
- State set in one process is missing, default, or stale in another.
- A binder call fails with `TransactionTooLargeException` or the remote dies mid-call.
- Initialisation runs twice, or a crash in a service takes down unrelated functionality.

## Do not use when

- Sharing data between apps you do not own → `component-exposure` (and prefer an explicit API).
- Background jobs that should outlive the screen → `background-work`.
- Persistence and multi-writer storage questions → `room-persistence`, `data-layer`.
- Security of an exported component → `component-exposure`.

## Rules

1. **Justify the process in writing.** Isolation for a crash-prone native library or a WebView is a
   reason; "performance" is not, and a second process costs memory and startup time.
2. **`Application.onCreate` runs once per process.** Initialise per-process work guarded by the
   process name (`Application.getProcessName()`), or every process pays for every dependency and
   inits things it does not own.
3. **Statics, singletons and in-memory caches are per process.** Anything shared must be persisted or
   fetched over IPC; a singleton "working" in debug is two singletons in release.
4. **`SharedPreferences` is not multi-process safe, and DataStore is single-process by design.** For
   shared preferences across processes, use a single writer process and read through IPC, or use
   Room with multi-instance invalidation.
5. **Room needs `enableMultiInstanceInvalidation()` when more than one process opens the same
   database**, and even then each process holds its own connection.
6. **Binder transactions are size-limited** (the whole transaction buffer is shared and roughly a
   megabyte). Pass a file descriptor/URI/stream for large payloads instead of a serialized object.
7. **Prefer `Messenger` unless you need concurrent callbacks or complex types**, and mark
   fire-and-forget methods `oneway` so the caller is not blocked on a slow callee.
8. **A remote can die at any time.** Register a `DeathRecipient`, clear the binder, rebind, and let
   the UI show a retry — a dead binder object throws on every call afterwards.
9. **Bind and unbind in pairs with the lifecycle**, and `exported=false` for every internal service or
   provider. An exported AIDL service is an attack surface with no authentication.
10. **`ContentProvider.onCreate` runs before `Application.onCreate` in the process that hosts it**, so
    provider work is on the critical path of every process that declares it; keep it to opening
    handles, never to network or migrations.
11. **Cross-process broadcasts are explicit** (`setPackage`, `exported=false`, signature permission);
    an implicit broadcast between your own processes is a leak waiting for another app to receive.
12. **A secondary process can be killed independently of the UI**, so it must be able to rebuild its
    state from storage and must not be the only holder of it.

## Procedure

1. Write down the reason for the extra process and what state it owns.
2. Guard initialisation by process name; remove cross-process assumptions (statics, prefs, caches).
3. Choose the channel: `Messenger` for simple messages, AIDL for typed concurrent calls, provider for
   data-shaped access.
4. Add `DeathRecipient` + rebind, and `exported=false`.
5. Test: kill the remote process (`am kill`), send a large payload, and verify recovery.

## Checklist

- [ ] Extra process has a written justification and an owner for its state.
- [ ] Initialisation guarded by process name.
- [ ] No shared statics/singletons assumed across processes.
- [ ] No multi-process `SharedPreferences`/DataStore assumption.
- [ ] Room configured with multi-instance invalidation where two processes open it.
- [ ] Large payloads cross as descriptors, not serialized blobs.
- [ ] `oneway` used for fire-and-forget methods.
- [ ] `DeathRecipient` + rebind path implemented.
- [ ] Bind/unbind paired; service/provider `exported=false`.
- [ ] Provider `onCreate` does no network or heavy migration.
- [ ] Cross-process broadcasts explicit and permission-guarded.
- [ ] Remote-process kill tested.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Config set in UI ignored in service | shared object | persisted value or IPC | one instance per process |
| Startup doubled | init everything in `onCreate` | guard by process name | per-process onCreate |
| Prefs out of sync | `SharedPreferences` both processes | single writer + IPC | prefs are not cross-process safe |
| `TransactionTooLargeException` | serialize a big object | pass a URI/descriptor | binder buffer limit |
| UI freezes on call | sync AIDL method | `oneway` or async callback | caller blocks on callee |
| Crash after remote restart | cached binder | `DeathRecipient` + rebind | dead binder throws |
| Slow cold start | migration in provider `onCreate` | lightweight provider init | runs before Application |

## Verify

```bash
adb -s <serial> shell ps -A | grep '<pkg>'
adb -s <serial> shell dumpsys activity processes | grep -A4 '<pkg>'
adb -s <serial> shell am kill <pkg>:remote
adb -s <serial> logcat -d | grep -iE 'DeadObjectException|TransactionTooLarge' | tail -20
```

Expected: the expected processes appear, killing the remote does not kill the UI, the next IPC call
rebinds and succeeds, and no `TransactionTooLargeException` or `DeadObjectException` reaches the user.

## References

- `android:process`, `Application.getProcessName`, per-process `Application`
- `Messenger`, AIDL, `oneway`, `IBinder.DeathRecipient`, `bindService`
- `RoomDatabase.Builder.enableMultiInstanceInvalidation`
- `ContentProvider.onCreate` ordering, `TransactionTooLargeException`
