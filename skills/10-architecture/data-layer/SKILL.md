---
name: data-layer
description: >-
  Build an offline-first data layer where one source of truth answers every read, network
  results are written to it rather than returned directly, and failures are modelled instead of
  becoming nulls. Use when implementing a Repository, wiring Room and DataStore, deciding what a
  Flow should emit, handling retries and ETags, writing a Room migration, adding Paging, or
  debugging "the list flickers / is empty after rotation / shows stale data".
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - agent-skills-standard (android-persistence, android-networking)
    - agent-skills-standard (android-data-layer) via awesome-android-agent-skills
    - kotlin-footguns (data-layer-footguns, remote-api-footguns)
    - agent-skills-standard (android-architecture)
---

# Data Layer

The data layer's only job: **answer reads from one place, and make writes to that place
transactional.** Everything else is an implementation detail of how that place is kept current.

## Use when

- Creating or changing a Repository, its interface, or its caching behaviour.
- Adding Room entities/DAOs/migrations, or DataStore preferences.
- Deciding whether a `Flow` should be cold (Room query) or hot (`StateFlow`).
- Handling retry, ETag/`If-None-Match`, pagination, or partial failures.
- A screen shows stale data, flickers, or loses data after process death.

## Do not use when

- The question is which layer a class belongs to → `layering`.
- The problem is state ownership in the UI → `compose-state-effects`.
- The problem is DTO field types and nullability at the API edge → `network-dto-safety`.
- Schema changes, migrations, indices and query shape → `room-persistence`.
- Page keys, RemoteMediator and end-of-list detection → `paging`.
- Timeouts, retry policy, auth refresh and interceptor order → `network-client`.

## Rules

1. **One source of truth per data domain, and it is local.** Room/DataStore is authoritative.
   A network response is an *input* written into the local store; it is never returned straight
   to the UI. If you can read the same entity from two places, you have two truths.
2. **Repository returns domain models; never `Entity`, never `Response<T>`, never JSON.** Mapping
   is explicit and lives in the data layer, one mapper per direction, each with a test.
3. **Failure is a value, not `null`.** `Result<T>` or a sealed `DataResult` with
   `Success | Failure.Network | Failure.Http(code) | Failure.Local`. `null` is reserved for
   "genuinely absent" and must be documented where it is allowed.
4. **Reads are cold `Flow` from the store; writes are `suspend`.** A repository read that returns
   `StateFlow` for data owned by the store duplicates state. Exceptions: a genuinely hot stream
   (auth session) that the repository itself owns.
5. **Every network write to the store is a transaction** if it touches more than one table or
   must delete-then-insert. Partial writes are the source of "half the list is old".
6. **Retries only for idempotent reads, with bounded attempts, and never for a 4xx.** Retrying a
   `401` or a `422` multiplies the problem. Backoff lives in one place (an `Interceptor` or a
   `retryWhen` on the repository's network call), not scattered.
7. **Freshness policy is explicit per repository.** One of: cache-first-then-refresh (show local
   immediately, refresh in background), network-first-with-fallback, or local-only. Write which
   one applies in the repository KDoc; mixed ad-hoc behaviour is a defect.
8. **Room migrations are additive and versioned; `fallbackToDestructiveMigration` is forbidden in
   release builds.** Every schema change ships a `Migration` and, if data must be transformed, a
   test that runs it against the previous schema (`MigrationTestHelper`).
9. **Small scalars go in DataStore, structured data in Room.** Do not build a key-value soup in
   Room, do not serialise a list into a preference string.
10. **The repository owns the clock and the paging.** Inject a `Clock`/time source (so tests are
    deterministic) and put `PagingSource`/remote-mediator inside the data layer, not the ViewModel.
11. **DTO field changes must not ripple.** Because of rule 2, an API rename stops at the mapper.
    If a DTO rename breaks a ViewModel, rule 2 was violated somewhere.

## Procedure

1. Write the repository interface in `domain` with domain types and rule-3 error type.
2. In `data`, define Entity + DAO (Room) or the DataStore keys; one table per aggregate.
3. Write `Entity ↔ domain` mappers; test round-trip.
4. Implement the read path: `dao.observe(): Flow<Entity>` → `map` → domain.
5. Implement the write path: fetch → map → transaction insert → (optionally) re-read.
6. Declare the freshness policy in KDoc (rule 7) and implement exactly that.
7. Add a migration when the schema changes; add `MigrationTestHelper` test.
8. Test: empty store, populated store, network failure with populated store (must still emit local
   data), and a corrupt/partial write.

## Checklist

- [ ] Repository interface in `domain`; implementation in `data`.
- [ ] No `Entity`/`Response`/JSON type crosses the repository boundary.
- [ ] Local store is the only read path for cached data.
- [ ] Errors are modelled; no `?: null` on a failed call.
- [ ] Multi-table network write wrapped in a transaction.
- [ ] Freshness policy documented per repository and implemented as documented.
- [ ] Room schema change has a `Migration` + test; destructive fallback absent in release.
- [ ] `Clock`/time source injected, not read statically.
- [ ] Mappers round-trip tested.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Empty list after rotation | repository returns network `List` | write to Room, read Room | no local truth |
| Stale list after refresh | update cache but keep returning response | response → cache → Flow | UI bypasses the store |
| "Error = null" | `suspend fun movies(): List<Movie>?` | `Result<List<Movie>>` | absent vs failed collapse |
| Duplicated list state | `StateFlow` in repo + `StateFlow` in VM | cold Flow from Room | two truths drift |
| Retry storm | `retry()` on all calls | bounded, idempotent, non-4xx | amplifies outage |
| Data loss after update | `fallbackToDestructiveMigration()` | versioned `Migration` | wipes user data |
| Flaky time tests | `System.currentTimeMillis()` in repo | injected `Clock` | untestable, timezone bugs |
| Partial update | two separate DAO calls | `@Transaction` | half-written state visible |

## Verify

```bash
./gradlew :core:data:test
# migration test must run against the previous schema version
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=MigrationTest
adb -s <serial> shell run-as <pkg> cat databases/<db>-wal 2>/dev/null | head -c 0   # store exists
```

Offline check: enable airplane mode (`adb -s <serial> shell cmd connectivity airplane-mode enable`), relaunch,
and confirm the last-known content still renders instead of an empty state.

## References

- Room `@Transaction`, `MigrationTestHelper`, `fallbackToDestructiveMigration` warning
- `dataStore` — `preferencesDataStore` delegate
- `PagingSource` / `RemoteMediator` for paged local-first reads
