# Provenance

Every rule in this repository came from a specific upstream file. This document records what
was taken, what was rejected, and why — so a future maintainer can re-check a decision instead
of re-reading 1060 SKILL.md files.

Audited: 33 repositories, 1060 `SKILL.md` files, 366 MB (2026-11-23).

## Upstream inventory

| Repo | skills | Android relevance | Disposition |
|---|---|---|---|
| `agent-skills-standard` | 788 (31 android + 4 kotlin) | high | **Adopted** domain coverage + taxonomy; rejected 750 non-Android skills and the 93 MB website/benchmark scaffolding |
| `mobile-agent-skillpack` | 61 | mixed | **Partially adopted** — `android-logcat-root-cause`, `android-release-checklist`, `android-api-dto-safety`; rejected generic coding skills (TDD, PDF, brainstorming) that duplicate the agent harness |
| `compose-performance-skills` (skydoves) | 26 | very high | **Adopted** the measurement chain: stability inference → diagnosis → fix → CI gate → baseline profile. Deepest source on recomposition |
| `android-agent-engineering` | 24 | high | **Adopted** design-system sub-domain split and the workflow chain (requirements-grill → spec → plan → implement → review) |
| `android-skill` (mazWaz) | 23 | very high | **Adopted** operational verbs: `fix-build`, `modularize`, `setup-ci`, `release-check`, `snapshot-tests`; also the AGP 9 era baseline |
| `skills` (chrisbanes) | 21 | very high | **Adopted** decision-style rule phrasing ("give every piece of UI state one lowest responsible owner") and `compose-focus-navigation`. Best writing in the corpus |
| `google-play-cli-skills` | 19 | high | **Adopted** the release/operations chain: tracks, release-flow, signing, recovery, vitals, monetization |
| `awesome-android-agent-skills` | 17 | high | **Adopted as a completeness check only** — its AGP 8.0/8.2 and espresso 3.5.1 pins are stale; content is superseded |
| `kotlin-kmp-claude-agent-skills` | 15 | medium | **Adopted** into `kmp` (source-set + expect/actual wording) |
| `kotlin-footguns` (maxrave) | 11 | medium | **Adopted** the "run the discriminating experiment first" debugging method and the footgun-scan idea |
| `android-adb-skill` | 11 | high | **Adopted** as the basis for `adb-automation` |
| `kotlin-agent-skills` (JetBrains) | 10 | medium | **Adopted** migration framing for `agp9-migration`, `java-to-kotlin`, `cocoapods-to-spm`; longest files in the corpus (494–523 lines) but include the version-transition exemption we allow |
| `Meet-Miyani-compose-skill` | 7 | high | **Reference only** — overlaps `compose-component-api`; its `>-` YAML multiline descriptions are a frontmatter defect |
| `pushengage-skills` | 6 | low | **Rejected** — single-vendor SDK integration |
| `compose-ai-tools` (yschimke) | 3 | low | **Rejected** — 192 MB, its skills are about its own render plugin |
| `store-ready` | 1 | high | **Adopted** the pre-submission audit checklist shape |
| `app-store-compliance` | 1 | high | **Adopted** the enterprise submission audit categories |
| `material-3-expressive-skill` | 1 | medium | **Adopted** (M3 Expressive token ideas) into `design-system` |
| `kmp-compose-multiplatform-skill` | 1 | medium | **Rejected** — 1082 lines, violates the length budget by 3x |
| `CreditTone/...reverse-engineering` | 1 | medium | **Partially adopted** into `reverse-engineering` (tool chain only; authorisation-first framing added) |
| `android-reverse-engineering-skill` (8.7k★) | 1 | medium | **Partially adopted** same as above |
| `android-kernel-lkm` | 1 | niche | **Kept as `specialized`** (798 lines, exempted: kernel work is genuinely long) |
| `android-mainline-port` | 1 | niche | **Adopted** as `specialized`, Chinese-language notes preserved |
| `claude-android-ninja` | 1 | high | **Reference** — AGP 9.2+ assumptions, too aggressive for a default |
| `Appium-Scripter` | 1 | low | **Rejected** — 2605 lines |
| `micorlov-e2e-mobile` | 1 | medium | **Adopted** into `e2e-device-testing` (evidence-on-failure + no-sleep rules) |
| others (1 each) | 8 | low | **Rejected** unless noted: `phone-spyware-check` (consumer tool), `android-qa-kit`, `android-rea`, `droid-skills`, `compose-skill`, `jetpack-compose-skills`, `Compose-Circuit-Skills`, `kmp-compose-multiplatform-skill` — all overlap adopted skills with less depth |

## Cross-cutting findings

1. **Every bundle rotted the same way**: a literal AGP/Kotlin version in prose. `awesome-android-agent-skills` (AGP 8.2.0, Kotlin 1.9.20), `compose-performance-skills` (AGP 8.2), `android-testing` (espresso 3.5.1). Measured against `maven-metadata.xml`: AGP is at 9.6.0-alpha05, Kotlin 2.5.0-RC, Hilt 2.60.1. Hence the version rule in `docs/skill-style.md`.
2. **Duplication is severe**: 330 Android-relevant skills, but ~90 distinct decisions. The corpus needs consolidation more than it needs coverage.
3. **The best-written source is the smallest**: `chrisbanes/skills` (21 skills) states decisions; `agent-skills-standard` (788) mostly states facts.
4. **4 repositories have no LICENSE** (`android-skill`, `Appium-Scripter`, `micorlov-e2e-mobile`, `mobile-agent-skillpack`). Nothing verbatim was copied from them — only ideas were re-expressed.
5. **Longest ≠ best**: `Appium-Scripter` 2605 lines, `kmp-compose-multiplatform-skill` 1082, `kotlin-agent-skills` 494–523. All exceed what an agent reliably follows.

## Rule attribution format

Each skill's `metadata.sources` lists the repos it distilled. When a rule contradicts a source
(e.g. the `StrongSkippingMode` flag advice in older Compose material is obsolete), the source is
still listed and the contradiction is noted in `## Anti-patterns` so a reader can see the revision.
