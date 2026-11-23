---
name: background-work
description: >-
  Run work that must outlive a screen with the right mechanism: WorkManager for deferrable and
  guaranteed jobs, exact alarms for user-facing time, foreground services with declared types for
  long-running visibility. Use when adding a sync, upload, retry queue or scheduled job, when work
  never runs on some devices, when it runs twice, or when a foreground service crashes on start.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - android-developers (WorkManager, Doze/App Standby, FGS types, re-expressed)
    - this-repo (gap analysis: background execution absent except one media rule)
---

# Background Work

One decision: **which guarantee the work needs** — "eventually, even after reboot" (WorkManager),
"at this wall-clock time" (alarm), or "must keep running now, visibly" (foreground service). Choosing
by habit gives work that silently never runs.

## Use when

- Adding sync, upload, download, cleanup, retry queue, or any "do this later" task.
- A worker never runs on some OEMs, in battery saver, or after the app is force-stopped.
- A job runs twice, or loses progress when the process dies.
- A foreground service fails to start, or Play flags a missing service type.
- Deciding between `WorkManager`, `AlarmManager`, a foreground service and a plain coroutine.
- Cancelling pending work on logout or account switch.

## Do not use when

- The work must finish while the screen is alive → `structured-concurrency` with `viewModelScope`.
- Media playback backgrounding and audio focus → `media3`.
- Widget refresh scheduling → `app-widgets`.
- Notification channels and tap targets rather than the job itself → `notifications-fcm`.

## Rules

1. **Pick the mechanism by guarantee:** deferrable + should eventually happen = `WorkManager`;
   exact wall-clock = `AlarmManager` (with the exact-alarm capability, and only for user-facing
   time); must keep running and be visible = foreground service; happens while the user watches =
   a coroutine.
2. **Nothing guarantees immediacy.** Workers are deferred by Doze and App Standby; a periodic
   worker's interval is a floor, not a schedule, and its start time drifts. User-facing "at 07:00"
   is an alarm, not a periodic worker.
3. **Unique work with an explicit policy.** `enqueueUniquePeriodicWork` with
   `KEEP`/`UPDATE`/`REPLACE` — chosen, not defaulted — otherwise every app start stacks another
   chain of jobs.
4. **Workers are idempotent and resumable.** The process can die mid-worker; the run may repeat.
   Key the write on a stable id, and checkpoint progress so a retry does not restart from zero.
5. **`Result.retry()` only for transient failures, and only with backoff configured.** Retrying a
   `400` or a permission failure burns battery forever; `Result.failure()` is the correct answer
   when the input is bad.
6. **Constraints encode the requirement, not a wish.** `NetworkType.CONNECTED`,
   `requiresBatteryNotLow`, `requiresStorageNotLow`, `requiresCharging` are all re-evaluated before
   the run; a worker whose constraint is never satisfied is invisible work, so log when a chain
   stays blocked.
7. **A long worker declares a foreground service type in the manifest and passes it to
   `setForeground`.** Modern Android requires the declared type and its permission; the types have
   different time budgets, and a data-sync type has a daily cap. Running without the type throws at
   runtime.
8. **The foreground notification is mandatory and must be honest** — a real title, a progress value
   and a cancel action. A placeholder notification gets the app reported and the service killed.
9. **`force-stop` is a hard boundary.** After the user force-stops the app (or some OEMs do it for
   them), jobs and alarms do not run until the app is launched again. Do not design a guarantee that
   assumes otherwise; use push or a sync-on-launch reconciliation.
10. **Cancel by account on logout.** Tag or name unique work per account and cancel it when the
    session ends, or the next user's launch uploads the previous user's queue.
11. **Reconcile on launch.** Whatever the queue missed while force-stopped must be repaired by a
    start-up sync that compares local pending state with the server, not by hoping the worker fired.
12. **Test the worker with the test initialiser, and test the constraint paths** (network lost,
    retry, cancellation) rather than only the happy path.

## Procedure

1. Name the guarantee; pick the mechanism from rule 1 and write it in the worker's KDoc.
2. Enqueue as unique work with an explicit existing-work policy and constraints.
3. Make the worker idempotent, with a stable key and a checkpoint.
4. If long-running, declare the service type and build a real foreground notification.
5. Add logout cancellation and start-up reconciliation.
6. Test: success, transient failure → retry, permanent failure, cancellation, constraint never met.

## Checklist

- [ ] Mechanism matches the guarantee (worker / alarm / foreground service / coroutine).
- [ ] No exact-time requirement implemented with a periodic worker.
- [ ] Unique work name + explicit `ExistingWorkPolicy`/`ExistingPeriodicWorkPolicy`.
- [ ] Worker idempotent with a stable key and a checkpoint.
- [ ] `retry()` bounded to transient failures; backoff configured.
- [ ] Constraints express real requirements; blocked chains are logged.
- [ ] Foreground service type declared in manifest, passed to `setForeground`, permission present.
- [ ] Foreground notification is real and cancelable.
- [ ] Force-stop/reboot recovery handled by reconciliation on launch.
- [ ] Work cancelled on logout, per account.
- [ ] Tests cover success, retry, failure, cancel, unsatisfiable constraint.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Sync at a user-chosen time | periodic worker | exact alarm | interval is a floor |
| Duplicate jobs | default enqueue | unique work + policy | one chain per launch |
| Work never runs | battery constraint "for safety" | only real constraints | permanently blocked |
| Crash on start | `setForeground` without type | declare type + permission | runtime exception |
| Re-uploads already-uploaded rows | no stable key | idempotent key/checkpoint | retry duplicates |
| Old user's data uploaded | no cancel on logout | cancel by account | data leak across accounts |
| Infinite retry | `retry()` on 4xx | `failure()` | battery drain, no progress |

## Verify

```bash
./gradlew :app:testDebugUnitTest --tests '*Worker*'
adb -s <serial> shell dumpsys jobscheduler | grep -A6 '<pkg>' | head -40
adb -s <serial> shell cmd deviceidle force-idle     # then confirm work is deferred, not lost
adb -s <serial> shell cmd deviceidle unforce
adb -s <serial> shell am set-standby-bucket <pkg> rare
adb -s <serial> shell dumpsys activity services <pkg> | head -20   # foreground service + type
```

Expected: the job appears in JobScheduler with its constraints, entering Doze defers rather than
drops it, the bucket change is reflected, and any long-running service reports its declared type.

## References

- `WorkManager`: `enqueueUniquePeriodicWork`, `ExistingPeriodicWorkPolicy`, `Constraints`,
  `setBackoffCriteria`, `setForeground`, `WorkManagerTestInitHelper`
- Foreground service types and their time budgets
- Doze, App Standby buckets, `cmd deviceidle`, `am set-standby-bucket`
