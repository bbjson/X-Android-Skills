---
name: modularization
description: >-
  Decide whether a project needs modules, which boundary each module enforces, and in which
  order to split, without creating a dependency graph nobody can build. Use when a single
  module build time is hurting, a feature team needs an enforced boundary, two features keep
  reaching into each other's internals, deciding between layer modules and feature modules, or
  setting up `api`/`impl` module pairs and convention plugins.
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - agent-skills-standard (android-architecture)
    - mobile-agent-skillpack (android-architecture)
    - android-skill (modularize)
    - awesome-android-agent-skills (android-gradle-logic)
    - chrisbanes/skills (gradle-run)
---

# Modularization

A module is a **compile-time fence plus a dependency declaration**. It is worth creating only
when you can state which dependency it makes impossible.

## Use when

- Deciding whether/how to split an app into modules.
- Two features reach into each other's internal packages.
- Build times are dominated by one giant module.
- Setting up `:feature:x:api` / `:feature:x:impl`, or `:core:*` modules.
- A new module's dependencies must be reviewable.

## Do not use when

- The problem is where code goes *inside* a module → `layering`.
- The problem is Gradle configuration shape (convention plugins, catalog) → `gradle-conventions`.
- The app has fewer than ~3 real features (see rule 2).

## Rules

1. **A module must ban something.** Write the sentence: "this module prevents X from depending on
   Y." If you cannot, you are creating directories with extra build files.
2. **Do not modularize a small app.** Under ~3 features or under ~15k hand-written Kotlin lines,
   package-level separation inside one module is the correct answer. The pay-off (parallel
   compilation, enforced boundary) does not exist yet, and the cost (declaration churn, `api` vs
   `implementation` bugs) is immediate.
3. **Choose one axis per layer of the tree, never both.** Feature-first
   (`:feature:feed`, `:feature:profile`) for app code; layer-first (`:core:data`, `:core:ui`)
   for shared code. Mixing `:feature:feed` next to `:domain` at the same level produces a graph
   where nothing is allowed to depend on anything.
4. **`impl` depends on `api`, never the reverse, and the app composes them.** Public types in
   `api`, everything else `implementation`-scoped in `impl`. `api` must compile alone and must not
   depend on Compose unless the exposed type *is* a Composable.
5. **`implementation` by default; `api` only for types in the public signature.** An accidental
   `api` dependency is transitive leakage — fix it by moving the type, not by hiding the import.
6. **No circular dependencies, including via `core`.** Shared code goes down, never sideways.
   If two features need each other, the shared part belongs in a `core` module — extract the
   *type*, not the feature.
7. **Navigation is the only legal feature→feature edge, and it goes through the app module.**
   `:feature:a` must not depend on `:feature:b`; the app/nav module wires `NavHost` between them.
8. **Every module declares its own `compileSdk`/`minSdk`/`jvmTarget` via a convention plugin**,
   not copy-pasted blocks. Ten copies of an android block is ten places to change one number.
9. **A module's public surface is a review artefact.** Adding a type to `api` is a contract
   change; treat it like a public API of a library.
10. **Split incrementally, and keep the build green at every step.** One module per commit,
    leaf-first (extract a `core:util` before a `feature`), never a big-bang restructure.

## Procedure

1. Measure first:
   ```bash
   ./gradlew assembleDebug --profile
   ./gradlew :app:assembleDebug --dry-run
   ```
2. List candidate fences with the sentence from rule 1; discard any without one.
3. Extract leaves first: `:core:model`, `:core:ui`, `:core:designsystem`, `:core:testing`.
4. Convert one feature to `api`/`impl`; move its public types into `api`; compile `:feature:x:api` alone.
5. Add the convention plugin that replaces duplicated `android { }` blocks.
6. Delete accidental `api` edges: `./gradlew :app:dependencies` and read the graph.
7. Only then split the next feature.

## Checklist

- [ ] Every new module has a one-line "prevents X→Y" justification.
- [ ] One axis per tree level (feature-first *or* layer-first, not both).
- [ ] `impl` → `api` edges only; `api` compiles by itself.
- [ ] No `:feature:a` → `:feature:b` edge; wired through the app/nav module.
- [ ] No module copies `android { }` config; convention plugin applies it.
- [ ] `:app:dependencies` shows no unintended transitive leak from an `api`.
- [ ] Build green after each split commit, not only at the end.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| 20 modules, 1 dev | full modularisation | 1 module, package split | fence with no cost model |
| Everything depends on `:core` | dump shared code there | purpose-named `core:*` modules | `core` becomes the god module |
| Feature A imports feature B | add the dependency | extract shared type to `core` | graph becomes a mesh |
| Build slows after split | keep `api` everywhere | `implementation` by default | transitive recompiles |
| `core:ui` depends on Compose & data | accept it | split design-system vs data | every consumer recompiles |
| Big-bang restructure | one 200-file PR | leaf-first, one module per commit | unreviewable, unrevertable |

## Verify

```bash
./gradlew projects
./gradlew :app:dependencies --configuration debugRuntimeClasspath | grep -E "project \'?:" 
./gradlew :feature:feed:api:compileDebugKotlin      # must succeed alone
grep -rn "implementation project(':feature:profile')" feature/feed/   # must be empty
```

Expected: `:feature:*:api` compiles without `:impl`, no feature→feature project dependency exists,
and the dependency report contains no module reachable only through an unintended `api`.

## References

- Gradle `java-library` semantics — `api` vs `implementation` configurations
- `nowinandroid` module graph as a reference shape (not a default to copy)
