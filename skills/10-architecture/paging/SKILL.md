---
name: paging
description: >-
  Wire Paging 3 so a list loads in bounded windows from the local store, remote mediation is
  keyed and idempotent, and every load state has a visible outcome. Use when adding an infinite
  or paged list, writing a PagingSource or RemoteMediator, seeing duplicate pages or a list that
  resets on refresh, deciding page size, or when the list jumps, loops or re-fetches page one.
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - android-developers (Paging 3 guide, re-expressed)
    - this-repo (gap analysis: Paging named in three skills, owned by none)
---

# Paging

One decision: **who owns the page cursor** — the database (local-first, `RemoteMediator`) or the
network (`PagingSource`). Mixing the two is what produces duplicated pages and refresh loops.

## Use when

- Adding a list that can grow beyond one screen of server data.
- Implementing `PagingSource` or `RemoteMediator`, or migrating from manual offset lists.
- The list duplicates rows, skips rows, resets to the top, or re-fetches page 1 on every scroll.
- Deciding `pageSize`, `prefetchDistance`, `initialLoadSize`, or placeholders.
- Connecting Room to the UI through paging.

## Do not use when

- The list is a fixed local dataset → `lazy-layouts`.
- The repository contract, transaction and caching policy → `data-layer`.
- The schema, indices and migration that back the cursor → `room-persistence`.
- Item stability, keys for animation and heterogeneous content types → `lazy-layouts`.

## Rules

1. **Pick one cursor owner.** Offline-first apps use `RemoteMediator` + Room and expose a
   `PagingSource<Int, Entity>` from the DAO. Online-only apps use a `PagingSource` that talks to the
   API and hold no database table. Choose once, in the repository KDoc.
2. **`cachedIn(scope)` is mandatory**, with a scope that outlives recomposition (the ViewModel's).
   A `Pager` flow collected without caching restarts the load on every re-collection.
3. **The `Pager` is constructed once** in the ViewModel or repository, never inside a Composable or
   a `remember` keyed on state. Recreating it is an infinite-load bug, not a perf nit.
4. **`RemoteMediator` honours `loadType`:** `REFRESH` clears the local page table and loads page 1;
   `APPEND` loads the next key only if `state.append.endOfPaginationReached` is false; `PREPEND` is
   implemented or explicitly returns `endOfPaginationReached = true` — never "ignore and return
   success", which loops forever.
5. **Remote keys are persisted with the rows, in the same transaction.** Deriving the next key from
   "rows currently in the table" breaks as soon as a background delete runs.
6. **Every local write from a page load is one transaction** (insert rows + upsert remote keys).
   Two writes means an observable state where rows exist without their keys.
7. **Deduplicate by a stable remote id.** A feed that inserts newer items while you paginate will
   duplicate rows unless the insert is upsert-on-conflict by remote id.
8. **`itemKey` is set for the UI** so scroll position survives a refresh; `contentType` is set when
   the list has heterogeneous items (see `lazy-layouts`).
9. **Placeholders off when item height varies.** `enablePlaceholders = true` with variable heights
   makes the scrollbar lie and the list jump on insert.
10. **`maxSize` is bounded.** Unbounded in-memory pages grow until the process dies; the database is
    the unbounded store, the UI window is not.
11. **Three load states, three UI outcomes.** Refresh failure replaces content with an error +
    retry; append failure shows a footer with retry; append loading shows a footer spinner. A single
    `isLoading` boolean cannot express this.
12. **`retry()` is wired to the failed state that failed**, not to a generic refresh button.
13. **Paging tests assert the sequence of pages**, not just the first page: `asSnapshot()` over a
    fake source, plus a mediator test that runs `REFRESH` twice and asserts no duplicated rows.

## Procedure

1. Add the entity + DAO read (`PagingSource`) and, for offline-first, an entity for remote keys.
2. Write `RemoteMediator.load` with the three `loadType` branches from rule 4.
3. Build the `Pager` in the repository; `cachedIn` in the ViewModel.
4. Expose `Flow<PagingData<DomainModel>>`; map entities to domain inside the data layer.
5. In Compose: `collectAsLazyPagingItems()`, then render the three states separately.
6. Test refresh-twice, append-error, and end-of-list.

## Checklist

- [ ] One cursor owner documented; no mixed source.
- [ ] `cachedIn` applied with a ViewModel-lifetime scope.
- [ ] `Pager` created once; nothing rebuilds it on recomposition.
- [ ] `RemoteMediator` handles all three `loadType`s without an infinite loop.
- [ ] Remote keys persisted in the same transaction as the rows.
- [ ] Upsert keyed on a stable remote id.
- [ ] `itemKey`/`contentType` set for the list.
- [ ] `maxSize` bounded; placeholders off for variable heights.
- [ ] Refresh/append/end states rendered distinctly, each with its own retry.
- [ ] Tests: refresh twice without duplicates; append failure; end of pagination.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Infinite load loop | `PREPEND` returns success | `endOfPaginationReached = true` | mediator keeps asking |
| List resets on scroll | `Pager` built in composable | built once, `cachedIn` | new source per collection |
| Duplicated rows | insert without conflict strategy | upsert by remote id | overlapping pages both inserted |
| Jumping scrollbar | placeholders on, variable height | placeholders off | estimated item height wrong |
| Stuck blank list | one `isLoading` flag | three load states | append error hides content |
| OOM after long scroll | `maxSize` unbounded | bounded window + DB | memory grows per page |
| Refresh loses position | no `itemKey` | stable `itemKey` | items rebuilt by index |

## Verify

```bash
./gradlew :core:data:testDebugUnitTest
# mediator test: run REFRESH twice, assert row count and no duplicate remote ids
./gradlew :app:assembleDebug
adb -s <serial> logcat -d | grep -i -E 'paging|PagingSource' | tail -20   # no repeated REFRESH
```

Expected: paging tests green (including refresh-twice idempotency); scrolling a long list in the
debug build produces no repeated full refresh and no duplicate rows.

## References

- Paging 3: `PagingSource`, `RemoteMediator`, `PagingConfig`, `cachedIn`, `LoadState`
- `collectAsLazyPagingItems`, `LazyPagingItems.retry`
- `paging-testing` `asSnapshot()`
