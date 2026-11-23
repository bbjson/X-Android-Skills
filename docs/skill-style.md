# Skill Authoring Standard

Every skill in this repository follows the same skeleton. Deviations must be justified.

## Why a fixed skeleton

An agent loads a skill *after* it has already decided the task is relevant. What it needs at
that moment is: a decision rule, the constraints, a checklist it can self-verify against, and
the traps. Not prose, not background, not a tutorial.

Every skill is written to be **verifiable**: a reviewer (human or agent) can read the skill,
read the diff, and decide pass/fail without asking a follow-up question.

## Frontmatter

```yaml
---
name: compose-state-effects            # kebab-case, matches directory name
description: >-
  One or two sentences. First clause states WHAT the skill covers. Second clause
  ("Use when ...") states the exact trigger conditions. Never write "Helps with X".
license: Apache-2.0
metadata:
  domain: compose
  level: core            # core | advanced | specialized
  sources:               # upstream projects this was distilled from
    - chrisbanes/skills
    - skydoves/compose-performance-skills
---
```

Rules:

1. `description` is the only thing the agent sees before loading. It decides routing.
   Name the *task shapes* and *file types* that should trigger it.
2. `metadata.sources` records provenance. Consolidation must be attributable.
3. `name` must equal the containing directory name. The validator enforces this.

## Body sections, in order

| Section | Required | Content |
|---|---|---|
| `# Title` | yes | Human name, not the slug |
| `## Use when` | yes | Bulleted trigger conditions, phrased as observable situations |
| `## Do not use when` | yes | The neighbouring skill that *does* apply, by name |
| `## Rules` | yes | Numbered, imperative, falsifiable. Each rule is one decision |
| `## Procedure` | when >5 steps | Ordered steps with the command/file each touches |
| `## Checklist` | yes | `- [ ]` items a reviewer can tick off against a diff |
| `## Anti-patterns` | yes | Concrete wrong code/config and why it fails, in a table |
| `## Verify` | yes | Commands or observable outcomes that prove the work is done |
| `## References` | optional | Upstream docs; never restate them |

## The version rule (most important)

**Skills must not pin dependency versions.**

Every upstream Android skill bundle we audited had rotted in exactly one way: a literal
`agp = "8.2.0"` or `kotlin = "1.9.20"` inside the instructions, which the agent then copies
into a fresh project and breaks. Here versions come from one place only:

1. Read the project's `gradle/libs.versions.toml` (or `build.gradle.kts` if absent).
2. If a version must be mentioned, write it as the *catalog key*: `libs.androidx.compose.bom`.
3. If the project has no catalog, say "use the latest stable from `maven-metadata.xml`" and
   give the URL, not a number.

Only exceptions: version-locked migrations (e.g. `agp9-migration`) may name the *from* version,
because that is the subject of the skill.

## Rule quality bar

A rule is only allowed if all three hold:

- It changes a decision the agent would otherwise get wrong.
- It can be checked against a diff.
- It is not restating a platform API name.

Bad: "Use StateFlow for state." (not a decision — nothing to choose)
Good: "If the UI must never miss an event, use `Channel` + `receiveAsFlow()`, not `SharedFlow`
with a buffer; state gets `StateFlow`." (a decision, checkable)

## Anti-pattern table format

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| ... | `code` | `code` | one line |

## Length

- Core skills: 80–200 lines. If longer, you are teaching, not constraining — split it.
- Migration skills: up to 300 lines, organised as Before/After pairs.
- Never exceed 400. An agent that must read 1000 lines to find a rule will drop rules.

## Language

Skill bodies are English: it tokenises predictably and the rules are quoted verbatim into
agent reasoning. Repository prose (README, docs) is bilingual.

## Reviewing a skill

```
tools/validate.py            # structure, frontmatter, hardcoded versions, length budget
tools/check_refs.py          # neighbour references must resolve to a real or planned skill
tools/audit_duplicates.py    # rule-level overlap report (an aid, not a judge)
tools/check_routing.py       # behavioural test: task -> expected skill
```

A skill is merge-ready when all four pass **and** every `## Verify` command was run once
on a real project.

A Verify pass was executed on 2026-11-23 against a real project on a real emulator; it found
8 skill defects (wrong task names, a dead Compose compiler property, a bogus `-P` property, a
non-existent adb subcommand, outdated Gradle output matching, and two inaccurate rules). All are
fixed. See `docs/verify-report.md` for the environment, the evidence, and the explicit list of
what could **not** be verified (Roborazzi, Macrobenchmark, Hilt/Koin, Room/KSP, KMP, Play Console,
kernel).

The rule this establishes: **a command that fails on first contact is a skill bug, not a project
problem.** Re-run `tools/verify_skills.py` whenever a tool version changes.
