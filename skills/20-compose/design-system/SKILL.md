---
name: design-system
description: >-
  Build the token layer that every screen reads from — semantic colour roles, a spacing scale,
  typography and shape — and decide what belongs inside the shared design system versus an app.
  Use when creating theme architecture, adding a colour/size/typography value, seeing hardcoded
  colours or dp literals in app code, supporting dark theme or dynamic colour, or deciding whether
  a component or token should be shared across apps.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - android-agent-engineering (design-system/design-tokens, compose-theming, design-system-boundary)
    - agent-skills-standard (android-design-system)
    - material-3-expressive-skill
    - chrisbanes/skills (compose-component-design)
---

# Design System

Three layers, one direction: **primitive → semantic → component**. App code reads semantic
tokens only. A component that reads a primitive is a design-system bug, not a convenience.

## Use when

- Setting up `MaterialTheme`/`XTheme` and its token extensions.
- Adding or changing a colour, spacing value, radius, elevation, or type style.
- App code contains `Color(0x…)`, `16.dp`, `sp`, or `R.color.*` inside Composables.
- Supporting dark theme, dynamic colour, or a brand switch.
- Deciding whether a piece of UI or a token belongs in the shared module.

## Do not use when

- The question is a single component's parameter API → `compose-component-api`.
- The question is RTL/bidi layout mechanics → `rtl-localization`.
- The question is an accessibility audit of components → `compose-component-api` + `masvs-audit` (roadmap).

## Rules

1. **Three token layers, and app code may only use the middle one.**
   - Primitive: `brandBlue500`, raw `Color(0xFF…)` — exists only inside the DS module.
   - Semantic: `colorScheme.primary`, `spacing.md`, `typography.titleLarge` — the only thing app
     code reads.
   - Component-scoped: `ButtonDefaults.containerColor` — derived from semantic, not from primitives.
2. **Semantic names describe role, not appearance.** `colorScheme.surfaceVariant` /
   `contentColorFor(surface)` / `danger` — never `lightGrayText` or `purpleButton`. Appearance-named
   tokens cannot survive dark mode or a rebrand.
3. **One spacing scale, small and closed.** A geometric or 4dp-based scale (`xs, sm, md, lg, xl`)
   exposed as a `Spacing` holder in the theme. Adding `17.dp` at a call site is a review finding.
   If a design needs a value outside the scale, the scale is wrong — change it once.
4. **Typography through one type scale.** Use `MaterialTheme.typography` or a DS extension
   (`XTheme.typography`); no inline `fontSize = 13.sp`, no `fontWeight` overrides at call sites.
   Line height belongs to the style, not the caller.
5. **Colours must be resolved by the theme, not computed by the caller.** `MaterialTheme.colorScheme`
   plus `contentColorFor()` for children; `LocalContentColor` for nested content. Dark mode then
   works without touching components.
6. **Dynamic colour is opt-in and must not break the brand.** If enabling it, keep the semantic
   layer identical and only swap the source palette; verify contrast on generated palettes, and
   provide a setting to fall back to the brand palette.
7. **The DS boundary is decided by consumers, not by convenience.** A component/token goes into the
   shared module when **≥2 apps or ≥3 unrelated features** need it *and* it has no dependency on
   app-specific data types. A screen-shaped Composable with a `FeedUiState` parameter is an app
   component even if it is reused once elsewhere.
8. **The DS module must not depend on app data types.** No `domain` models, no repository. If a
   component needs domain data, it takes primitives or a `content` slot.
9. **Every token change is verified in both themes and at font scale 2.0.** A token that only looks
   right in light mode at 1.0 is unfinished; contrast is measurable (WCAG AA 4.5:1 for body text).
10. **Tokens are additive; renames are migrations.** Removing a token breaks every call site at
    compile time — fine — but changing a token's *value* silently restyles the whole app. Treat a
    value change as a design change requiring a visual review.

## Procedure

1. Inventory literals:
   ```bash
   grep -rnE "Color\(0x|\.dp\b|fontSize\s*=" --include=*.kt feature/ app/src | head -30
   grep -rn "R\.color\." --include=*.kt feature/ | head
   ```
2. Define primitives in the DS module (private to it).
3. Define semantic tokens: `ColorScheme`, `Spacing`, `Shapes`, `Typography` holders.
4. Expose via `XTheme { content }` with `CompositionLocal`s, each with a sensible default so
   previews work without wrapping.
5. Replace app-site literals with semantic tokens, screen by screen.
6. Verify: both themes, font scale 2.0, contrast check on text roles.
7. Document the boundary rule (rule 7) in the DS module README.

## Checklist

- [ ] Primitives exist only inside the DS module.
- [ ] App code reads semantic tokens only (`colorScheme`, `spacing`, `typography`).
- [ ] Token names describe role, not appearance.
- [ ] Single closed spacing scale; no off-scale literals in app code.
- [ ] No inline `fontSize`/`fontWeight` in screens.
- [ ] `CompositionLocal` tokens have defaults so `@Preview` works unwrapped.
- [ ] Dynamic colour (if enabled) verified for contrast + brand fallback.
- [ ] DS module has no dependency on app/domain types.
- [ ] Boundary rule written down and applied to recent additions.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Breaks in dark mode | `Color(0xFF212121)` | `colorScheme.onSurface` | literal ignores theme |
| Off-scale spacing | `padding(17.dp)` | `spacing.md` | design drift, unreviewable |
| Token named by look | `lightGrayText` | `onSurfaceVariant` | cannot invert in dark mode |
| DS depends on app | `fun FeedCard(state: FeedUiState)` in DS | primitives + `content` slot | DS tied to one app |
| Inline type tweak | `fontSize = 13.sp` | `typography.labelMedium` | type scale bypassed |
| Silent restyle | change token value in DS | design review + screenshots | touches every screen |
| Unpreviewable theme | `CompositionLocal` without default | provide default | every Preview must wrap |

## Verify

```bash
./gradlew :core:designsystem:assembleDebug
grep -rnE "Color\(0x" --include=*.kt feature/ app/src | grep -v designsystem   # must be empty
./gradlew :app:lintDebug
```

Expected: no colour/dimension literals outside the DS module, and every screen renders correctly
with `darkColorScheme` and font scale 2.0 without edits.

## References

- Material 3 colour roles (`surface`, `onSurface`, `surfaceVariant`, `outline`)
- `CompositionLocal` + `staticCompositionLocalOf` vs `compositionLocalOf` (invalidation cost)
