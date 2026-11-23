---
name: room-persistence
description: >-
  Own the SQLite schema: additive versioned migrations, exported schemas, indices, transactions
  and query shapes that do not scale badly. Use when changing an entity or DAO, writing a
  Migration or AutoMigration, deciding how to store an enum/date/list, adding search, seeing a
  migration test fail, or diagnosing "no such column", "database is locked" and slow list queries.
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - android-developers (Room persistence guide, re-expressed)
    - this-repo (gap analysis: schema work was one rule inside data-layer)
---

# Room Persistence

One decision: **the schema is a versioned public contract with user data behind it.** Treat a
column change like an API change, because rollback is not available once users have the app.

## Use when

- Adding, renaming or removing an entity, column, index, or relation.
- Writing a `Migration`/`@AutoMigration`, or a `MigrationTestHelper` test.
- Choosing the column representation for an enum, a timestamp, a list, or money.
- A query is slow, or the list query reads far more rows than it displays.
- Editing `core/database/`, `**/data/local/**`, or `schemas/`.

## Do not use when

- Deciding the repository contract, caching policy or error type → `data-layer`.
- Deciding page keys, remote mediator or end-of-list → `paging`.
- Migrating an existing database schema from another store (Realm, raw SQLite) → `data-layer`
  first, then this skill for the target schema.

## Rules

1. **`exportSchema = true` and the schema directory is committed.** No exported schema means the
   migration test cannot be written and the next migration is guesswork.
2. **Every schema change ships a `Migration` with a version bump; destructive fallback is banned
   in release builds.** `fallbackToDestructiveMigration()` is acceptable only in a debug-only
   builder branch, never in the instance the release build creates.
3. **Migrations are additive and self-contained.** Each migration does its own work and does not
   read the "current" entity classes — a migration referencing a DAO breaks as soon as the
   entity changes again.
4. **`NOT NULL` + `DEFAULT` + backfill in one migration** for a new column: add nullable, backfill,
   then rely on the default. Never add `NOT NULL` without a default to a populated table.
5. **Rename via `ALTER TABLE ... RENAME COLUMN`; do not drop-and-recreate a table holding user
   data.** Copying rows through a temp table is correct only when the type changes, and then the
   copy must be a single transaction.
6. **Multi-statement writes are `@Transaction` (or `withTransaction` for suspend).** Half-applied
   writes are the visible "some rows updated" bug.
7. **Index every foreign key and every column used in a `WHERE`/`ORDER BY` on a list query.** An
   unindexed FK makes a cascade delete O(n²); an unindexed sort column makes a cached list scan.
8. **Store enums by name with an explicit `UNKNOWN` fallback; store money as integer minor units;
   store time as epoch millis with the timezone stored separately if it matters.** A stored enum
   ordinal reorders silently when someone inserts a member.
9. **Do not serialise a list or object graph into a single column** to avoid a relation table —
   unless it is opaque to queries. If you filter, sort or join on it, it is a table.
10. **DAO reads return `Flow` (cold) or `suspend`; never a blocking call on the main thread.** No
    `allowMainThreadQueries()` in any builder reachable from release.
11. **Chunk `IN (...)` lists and `@Upsert`/batch inserts.** The bind-parameter limit is version
    dependent; a fixed small chunk size is the portable answer.
12. **Use `@Relation`/`@Embedded` deliberately, and know it is an N+1 by default** — a
    `@Transaction` + join query is the fix when the relation is on a list screen.
13. **`addCallback` for `onOpen`/`onDestructiveMigration`; `PRAGMA`/journal settings set once at
    build time.** Losing a required index is a silent performance regression.
14. **Database tests use `inMemoryDatabaseBuilder` + `clearAllTables`, and migration tests run
    against the previous schema version, not the current one.**

## Procedure

1. Change the entity/DAO; bump `@Database(version = ...)`.
2. Write the `Migration(from, to)`; keep it independent of entities and DAOs.
3. Regenerate and commit `schemas/<db>/<new version>.json`.
4. Add a `MigrationTestHelper` test: create at `to - 1`, insert representative rows, run the
   migration, assert both migrated and preserved data.
5. Run the app once against a copy of a real database before shipping (`adb shell run-as` pull).

## Checklist

- [ ] `exportSchema = true`; schema JSON committed.
- [ ] Version bumped; `Migration` present for that step.
- [ ] No destructive fallback in a release-reachable builder.
- [ ] New non-null column has a default or a backfill inside the migration.
- [ ] Table rename uses `RENAME COLUMN`, not drop/recreate.
- [ ] Multi-statement write wrapped in a transaction.
- [ ] Indices present for FK and list-query columns.
- [ ] Enum stored by name with `UNKNOWN`; money as integers; time as epoch millis.
- [ ] Migration test creates the previous version and asserts preserved rows.
- [ ] No `allowMainThreadQueries()`, no blocking DAO call on main.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Data wiped on update | `fallbackToDestructiveMigration()` | versioned `Migration` + test | destroys user data with no recovery |
| Crash after update | migration referencing entity class | self-contained SQL | next entity change breaks old migration |
| "no such column" | edited entity, forgot version bump | bump + migration | Room validates the schema hash |
| List scrolling stalls | no index on sort column | index on `WHERE`/`ORDER BY` | full scan per emission |
| Silent reorder bug | enum stored as ordinal | store by name + `UNKNOWN` | ordinal shifts when a member is inserted |
| Half-saved batch | separate DAO calls | `@Transaction` | partial state visible to observers |
| Slow detail screens | `@Relation` on a list | join query in one DAO method | N+1 queries per row |

## Verify

```bash
./gradlew :core:database:testDebugUnitTest
# migration test must construct the previous version and assert preserved rows
adb -s <serial> shell run-as <pkg> ls databases/
adb -s <serial> shell run-as <pkg> cat databases/<db>-wal | head -c 0   # store exists and is WAL
./gradlew :app:lintDebug --continue 2>&1 | grep -i room                  # no Room lint errors
```

Expected: unit tests and the migration test pass; a real device database pulls, migrates and
still shows the previous content; lint reports no Room schema/query errors.

## References

- Room `Migration`, `@AutoMigration`, `MigrationTestHelper`, `@Transaction`, `withTransaction`
- `RoomDatabase.Builder`: `setJournalMode`, `enableMultiInstanceInvalidation`, `addCallback`
- SQLite `ALTER TABLE RENAME COLUMN` semantics
