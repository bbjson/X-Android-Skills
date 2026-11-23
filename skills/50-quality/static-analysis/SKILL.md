---
name: static-analysis
description: >-
  Set up Android Lint, Detekt and Ktlint as a real quality gate: severity policy, a shrinking
  baseline, per-module configuration, and CI failure on new problems only. Use when adding static
  analysis to a project, when the baseline is being used to hide new issues, when CI produces 4000
  warnings nobody reads, or when deciding which rules to make errors.
license: Apache-2.0
metadata:
  domain: quality
  level: advanced
  sources:
    - agent-skills-standard (android-tooling)
    - android-agent-engineering (android-code-review)
    - android-skill (setup-ci)
    - mobile-agent-skillpack (security-best-practices)
---

# Static Analysis

A linter that reports 4000 warnings is a linter nobody reads. The only configuration that works:
**existing problems frozen in a baseline that shrinks, new problems fail the build.**

## Use when

- Adding Lint/Detekt/Ktlint to an Android project.
- CI is noisy with warnings that are ignored.
- A baseline is masking newly introduced problems.
- Deciding which rules should be errors.
- Writing a custom Detekt rule for a project-specific convention.

## Do not use when

- The issue needs semantic judgement (architecture, boundaries) → `code-review`.
- The issue is formatting only and the tool already runs → fix and commit.
- The problem is test coverage → `unit-testing` / `benchmark-testing` (mutation).

## Rules

1. **Three tools, three jobs, no overlap:** Android Lint (platform/API/resources), Detekt (Kotlin
   complexity/code smells), Ktlint (formatting). Configuring two to check the same thing produces
   duplicate findings and arguments about which one is authoritative.
2. **Formatting is automated, not reviewed.** Ktlint (or the formatter) runs on save and in a
   pre-commit/CI check with autofix; a human comment about spacing is a process failure.
3. **Baselines are frozen debt, and they must only shrink.** `lint-baseline.xml` and Detekt's
   `baseline.xml` are allowed once; a PR that adds entries must be rejected in review. Enforce by
   diffing the baseline in CI.
4. **New code fails on errors; old code is grandfathered.** Set `abortOnError = true` for the Lint
   task and let the baseline absorb only pre-existing issues. Without `abortOnError`, CI is a report
   generator.
5. **Promote rules to `error` when they catch a defect class you have actually hit.** Correctness,
   security and API-level misuse (`NewApi`, `ExportedReceiver`, `MissingPermission`) are errors.
   Style preferences stay warnings — errors on taste produce workarounds.
6. **Lint runs on every variant you ship, with the release build included.** A rule that only runs on
   `debug` misses R8/obfuscation issues. `lintRelease` (or `lintVitalRelease`) is part of the release
   gate.
7. **Per-module configuration beats one global file** when modules differ (library vs app, generated
   code excluded). Exclude generated sources explicitly (`build/generated/**`) — linting KSP output
   buries real findings.
8. **Suppress with a reason, in the narrowest scope.** `@Suppress("UnusedResources")` on a single
   declaration is documentation; a global ignore in the config is deletion of a check.
9. **A rule that fires on generated code or third-party code is misconfigured, not the code.** Fix the
   exclusion; do not suppress at every call site.
10. **Measure the gate's cost.** Lint on a large multi-module project can take minutes; run it in
    parallel with tests and cache the results (`lint` is cacheable when inputs are declared).

## Procedure

1. Decide tool ownership (rule 1); delete overlapping configuration.
2. Wire Ktlint with autofix, wired into `check` or a pre-commit hook.
3. Configure Detekt with a small, opinionated config: complexity thresholds that match the project,
   `maxIssues = 0`, and a baseline for legacy code.
4. Configure Lint: `abortOnError = true`, baseline committed, `checkDependencies` only in the app
   module to avoid duplicate reports.
5. Add CI steps: `lintRelease`, `detekt`, `ktlintCheck`.
6. Enforce baseline shrink: CI diffs `*-baseline.xml` and fails when entries are added.
7. Once a month (or per release), remove a batch of baseline entries and fix them.

## Checklist

- [ ] One tool per concern; no duplicate rule coverage.
- [ ] Formatting automated, not commented on in review.
- [ ] Baselines committed and **only shrinking** (CI enforces).
- [ ] `abortOnError = true`; new code fails on errors.
- [ ] Correctness/security/API rules set to error; style stays warning.
- [ ] Lint runs for release too (`lintRelease`/`lintVitalRelease`).
- [ ] Generated and third-party sources excluded.
- [ ] Suppressions are narrow with a reason.
- [ ] Tool cost measured and parallelised.
- [ ] `maxIssues = 0` for Detekt (baseline absorbs legacy).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| 4000 warnings ignored | no baseline, no abort | baseline + `abortOnError` | signal lost |
| New problems hidden | baseline regenerated on each PR | CI diff rejects additions | debt grows |
| Style arguments in review | comment on spacing | autofix + CI check | wrong tool |
| Release-only bug | lint on debug only | `lintRelease` | R8/API misuse missed |
| Suppression everywhere | config-level ignore | narrow `@Suppress` with reason | check deleted |
| Linting KSP output | no exclusion | exclude `build/generated` | noise buries findings |
| Two tools, one rule | Lint + Detekt both check complexity | one owner | duplicate, disputes |

## Verify

```bash
./gradlew lintRelease detekt ktlintCheck
git diff --stat -- '*baseline.xml'    # must not grow in a feature PR
```

Expected: `lintRelease`/`detekt` fail on a deliberately introduced error-level issue, pass on the
baseline, and a PR that adds a baseline entry fails CI.

## References

- Android Lint `lint { abortOnError, baseline, checkDependencies }`
- Detekt `baseline.xml`, `maxIssues`, `buildUponDefaultConfig`
