---
name: hilt-to-koin
description: >-
  Replace Hilt with Koin preserving scopes and lifetimes, and add the runtime graph validation Hilt gave
  you for free. Use when moving to Koin (or evaluating it), when `NoDefinitionFoundException` appears
  after a migration, when a singleton becomes a new instance per screen, or when deciding whether the
  move is worth it.
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - android-skill (migrate-di)
    - agent-skills-standard (android-di)
    - mobile-agent-skillpack (android-architecture)
    - agent-skills-standard (android-architecture)
---

# Hilt to Koin

The migration is mechanical in syntax and risky in **timing**: Hilt fails at compile time, Koin fails
at runtime on the code path that needs the missing definition.

## Use when

- Migrating from Hilt/Dagger to Koin.
- `NoDefinitionFoundException` / `InstanceCreationException` after the move.
- A `@Singleton` became "new instance per screen" (or the reverse) after conversion.
- Deciding whether to move from Hilt to Koin at all.

## Do not use when

- The problem is scope design, not the framework → `dependency-injection`.
- The problem is modularisation of DI bindings → `modularization`.
- The problem is test doubles → `unit-testing`.

## Rules

1. **Scopes map by lifetime, exactly:**
   `@Singleton` → `single { }`; `@ActivityRetainedScoped` → `activityRetainedScope` (or a custom scope);
   `@ViewModelScoped` → `viewModel { }`; `@ActivityScoped` → `activityScope`; unscoped → `factory { }`.
   Getting this table wrong is the whole risk of the migration.
2. **`@Binds` → `singleOf(::Impl) { bind<Api>() }`** (or `factoryOf`/`viewModelOf`). `@Provides` →
   `single { }`/`factory { }` with the construction inline, **minus business logic** (same rule as
   `dependency-injection` rule 5).
3. **`@Inject constructor` annotations can stay or go; they are inert in Koin.** Remove them in a
   separate commit so the conversion diff stays reviewable.
4. **Replace the compile-time guarantee with `verify(modules)` in a test.** A Koin graph is not checked by
   the compiler; without a `checkModules`/`verify` unit test, a missing binding ships.
5. **`@Module @InstallIn` → `module { }`**, one module per concern; do not create one giant module.
6. **`@EntryPoint`/`EntryPointsAccessors` have no direct equivalent.** Replace with an injected
   dependency on the framework class, or a thin accessor object defined in a module — do not call
   `getKoin()` from inside a class.
7. **`@AndroidEntryPoint` disappears; call `startKoin` once in `Application`.** A second `startKoin` (in a
   test, or a second Application) throws; use `loadKoinModules`/`unloadKoinModules` in tests instead.
8. **Qualifiers: `@Named("x")` → `named("x")`; typed qualifiers → a typed `Qualifier` class.** Keep the
   distinction, do not collapse two same-typed bindings into positional order.
9. **The migration is all-or-nothing per process.** Hilt and Koin can coexist in a build (both compile),
   but not for the same class graph: an `@AndroidEntryPoint` Activity and a Koin-injected ViewModel are
   two containers. Convert a whole app, or a module that owns its entire graph.
10. **Measure what you gain.** Koin removes annotation processing from the build and adds runtime cost +
    a new failure mode. Record the build-time delta and the new test; if the delta is small, the move may
    not be worth it.

## Procedure

1. Build the scope table (rule 1) for every binding before changing code.
2. Create `module { }` definitions mirroring the Hilt modules (rule 5).
3. Convert bindings (rule 2); remove `@Inject` in a separate commit (rule 3).
4. Replace entry points (rule 6) and `startKoin` (rule 7).
5. Delete `@AndroidEntryPoint`, `hilt-android` dependency, KSP/kapt processor, and the Hilt Gradle plugin.
6. Add a `verify(modules)` test (rule 4).
7. Exercise every screen — the runtime verification is now your compiler.

## Checklist

- [ ] Scope table written and applied per binding.
- [ ] `@Binds`/`@Provides` converted without business logic in the DSL.
- [ ] `@Inject` annotations removed in a separate commit.
- [ ] `verify(modules)`/`checkModules` test added and passing.
- [ ] One module per concern.
- [ ] No `getKoin()` / service-locator calls inside classes.
- [ ] `startKoin` once; tests use `loadKoinModules`/`unloadKoinModules`.
- [ ] Qualifiers preserved (named/typed).
- [ ] Hilt plugin, dependency and processor removed.
- [ ] Every screen exercised; build-time delta recorded.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| New instance per screen | `@Singleton` → `factory` | `single` | lifetime changed |
| Leak | `@ViewModelScoped` → `single` | `viewModel { }` | survives screen |
| Runtime crash in prod | no `verify` test | `verify(modules)` in unit test | no compiler check |
| Two containers | Hilt + Koin for the same graph | convert per module/app | duplicate instances |
| Service locator | `getKoin().get()` in a class | constructor parameter | untestable |
| Duplicate start | `startKoin` in Application and test | `loadKoinModules` | throws |

## Verify

```bash
./gradlew :app:assembleDebug
./gradlew :app:testDebugUnitTest --tests '*KoinVerify*'    # verify(modules)
grep -rn "@AndroidEntryPoint\|@HiltAndroidApp\|hilt" --include=*.kt --include=*.kts . | head
```

Expected: `verify(modules)` passes, no Hilt annotations or dependencies remain in converted modules, and
navigating every screen produces no `NoDefinitionFoundException`.

## References

- Koin `module { single/factory/viewModel/singleOf }`, `verify(modules)`, `loadKoinModules`
- Hilt scope semantics (the mapping table above is the contract)
