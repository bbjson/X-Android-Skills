---
name: ci-pipeline
description: >-
  Build a CI pipeline that catches real failures in minutes: correct JDK/toolchain, useful caching,
  fast PR checks separated from slow nightly device tests, artifacts that diagnose failures, and
  secrets that never end up in logs. Use when setting up GitHub Actions or another CI for an Android
  project, when CI is slower than local, when caching never hits, when instrumented tests need an
  emulator, or when a release job must sign and upload.
license: Apache-2.0
metadata:
  domain: build
  level: advanced
  sources:
    - android-skill (setup-ci)
    - mobile-agent-skillpack (mobile-ci-release-flow)
    - agent-skills-standard (android-tooling, android-deployment)
    - awesome-android-agent-skills (gradle-build-performance)
---

# CI Pipeline

A pipeline is **a set of questions answered in order of cost**. Cheap questions first, and every job
must fail for a reason a developer can act on from the output alone.

## Use when

- Setting up CI for an Android repo.
- CI is slower than the local build, or caching never hits.
- Instrumented tests need a device/emulator in CI.
- A release job must sign and upload to Play.
- A PR needs a required check that actually means something.

## Do not use when

- The build itself is slow locally → `build-performance`.
- The signing configuration is wrong → `signing-and-play-signing`.
- The release sequence (tracks, rollout) → `release-flow`.

## Rules

1. **Order jobs by cost:** lint → unit tests → assemble → (nightly) instrumented → release. Never
   make a PR wait for an emulator to discover a lint error.
2. **One JDK, provisioned explicitly.** `actions/setup-java` with the same major version the toolchain
   declares, plus `gradle/actions/setup-gradle`. Relying on the runner's default JDK is a
   CI-only failure generator (`kotlin-toolchain`).
3. **Cache two things, keyed on the right files:** the Gradle wrapper/user home
   (`~/.gradle/caches`, `~/.gradle/wrapper`) keyed on `**/*.gradle*`, `**/libs.versions.toml`, and the
   configuration-cache entry keyed on the same. Do not cache `build/` directories — stale outputs
   produce impossible failures.
4. **`concurrency: cancel-in-progress: true` per branch/PR.** A superseded run must die; otherwise
   queue time is the pipeline's dominant cost.
5. **Least privilege and no secrets on PRs from forks.** `permissions: contents: read` by default;
   signing keys and Play credentials only in jobs that need them, never exposed to `pull_request`
   from forks.
6. **Secrets are files injected at job time, never committed or echoed.** Write the keystore from a
   base64 secret into `$RUNNER_TEMP` with restrictive permissions, pass paths via `-P` properties or
   env vars, and never `cat` them.
7. **Every failing job uploads the artefact that explains the failure:** test reports, `lint-results`,
   `mapping.txt` for release builds, and the Gradle build scan link if available.
8. **Instrumented tests run on a managed device or a KVM-accelerated emulator, not the default one.**
   Use Gradle Managed Devices or a hardware-accelerated action; a software-rendered emulator turns a
   3-minute suite into 30 and flakes on timeouts.
9. **Split PR vs nightly.** PR: lint, unit tests, `assembleDebug`, `assembleRelease` (to catch R8
   rule errors). Nightly: instrumented tests across 2 API levels, macrobenchmark, dependency report.
10. **Timeouts and fail-fast.** Set `timeout-minutes` per job; a hung emulator otherwise consumes the
    whole budget. `fail-fast: false` only in matrix jobs where you need all failures.
11. **The pipeline must be reproducible from a tag.** A release build must be producible by re-running
    the workflow on the tag, not by a developer's local machine.

## Procedure

1. Write `ci.yml` with jobs: `lint`, `test`, `build` (debug+release), sharing a Gradle setup step.
2. Add JDK + Gradle setup with caching (rule 3).
3. Add `concurrency` and `permissions` at the top.
4. Add artifact upload on failure (`if: failure()`).
5. Add a `nightly.yml` with managed devices and a matrix of API levels.
6. Add the release job: signing secret injection + `bundleRelease` + upload (see
   `signing-and-play-signing`).
7. Measure: record the PR job duration; if >10 min, find the dominant step rather than adding parallelism.

## Checklist

- [ ] Jobs ordered cheapest-first; PR path has no emulator.
- [ ] JDK pinned to the declared toolchain; Gradle caching enabled.
- [ ] Cache keys include build scripts and version catalog.
- [ ] No `build/` directory caching.
- [ ] `concurrency` cancel-in-progress set.
- [ ] `permissions` minimal; secrets only in release jobs.
- [ ] Keystore injected from a secret into a temp file, never echoed.
- [ ] Failure artefacts uploaded (reports, lint, mapping).
- [ ] Instrumented tests on managed device / KVM emulator.
- [ ] Job timeouts set; release reproducible from a tag.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| 40-minute PRs | emulator in PR path | nightly only | wrong cost ordering |
| CI-only failure | default runner JDK | pinned JDK matching toolchain | environment drift |
| Cache never hits | key on commit sha | key on gradle files | always miss |
| Impossible failures | cache `build/` | cache Gradle user home only | stale outputs |
| Queue saturation | no concurrency | cancel-in-progress | superseded runs |
| Secret in logs | `echo $KEYSTORE_B64` | write to temp file, no output | leak |
| Flaky emulator | software rendering | KVM / managed device | timeouts |
| No diagnosis | empty failure output | upload reports/mapping | re-run guessing |

## Verify

```bash
# local approximation of the CI check
./gradlew lintDebug testDebugUnitTest assembleDebug assembleRelease --warning-mode all
```

Expected: the same commands pass locally and in CI with the same JDK; a repeated run shows cache hits;
a deliberately broken test produces a failure with an uploaded report naming the test.

## References

- `actions/setup-java`, `gradle/actions/setup-gradle`
- Gradle Managed Devices (`android.testOptions.managedDevices`)
- Play upload: see `release-flow` and `signing-and-play-signing`
