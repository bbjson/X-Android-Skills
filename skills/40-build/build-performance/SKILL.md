---
name: build-performance
description: >-
  Reduce Gradle build time by measuring first, then fixing configuration-phase work, task
  configurability, caching and annotation processing. Use when a build takes minutes, when
  configuration cache reports problems, when a one-line change rebuilds everything, when
  "clean build" and incremental differ wildly, or when a build scan shows a dominant task.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - awesome-android-agent-skills (gradle-build-performance)
    - agent-skills-standard (android-tooling)
    - chrisbanes/skills (gradle-run)
    - android-skill (setup-ci)
---

# Build Performance

Build time is **configuration time + execution time**, and they need different fixes. Optimising
execution while the configuration phase runs `exec` on every invocation is the most common mistake.

## Use when

- `./gradlew assembleDebug` exceeds the team's tolerance.
- A one-file change recompiles many modules.
- `--configuration-cache` reports "problems" and someone wants to disable it.
- A build scan shows one task dominating.
- CI cache is ineffective or always misses.
- Incremental and clean builds differ by an order of magnitude.

## Do not use when

- The problem is *runtime* app performance → `startup-and-perfetto` / `recomposition`.
- The problem is module structure decisions → `modularization`.
- The problem is annotation processing configuration specifics → `ksp-processing`.

## Rules

1. **Profile before changing anything.** `--scan` or `--profile` gives per-task time and the
   configuration vs execution split. A change without a before/after number is a guess.
2. **Configuration phase must not do I/O.** `exec`, `git`, `fileTree` walks, `System.getenv` in a
   task *configuration* block run on every invocation, even for `help`. Move them into a task action
   (`@TaskAction`) or a `ValueSource` (which is cacheable).
3. **`tasks.register`, never `tasks.create` or `task foo`.** Registration is lazy: the task is only
   configured if it is in the task graph. `create` configures everything, always.
4. **Enable the configuration cache, and fix the reported problems instead of disabling it.**
   Every "problem" is configuration-phase state that cannot be reused. Disabling it restores
   seconds-per-invocation cost.
5. **Enable the build cache and verify it actually hits.** `org.gradle.caching=true` plus a local or
   remote cache. Check a scan for `FROM-CACHE` results; if zero, the tasks are not cacheable
   (undeclared inputs/outputs or `doNotCacheIf`).
6. **Declare task inputs and outputs properly** when writing custom tasks. An undeclared output makes
   the task uncacheable and forces re-execution; an undeclared input makes the cache **wrong**
   (stale results), which is worse.
7. **Turn off unused AGP features per module.** `buildFeatures { buildConfig = false; viewBinding = false }`
   unless used, `resourcePrefix`, and `androidResources { noCompress }` for already-compressed assets.
   These are cheap wins that compound across modules.
8. **Annotation processing and Kotlin compilation usually dominate.** Address in this order:
   kapt→KSP, processor scope (`ksp-processing`), module count and dependency depth
   (`modularization`), then everything else.
9. **Resources and asset processing are a fixed cost per module.** Large `res/` trees, unused
   resources, and many `drawable-*` variants add time to every variant build. `shrinkResources` and
   `lint`'s `UnusedResources` are the cleanup tools.
10. **Parallelism and ordering are settings, not hacks.** `org.gradle.parallel=true`,
    `org.gradle.caching=true`, `org.gradle.configuration-cache=true`. `--max-workers` above CPU count
    makes things slower, not faster.
11. **Keep a baseline in the repository.** Time for `assembleDebug` (clean and 1-file change) per
    machine class, so regressions are visible in review rather than in a developer's memory.

## Procedure

1. Baseline: `./gradlew --profile :app:assembleDebug` (clean), then one-file change (incremental).
   Record configuration, execution and the top 10 tasks.
2. Enable/repair the four settings (rules 3–5).
3. Grep for configuration-phase work:
   ```bash
   grep -rn "exec {\|\.execute()\|fileTree(\|System.getenv" --include=*.kts .
   ```
4. Convert eager task creation to `register`, move I/O into task actions or `ValueSource`.
5. Disable unused `buildFeatures`; check kapt→KSP status.
6. Re-run the same two measurements; keep only changes that improve without breaking cacheability.

## Checklist

- [ ] Baseline recorded (clean + incremental, per task).
- [ ] No `exec`/IO in configuration blocks.
- [ ] All tasks created with `register`.
- [ ] Configuration cache enabled; zero reported problems.
- [ ] Build cache enabled; a scan shows `FROM-CACHE` on repeat builds.
- [ ] Custom tasks declare inputs and outputs.
- [ ] Unused `buildFeatures` disabled per module.
- [ ] kapt eliminated or justified.
- [ ] `parallel` and `caching` set in `gradle.properties`, not per invocation.
- [ ] Before/after numbers in the PR.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Seconds for `help` | `exec` in configuration | task action / `ValueSource` | runs every invocation |
| Everything configures | `tasks.create` | `tasks.register` | eager configuration |
| Cache never hits | no input/output declarations | declare them | uncacheable |
| Stale cache results | undeclared input | declare + `@Input` | wrong output |
| Disabled config cache | "it reported problems" | fix each problem | 2–5s per invocation |
| Fake speedup | `--max-workers=64` | CPU-count parallelism | context switching |
| Big res folders | never pruned | `lint` UnusedResources | every variant cost |

## Verify

```bash
./gradlew --profile :app:assembleDebug            # clean baseline
./gradlew :app:assembleDebug                       # incremental
./gradlew help --configuration-cache --configuration-cache-problems=fail
./gradlew :app:assembleDebug --build-cache --scan
```

Expected: configuration time under a second on incremental runs, `FROM-CACHE` entries in the scan,
and a measurable drop in the top task's time versus the recorded baseline.

## References

- Gradle configuration cache, build cache, `ValueSource`, `TaskProvider`
- `gradle.properties`: `org.gradle.parallel`, `caching`, `configuration-cache`, `daemon`
