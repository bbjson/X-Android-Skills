---
name: compose-component-api
description: >-
  Design the API of a reusable Composable so callers can extend it without forking it: slots
  instead of booleans, no default colours, no ViewModel parameters, and semantics that survive
  theming. Use when extracting a component for reuse, converting a screen-specific Composable into
  a shared one, when a component accumulates Boolean flags, when callers need to inject their own
  content, or when a design-system component must work in light/dark/RTL/large-font without edits.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - chrisbanes/skills (compose-component-design)
    - agent-skills-standard (android-compose)
    - Meet-Miyani-compose-skill (compose-ui)
    - agent-skills-standard (android-design-system)
---

# Compose Component API

A reusable component is a **contract**, not a screen that got moved. The contract is: what the
caller controls, what the component controls, and what happens when content does not fit.

## Use when

- Extracting a Composable that a second screen wants to use.
- A component's signature has grown booleans (`showIcon`, `dense`, `isError`, `withDivider`).
- Callers need to place their own content inside a component.
- A shared component hardcodes colours/sizes and breaks in dark theme or with large fonts.
- A component takes a `ViewModel`, an `Activity`, or a navigation callback from deep inside.

## Do not use when

- The component is used by one screen only — keep it local and skip this skill.
- The question is theme tokens themselves → `design-system`.
- The question is state ownership inside the component → `compose-state-effects`.

## Rules

1. **Slots replace variations.** A `content: @Composable () -> Unit` (or `RowScope.() -> Unit`)
   parameter serves "I need my own icon/text/extra row" better than three booleans. Booleans
   multiply: 3 booleans = 8 variants, most of which nobody tested.
2. **Two modes only: stateless (recommended) or self-contained.** Stateless takes a value and
   emits events. Self-contained owns its own state and is rare (e.g. a disclosure section).
   Never half-and-half: a component that owns state *and* accepts an override value has two
   sources of truth.
3. **Never accept a `ViewModel`, `NavController`, or `Context` for navigation.** The component emits
   `onClick: () -> Unit` / `onAction: (Action) -> Unit`; the screen decides what that means. This is
   what makes it previewable and testable.
4. **No default colours, no default `dp`.** Colours come from `MaterialTheme.colorScheme` (or a DS
   token), spacing from the theme. A hardcoded `Color(0xFF6200EE)` is the definition of a component
   that will not survive a rebrand or dark mode.
5. **Sizes are content-driven unless a size is part of the contract.** `Modifier.height(56.dp)` on a
   button is contract; the same on a card is a bug that clips large fonts (see rule 7).
6. **Expose semantics, not appearance.** Parameters named after meaning (`state: ButtonState`,
   `emphasis: Emphasis`) age well; parameters named after pixels (`paddingStart`, `iconSize`) pin the
   implementation. Appearance knobs belong in a slot or a `Modifier`.
7. **Must survive: dark theme, RTL, font scale 2.0, and a long loading state.** Test all four in
   `@Preview` before calling the component done. Use `start`/`end`, never `left`/`right`; no fixed
   `height` on text containers.
8. **Accessibility is part of the contract.** One `contentDescription` per meaningful image, a
   clickable node with `role`, and a touch target ≥48dp. A component that fires an action on
   `pointerInput` without `clickable` is invisible to TalkBack.
9. **Every component ships with at least one `@Preview` and one UI test.** The preview carries the
   state matrix (default/pressed/disabled/error); the test asserts the emitted event, not the pixels.
10. **Version the API in your head: a shared component's signature is a public API.** Renaming a
    parameter breaks every call site; adding a required one is a breaking change. Add optional
    parameters with defaults instead.

## Procedure

1. List what varies across call sites; each item becomes a parameter or a slot.
2. Collapse boolean clusters into a single enum/sealed type or a slot.
3. Move navigation/DI out: replace with lambdas.
4. Replace literal colours/sizes with tokens.
5. Write the signature in rule-1 order, apply rule 2's mode decision.
6. Add previews: default, disabled, loading, long text, RTL, font scale 2.0.
7. Add the UI test asserting the event/state output.

## Checklist

- [ ] Varying behaviour expressed as slots or one enum, not ≥3 booleans.
- [ ] Stateless with hoisted state, or fully self-contained — not both.
- [ ] No `ViewModel`/`NavController`/`Context` parameter for navigation.
- [ ] No literal colours or spacing.
- [ ] Uses `start`/`end`, no fixed text heights.
- [ ] Clickable nodes have `role` and ≥48dp target.
- [ ] Previews cover state matrix + RTL + font scale 2.0.
- [ ] At least one UI test asserts the emitted event.
- [ ] Signature change is additive with defaults.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Boolean explosion | `showIcon, showDivider, dense, isError` | `content` slot + `state` enum | 16 untested variants |
| Untestable | `onNavigate(navController, "detail")` | `onClick: () -> Unit` | component owns routing |
| Breaks in dark mode | `Color.Black` text | `MaterialTheme.colorScheme.onSurface` | hardcoded palette |
| Clipped at 2x font | `Modifier.height(48.dp)` on text row | `heightIn(min = …)` | text needs to grow |
| RTL broken | `padding(start = 16.dp)` implemented as `left` | `start`/`end` | mirroring |
| Invisible to TalkBack | `Modifier.pointerInput { detectTapGestures }` | `Modifier.clickable(role = Role.Button)` | no semantics node |
| Callers fork the component | copy it and edit | add a slot | duplication forever |

## Verify

```bash
./gradlew :core:designsystem:assembleDebug
./gradlew :core:designsystem:testDebugUnitTest
```

Preview matrix check: default, disabled, loading, 200-char text, `LayoutDirection.Rtl`, font scale
2.0 — no clipping, no colour outside the theme, action still reachable by a single tap.

## References

- Compose API guidelines — slots, `modifier`, and "emit events, don't navigate"
- `Modifier.semantics`, `Role`, `Modifier.minimumInteractiveComponentSize`
