---
name: router
description: >-
  Route an Android task to the correct domain skill before doing any work, and refuse to start
  when the task is under-specified. Use at the start of any Android, Kotlin, Jetpack Compose,
  Gradle, Play release, or device-automation request when you are unsure which skill applies,
  when several could apply, or when the request is a symptom ("it's slow", "it crashes") rather
  than a task. Use when starting any Android/Kotlin/Compose/Gradle/Play/device request whose
  owning skill is not obvious.
license: Apache-2.0
metadata:
  domain: meta
  level: core
  sources:
    - chrisbanes/skills (using-chrisbanes-skills)
    - android-skill (official-android-skills)
    - agent-skills-standard (metadata)
---

# Router

Do not start work from a symptom. Name the artefact that must change, then load the one skill
that owns it. Loading two domain skills for one change is usually a sign the task should be split.

## Use when

- The request is vague ("make it faster", "it's broken", "add a screen").
- Two or more skills might apply and you must pick one.
- The request spans domains (e.g. "add a screen and release it") — split it first.

## Do not use when

- The owning skill is already obvious — load it directly. The router is a fallback, not a ritual.

## Routing table

| Request shape | Load | Not |
|---|---|---|
| crash / ANR / wrong value / build error | `bug-fix` | `refactor` |
| "where does this class go?" / layer violation | `layering` | `modularization` |
| state ownership, effects, rotation loss | `compose-state-effects` | `recomposition` |
| add screen, args, deep link, back behaviour | `compose-navigation` | `compose-state-effects` |
| "slow", "janky", "recomposes too much" | `recomposition` | `baseline-profiles` (measure first) |
| cold start / first-scroll jank only | `baseline-profiles` | `recomposition` |
| dependency versions, catalog, BOM | `version-catalog` | `gradle-conventions` |
| screenshot / visual regression | `screenshot-testing` | `compose-ui-testing` |
| token storage, crypto, secret leak | `keystore-and-crypto` | `masvs-audit` |
| ship to Play, tracks, staged rollout | `release-flow` | `play-metadata` |

## Rules

1. **One skill per change.** If two skills genuinely apply, split the change into two commits
   and route each separately.
2. **Symptom ≠ task.** Convert to an artefact first: "it's slow" → which screen, which
   interaction, measured how? If the user cannot answer, ask exactly one clarifying question.
3. **Order matters for symptoms:** measure → diagnose → fix. Never route a performance
   complaint straight to a fix skill.
4. **Respect the do-not-use lists.** Every skill names its neighbours; those lists are the
   routing contract and override your intuition about the topic.
5. **Versions never come from a skill.** Any version mentioned in a skill is a catalog key or a
   URL; the project's `gradle/libs.versions.toml` wins.
6. **Missing coverage is an answer too.** If no skill covers the task, say so and proceed with
   the platform docs — do not stretch a neighbouring skill to fit.

## Checklist

- [ ] Exactly one domain skill chosen and named out loud.
- [ ] The task is an artefact ("edit X in file Y"), not a symptom.
- [ ] No version literal taken from skill prose.
- [ ] Multi-domain request split into ordered commits.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Vague request | guess and start editing | ask one clarifying question | wrong artefact changed |
| Two skills loaded | read both, mix rules | split the change | contradictory checklists |
| Perf complaint | jump to `recomposition` | measure first | optimise the wrong thing |
| No matching skill | force-fit the nearest | state the gap, use docs | fabricated rules |

## Verify

State in one line: `<skill-name> — because <artefact>`. If that line cannot be written, the
routing is not done.
