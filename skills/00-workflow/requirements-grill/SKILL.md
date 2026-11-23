---
name: requirements-grill
description: >-
  Interrogate a feature request until the unstated assumptions are decided, and refuse to write
  code while a requirement is still ambiguous. Use when starting any non-trivial feature, when
  a request is one sentence ("add a filter"), when the user says "you know what I mean", when
  scope is unclear, or when two people could build visibly different apps from the same brief.
license: Apache-2.0
metadata:
  domain: workflow
  level: core
  sources:
    - android-agent-engineering (workflows/requirements-grill)
    - mobile-agent-skillpack (brainstorming, story-splitting)
    - chrisbanes/skills (to-plan)
---

# Requirements Grill

An ambiguous requirement is a debt that gets paid with a rewrite. This skill's job: convert a
sentence into decisions, or refuse to proceed.

## Use when

- A feature request is one sentence, a screenshot, or a competitor reference.
- The words "simple", "just", "obviously", or "you know what I mean" appear.
- Two people could build visibly different apps from the same brief.
- Scope, data source, or error behaviour is unstated.
- You are about to ask "should I…?" — that question belongs in this grill, not in the code.

## Do not use when

- The requirement is already specified with acceptance criteria → `feature-to-spec`.
- The task is a defect with a reproduction → `bug-fix`.
- The change is a pure refactor with no behaviour change → `refactor`.

## Rules

1. **Ask one question at a time, and only questions whose answers change the code.** A grill is
   not a survey. Each question must map to a decision with two different implementations.
2. **Every grill produces a written answer for these eight slots.** Missing slot = not ready:
   1. **Actor & trigger** — who does what, from where (screen/deep link/widget/notification).
   2. **Happy path** — the exact steps and the observable result.
   3. **Data source** — local store, network, cached, derived; who owns it.
   4. **Empty / loading / error** — the three states a designer forgets and a user sees daily.
   5. **Boundaries** — limits, pagination, max length, rate, currency, locale, timezone.
   6. **Permissions & offline** — what happens when denied, revoked, or offline mid-flow.
   7. **Non-goals** — what this change explicitly does *not* do.
   8. **Done means** — the checkable acceptance criteria (numbers where possible).
3. **Ask about the *next* thing only after the current answer is decided.** Stacked questions get
   partial answers and produce a design built on guesses.
4. **Propose your interpretation, then ask if it is right.** "I'll treat filtering as client-side
   over the cached list, and the filter resets on app restart — correct?" gets a yes/no; "how should
   filtering work?" gets an essay or silence.
5. **Never fill a slot with an assumption and keep going silently.** Write it as
   `ASSUMED: <x> — confirm` in the spec. Assumptions are cheap when visible, expensive when hidden.
6. **Refuse to start when slot 7 (non-goals) or slot 8 (done) is empty.** Those two are what prevent
   the most rework; everything else can be discovered while building.
7. **Grill the failure modes, not the aesthetics.** "What if the list is 10,000 items?" and "what
   does the button do while the request is in flight?" change architecture; "should it be blue?"
   does not.
8. **Record the decisions where the code will live** (issue/spec file), not only in chat. A decision
   that exists only in conversation is lost at the next context switch.
9. **Three questions is a success, thirty is a survey.** If after ~8 questions a slot is still open
   because the user cannot answer, propose the simplest defensible default, mark it `ASSUMED`, and
   ship that decision into the spec for review.

## Procedure

1. Read the request; list what it *does not say*.
2. Convert each gap into a question with two candidate answers.
3. Ask the highest-impact question (usually data source or happy path first).
4. Fill the eight slots as answers arrive; mark `ASSUMED` where you decided.
5. Stop when slots 1–8 are filled and 7–8 are concrete.
6. Hand the filled slots to `feature-to-spec`.

## Checklist

- [ ] All eight slots filled or explicitly marked `ASSUMED`.
- [ ] Non-goals listed (at least one).
- [ ] Acceptance criteria are checkable and numeric where possible.
- [ ] Empty/loading/error described, not just happy path.
- [ ] Boundaries stated (limits, locale, timezone).
- [ ] Permission-denied and offline behaviour decided.
- [ ] Decisions written to a durable artefact, not just chat.
- [ ] No question left that would change the code.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Built the wrong thing | guess the data source | ask, with two concrete options | cheapest possible fix |
| Endless grill | 30 questions, no work | 8 slots, ≤~8 questions | analysis paralysis |
| Silent assumption | decide and code | `ASSUMED:` in the spec | invisible debt |
| Aesthetic questions first | "what blue?" | "what happens on error?" | architecture first |
| Design on guesses | 5 stacked questions | one question per turn | partial answers |
| Lost decisions | chat only | spec file + issue | context loss |

## Verify

The grill is complete when this sentence can be filled without inventing anything:

> "`<actor>` does `<action>` from `<entry point>`; success shows `<observable>`;
> failure shows `<state>`; it does **not** `<non-goal>`; done when `<numeric criterion>`."

If a clause cannot be filled, that slot is the next question.

Expected: the sentence can be filled without inventing anything; an unfillable clause is the next question.

## References

- Story-splitting heuristics for oversized requests: `mobile-agent-skillpack/story-splitting`
