---
name: layering
description: >-
  Decide and enforce which Android module and layer owns a piece of code, including
  dependency direction, boundary types, and where mapping happens. Use when creating a feature,
  reviewing a pull request for layer violations, moving code between data/domain/presentation,
  choosing whether logic belongs in a ViewModel or a use case, or when a Composable or UI model
  leaks into the data layer.
license: Apache-2.0
metadata:
  domain: architecture
  level: core
  sources:
    - agent-skills-standard (android-architecture)
    - android-agent-engineering (android-architecture)
    - mobile-agent-skillpack (android-architecture, mobile-modern-clean-architecture)
    - awesome-android-agent-skills (android-architecture)
---

# Layering

A layer exists to own one kind of decision. Every class must have a defensible answer to
"which layer owns this, and who is allowed to depend on me".

## Use when

- Adding a feature and deciding which modules/files to create.
- Reviewing a diff for architecture violations.
- A `data class` is being reused across API, database, domain, and UI.
- Debating "should this be a use case?" or "can the ViewModel call the API directly?".

## Do not use when

- Only module *count* and Gradle wiring is at issue → `modularization`.
- Deciding the state holder shape → `state-holders`.
- The question is how to wire Hilt/Koin → `dependency-injection`.

## Rules

1. **Three layers, one direction:**
   `presentation → domain ← data`. Domain depends on nothing but Kotlin (and, if you accept
   it, coroutines). `data` and `presentation` never see each other.
2. **Domain has no Android import.** No `android.*`, no `androidx.*`, no `Context`, no
   `Uri`, no `Log`. If a domain type needs a platform concept, model the concept.
3. **One model per boundary.** API DTO, database entity, domain model, and UI model are
   distinct types. Mapping lives in the layer that *receives* the foreign type
   (DTO→domain in `data`, domain→UI in `presentation`).
4. **A use case exists when the operation is (a) reused by >1 presenter, (b) a transaction
   over >1 repository, or (c) a named business rule with non-trivial branching.** "It is one
   repository call" is not a use case — the ViewModel may call the repository directly.
   Adding passthrough use cases is a cost, not an architecture.
5. **Repositories return domain models and expose failure explicitly.** Return
   `Result<T>`, a sealed `ApiResult`, or throw a typed exception mapped at the boundary.
   Returning `null` for "failed" is forbidden — it erases the distinction from "absent".
6. **The repository interface lives in domain; its implementation lives in data.** The
   interface is the dependency-inversion point; do not define it next to the implementation.
7. **No UI types below presentation.** No `UiState`, no `String` resources ids, no formatted
   strings in domain/data. Formatting is a presentation concern.
8. **No framework types leak upward.** `Response<T>`, `Flow` from a specific library,
   `Entity`, cursor, or `JSONObject` must not cross into domain.
9. **One reason to change per class.** If a class maps a DTO *and* enforces a business rule
   *and* caches, split it at the layer whose invariant it protects.
10. **Do not create layers for a 3-screen app.** Layering pays for itself when there is more
    than one presenter or more than one data source. For a single-screen app, one module with
    package-level separation is correct — do not generate `domain/usecase/` for a counter.

## Procedure

1. Name the feature and its one-line responsibility.
2. For each new type, write: owner layer, allowed dependents, boundary type it accepts and returns.
3. Place the file; if it imports something from a layer it may not depend on, the model is
   wrong — change the type, not the rule.
4. For each new use case, verify rule 4 justifies it; delete passthroughs.
5. Map explicitly at each boundary and give the mapper a test.

## Checklist

- [ ] `domain` compiles without any `android`/`androidx` dependency.
- [ ] Repository interfaces in `domain`, implementations in `data`.
- [ ] Every cross-boundary type has an explicit mapper with a test.
- [ ] No passthrough use case in the diff.
- [ ] Failure is modelled (`Result`/sealed), not `null`.
- [ ] No `UiState`/formatted string/resource id below presentation.
- [ ] New classes each have one stated reason to change.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| DTO used as UI model | `@SerializedName` field bound to Composable | DTO → domain → UI model | UI now breaks when API renames |
| Repository returns `null` on error | `suspend fun get(): User?` | `Result<User>` / `Error` sealed | "absent" and "failed" collapse |
| Use-case explosion | `GetUserUseCase { repo.get() }` | ViewModel calls repository | indirection with no decision |
| Domain needs `Context` | pass `Context` in | pass `Clock`/`Locale`/values | layer becomes untestable |
| Entity annotated with Compose | shared `data class` across 4 layers | one model per boundary | one change breaks four layers |
| 3-screen app with 8 modules | full clean-arch scaffold | single module, package split | cost without benefit |

## Verify

```bash
./gradlew :domain:dependencies            # no android artefacts in the graph
./gradlew :domain:compileKotlin
grep -rn "import android" domain/src/main | grep -v test   # must be empty
```

Expected: empty grep output, and `:data` does not appear in `:presentation`'s implementation
dependencies.

## References

- Android Developers — Guide to app architecture (layer names only; ownership rules above are ours)
