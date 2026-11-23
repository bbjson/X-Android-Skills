# AGENTS.md — X-Android-Skills

Project-level conventions. Every agent working **on this repository** reads this first.
For conventions an agent should follow when using these skills **in an app project**, see
`docs/skill-style.md` (authoring) and `skills/router/SKILL.md` (routing).

## What this repository is

A distilled, deduplicated set of Android agent skills assembled from 33 public skill
repositories (see `docs/provenance.md`). The value is not coverage — it is that every rule
here survived a conflict resolution between upstream sources, and that no rule can rot into a
stale version number.

## Non-negotiables

1. **No hardcoded dependency versions.** Only catalog keys (`libs.*`) or `maven-metadata.xml`
   URLs. `tools/validate.py` warns on violations; warnings must be justified in the PR.
2. **No rule without a decision.** "Use Compose" is not a rule. "If the UI must never miss an
   event, use Channel-backed flow, not SharedFlow with replay" is.
3. **Provenance is recorded** in `metadata.sources`. Adding content from a new upstream means
   adding the source.
4. **One skill, one decision surface.** If a skill needs two `## Rules` sections that do not
   talk to each other, it is two skills.
5. **Length budget.** core ≤ 200 lines, advanced ≤ 260, specialized/migration ≤ 400. Over
   budget means teaching, not constraining.
6. **Every `## Verify` command must be one that was actually run.** Do not invent gradle tasks.

## File layout

```
skills/<NN-domain>/<slug>/SKILL.md    # slug == frontmatter name
skills/router/SKILL.md                # routing fallback
templates/SKILL.template.md           # authoring template
tools/validate.py                     # structure + version-rule check
tools/install.sh                      # install into an agent skill dir
docs/skill-style.md                   # authoring standard (authoritative)
docs/provenance.md                    # upstream sources and what was taken
```

## Before committing

```bash
python3 tools/validate.py
python3 tools/check_refs.py
python3 tools/check_routing.py
./tools/install.sh --list | tail -3
# when a tool version changed, re-run the Verify pass (needs a real project + device):
# python3 tools/verify_skills.py --fixture ~/Desktop/verify-fixture
```

All must be clean. A skill that only "reads well" is not done. A skill whose `## Verify`
commands were never executed is a hypothesis — say so when adding one.

## Domain numbering

`00` workflow · `10` architecture · `20` compose · `30` performance · `40` build ·
`50` quality · `60` security · `70` release · `80` device · `90` platform · `95` migration

Numbering is stable. New skills take a free number inside the closest domain; renumbering is
forbidden because it breaks saved routing tables.

## What NOT to add

- Framework-specific app code, sample apps, or generated projects.
- Restatements of platform documentation (link instead).
- Tool marketing, version-chasing "latest and greatest" advice.
- Skills for niche SDKs from a single vendor — keep those out of the core set.
