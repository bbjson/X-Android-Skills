---
name: dependency-injection
description: >-
  Wire Hilt or Koin with correct scopes, define what each module may provide, and keep
  construction testable. Use when adding a dependency, creating a DI module, deciding between
  Singleton and ViewModel scope, injecting a dispatcher or clock, resolving a
  MissingBinding/DuplicateBinding or Koin NoDefinitionFound error, or migrating between Hilt and
  Koin.
license: Apache-2.0
metadata:
  domain: architecture
  level: core
  sources:
    - agent-skills-standard (android-di)
    - android-skill (migrate-di)
    - agent-skills-standard (android-architecture)
    - mobile-agent-skillpack (android-architecture)
---

# Dependency Injection

DI is a **scope model plus a construction rule**. The scope answers "how long does this live";
the rule answers "who is allowed to construct it". Everything else is syntax.

## Use when

- Adding a class that needs dependencies, or a new DI module.
- Choosing a scope (`@Singleton`, `@ViewModelScoped`, custom scope, Koin `single`/`factory`).
- Resolving `MissingBinding`, `DuplicateBinding`, `Scope mismatch`, `NoDefinitionFound`.
- Injecting `Dispatcher`, `Clock`, or config into a class.
- Migrating Hilt ↔ Koin, or deciding which to use.

## Do not use when

- The question is whether a class belongs in `domain`/`data` → `layering`.
- The question is module boundaries and `api`/`impl` → `modularization`.
- The question is test doubles for a class → `unit-testing`.

## Rules

1. **Constructor injection for everything you own.** Field injection (`@Inject lateinit var`) is
   only for framework-instantiated classes (Activity, Fragment, `@AndroidEntryPoint` targets).
   A class constructed by DI must be constructible by a test with plain arguments.
2. **Scope by lifetime, not by convenience.**
   - `@Singleton`: state must match the process (repositories over the local store, HttpClient).
   - `@ViewModelScoped`: state must match a screen/session and be released with it.
   - Unscoped/`factory`: stateless helpers, mappers, use cases.
   Using `@Singleton` for anything holding screen state is the #1 leak.
3. **Never inject a short-lived object into a longer-lived one.** Singleton holding a
   ViewModel-owned object keeps it alive forever. DI will let you; the compiler will not help.
4. **Provide, do not construct, platform types.** `Context`, `Retrofit`, `OkHttpClient`,
   `RoomDatabase`, `DataStore` are provided once at the right scope (usually `Singleton`) and
   injected — never built inside a repository.
5. **One module per concern, and it must be free of logic.** `NetworkModule`, `DatabaseModule`,
   `DispatcherModule`. A provider with `if`/`try`/business logic belongs in a class, and DI provides
   that class.
6. **Interface via `@Binds`, implementation as the injected class.** `@Provides` is for types you
   cannot annotate (third-party constructors) or that need factory logic. Prefer `@Binds` so the
   implementation stays a plain `@Inject constructor`.
7. **Qualifiers for every same-type pair.** Two `String`s (base URL vs api key) without
   `@Named`/custom qualifier is a production bug waiting for the first reorder of parameters.
8. **Inject dispatchers and clocks, never reference them statically.** `@IoDispatcher` injected,
   `Clock` injected. `Dispatchers.IO` inside a class makes it untestable (see `unit-testing`).
9. **`Context` stays at the edge.** Inject `Context` only into classes that genuinely need it
   (file I/O, system services); prefer the narrowest type (`Application`, `ContentResolver`).
   A ViewModel must never receive `Context` — pass `Application`-scoped values or results instead.
10. **No Binds-cycle, no two-module cycle.** Hilt reports it; treat it as a layering signal
    (`layering`), not as a reason for a `Provider<T>` indirection.
11. **Choose one framework for the project.** Hilt gives compile-time graph validation; Koin gives
    runtime graphs and no KSP/kapt cost. Mixing them means two graphs and two failure modes.

## Procedure

1. For the new class, write its lifetime and its owner.
2. Hilt: `@Inject constructor(...)` + `@Binds`/`@Provides` for interfaces/third-parties.
3. Koin: `factory`/`single`/`viewModel` in the module that owns the concern.
4. Add qualifiers for same-type params.
5. If the class takes `Dispatcher`, `Clock`, `Context`: verify they come from a module, not a
   literal.
6. Run the graph check.

## Checklist

- [ ] Owned classes use constructor injection only.
- [ ] Scope matches lifetime; no singleton holds screen/session state.
- [ ] No singleton depends on a shorter-lived object.
- [ ] Platform types provided once, at `Singleton` scope.
- [ ] Every same-type parameter pair has a qualifier.
- [ ] Dispatchers/clock injected; no `Dispatchers.IO` literal in tested code.
- [ ] No `Context` in a ViewModel.
- [ ] One DI framework in the project.
- [ ] Graph validates (`./gradlew :app:hiltJavaCompileDebug` or Koin `checkModules`).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Memory leak | `@Singleton` repository holding a screen cache | `@ViewModelScoped` / unscoped | lives forever |
| `MissingBinding` | add `@Provides` in a random module | check layering: who should own it | usually a boundary bug |
| Wrong base URL | two `@Named("x")` swapped | typed wrapper / distinct qualifier | silent misroute |
| Untestable | `Dispatchers.IO` inside | injected `@IoDispatcher` | no virtual time |
| VM has `Context` | inject activity context | pass resolved values | leak + untestable |
| DuplicateBinding | two providers for one type | one owner module | ambiguous graph |
| Provider with logic | `@Provides fun repo(): Repo { if (...) }` | logic in a class, provide it | graph becomes code |

## Verify

```bash
./gradlew :app:hiltJavaCompileDebug          # Hilt: graph validated at compile time
./gradlew :app:testDebugUnitTest             # Koin: verify(modules) check
./gradlew :app:assembleDebug                 # full graph resolution
```

Expected: compile-time graph validation passes (Hilt) or `checkModules` passes (Koin), and a test
can construct the class with plain fake arguments.

## References

- Hilt scope hierarchies: `@Singleton`, `@ActivityRetainedScoped`, `@ViewModelScoped`
- Koin `module { }`, `single`, `factory`, `viewModel`, `verify()`
