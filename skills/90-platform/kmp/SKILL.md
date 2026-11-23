---
name: kmp
description: >-
  Structure a Kotlin Multiplatform project so shared code stays platform-free: source set layout,
  expect/actual boundaries, dependency and serialization rules, iOS interop, and testing per platform.
  Use when setting up KMP, moving logic into commonMain, deciding whether UI is shared (Compose
  Multiplatform) or native, adding a platform-specific implementation, or debugging a commonMain
  compile error.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - kotlin-kmp-claude-agent-skills (kotlin-project-modularization, kotlin-platform-kmp-bridges, kotlin-testing-kmp)
    - kotlin-footguns (kmp-architecture-footguns)
    - agent-skills-standard (android-architecture)
    - kotlin-agent-skills (kotlin-tooling-gradle-to-kotlin-toolchain-project)
---

# Kotlin Multiplatform

Sharing code between platforms is a **boundary decision**: share what has no platform semantics, wrap
what does. Every `expect` is a boundary you promise to maintain.

## Use when

- Setting up KMP or adding a target (iOS/desktop/wasm).
- Moving logic into `commonMain`.
- Deciding whether to share UI with Compose Multiplatform or keep it native.
- Adding an `expect`/`actual` pair for a platform capability.
- `commonMain` fails to compile because something pulled in an Android/Apple type.

## Do not use when

- The question is Android-only architecture → `layering` / `modularization`.
- The question is Compose UI details → `compose-core` (CMP shares the same APIs).
- The question is CocoaPods→SPM tooling → `cocoapods-to-spm`.

## Rules

1. **`commonMain` contains zero platform types.** No `android.*`, no `platform.Foundation.*`, no
   `java.*` (except when targeting JVM-only and documented). If it needs one, it is an `expect`.
2. **Share domain and data, share UI only deliberately.** Shared logic gives the highest return;
   shared UI (Compose Multiplatform) gives the highest lock-in. Decide per screen group, not per app.
3. **`expect` is a contract, so keep it small and few.** One `expect` per capability (clock, uuid,
   hashing, file system, key-value store), not one per call site. A large `expect` surface is a
   platform abstraction that failed.
4. **`actual` implementations must be trivially thin.** Business logic in an `actual` is logic you
   cannot test in `commonTest`. Move it to common and keep the actual to the API call.
5. **Source sets reflect dependencies, not tidiness.** `commonMain` → `jvmMain`/`appleMain` →
   `androidMain`/`iosMain` (in that order). A `commonMain` dependency pulled down into a platform set
   is nearly always a mistake; a platform dependency in `commonMain` does not compile.
6. **Coroutines need a dispatcher provided per platform.** Do not rely on `Dispatchers.Default` being
   the UI thread equivalent on iOS; inject a `CoroutineContext`/`CoroutineScope` or use a
   platform main dispatcher implementor.
7. **Serialization is the shared data boundary.** Use `kotlinx.serialization` with `commonMain` DTOs
   and one `Json` configuration; platform JSON libraries in common code create two behaviours.
8. **iOS interop memory model: do not pass mutable shared state across threads.** Kotlin/Native
   objects are frozen by default in modern memory manager terms — prefer immutable data across the
   boundary, and keep callbacks on the main thread unless explicitly scheduled.
9. **Test in `commonTest` for logic and in each platform's test set for the `actual`.** A test only in
   `androidTest` leaves iOS's `actual` unverified — which is where platform bugs live.
10. **Gradle: one module per boundary, toolchain from the convention plugin.** KMP modules still follow
    `modularization`; a single `shared` module that becomes everything is the same god module problem.

## Procedure

1. Decide targets and what is shared (rule 2); write the source set tree.
2. Put DTO/domain/interfaces in `commonMain`; put platform capabilities behind small `expect`s.
3. Implement `actual`s thinly per platform.
4. Inject dispatchers/scopes; test logic in `commonTest`.
5. Add one platform test per `actual` that exercises the real API.
6. Build both targets: `./gradlew :shared:compileKotlinJvm :shared:compileKotlinIosSimulatorArm64`.

## Checklist

- [ ] `commonMain` compiles with no Android/Apple/JVM-only imports.
- [ ] UI-sharing decision made per screen group and written down.
- [ ] `expect` surface small; no per-call-site expects.
- [ ] `actual`s contain no business logic.
- [ ] Dispatchers/scopes injected, not assumed.
- [ ] Serialization configured once in common.
- [ ] No mutable state passed across iOS threads.
- [ ] Logic tested in `commonTest`; each `actual` tested natively.
- [ ] Module boundaries follow `modularization`, not "one shared module".

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| commonMain won't compile | `import androidx.…` | `expect` capability | platform coupling |
| Untestable logic | logic inside `actual` | logic in common, thin actual | native-only bugs |
| expect explosion | one expect per function | one per capability | contract maintenance |
| Shared UI lock-in | CMP for everything | shared logic, native UI where needed | platform UX differences |
| Wrong thread on iOS | `Dispatchers.Main` assumed | injected dispatcher / main implementor | crashes/misbehaviour |
| Two JSON behaviours | platform JSON in common | one kotlinx `Json` | divergent parsing |
| God module | one `shared` module | boundary modules | same problems as Android |

## Verify

```bash
./gradlew :shared:compileKotlinJvm :shared:compileKotlinIosSimulatorArm64
./gradlew :shared:allTests
grep -rn "import android\.\|import platform\.Foundation\|import java\." shared/src/commonMain   # must be empty
```

Expected: common sources compile for every target, both platform test sets pass, and the grep is empty.

## References

- `kotlin-multiplatform` source set hierarchy, `expect`/`actual` rules
- Compose Multiplatform for the UI-sharing decision
