---
name: compose-accessibility
description: >-
  Give every Compose node a defensible accessibility identity: content descriptions that describe
  purpose, correct roles and toggle state, 48dp targets, sane focus order, live announcements, and
  contrast that survives dark mode. Use when adding an image, icon button, custom toggle, custom
  gesture, dialog, or dynamic content; when TalkBack announces the wrong thing; or when auditing a
  screen before release.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - agent-skills-standard (android-accessibility)
    - awesome-android-agent-skills (android-accessibility)
    - android-agent-engineering (design-system/design-system-accessibility)
    - chrisbanes/skills (compose-focus-navigation)
---

# Compose Accessibility

Accessibility is the **semantics tree**, not an add-on. If TalkBack cannot describe and operate a
control, the control is broken for every non-visual user — and for automation, which reads the same
tree.

## Use when

- Adding an `Image`, `Icon`, `IconButton`, or a clickable custom-drawn area.
- Building a custom toggle, slider, chip, or segmented control.
- A gesture (`swipe`, `drag`, `long-press`) carries the only way to do something.
- Adding a dialog, snackbar, banner, or dynamically updating text.
- TalkBack reads "unlabelled button", two nodes for one control, or the wrong order.
- Pre-release accessibility audit.

## Do not use when

- The question is a component's parameter API → `compose-component-api`.
- The question is font-size/colour tokens → `design-system`.
- The question is bidi/RTL layout → `rtl-localization`.

## Rules

1. **Every meaningful image gets a description of its purpose, not its content.**
   `"Profile photo of Alex"` not `"image"`; `contentDescription = null` only for purely decorative
   graphics that a sighted user would also ignore.
2. **An icon inside a labelled button is decorative.** `Icon(..., contentDescription = null)` when
   the surrounding `Button` has text; the button's text is the label. Double announcement is a
   common defect.
3. **Custom controls must be operable, not just visible.** Use `Modifier.clickable(role = Role.Button)`,
   `Modifier.toggleable(value, role = Role.Switch, onValueChange)`, or
   `Modifier.selectable(selected, role = Role.Tab)` — the role is what makes TalkBack say "switch,
   on" instead of "button".
4. **`pointerInput` gestures need an accessible equivalent.** A swipe-to-delete needs a visible
   action (menu item or button); a drag needs `semantics { customActions = listOf(...) }` or an
   alternative control. Gesture-only functionality is inaccessible by construction.
5. **Touch targets ≥ 48dp, achieved with `Modifier.minimumInteractiveComponentSize()` or padding —
   never by shrinking padding to 0.** Visual size may stay smaller than the target.
6. **Merge or clear semantics deliberately.** A card whose title+subtitle should be one node:
   `Modifier.semantics(mergeDescendants = true) { }`. A wrapper that adds noise:
   `Modifier.clearAndSetSemantics { }`. Do not leave the default when either is wrong.
7. **Focus order is authored, not accidental.** Use `Modifier.focusProperties { next = … }` /
   `traversalIndex` when visual order and tree order diverge. Verify with TalkBack swipe navigation
   and with a hardware keyboard.
8. **Dynamic updates are announced.** Use `Modifier.semantics { liveRegion = LiveRegionMode.Polite }`
   for a status line, or `View.announceForAccessibility` at a boundary; a silent counter change is
   invisible to a screen-reader user.
9. **Contrast is measured, not assumed.** Body text ≥ 4.5:1, large text ≥ 3:1, icons ≥ 3:1 against
   the adjacent surface, in **both** themes. `surfaceVariant`/`outline` roles are where this usually
   fails.
10. **Layout must survive font scale 2.0 and display size large.** No fixed heights around text, no
    `maxLines = 1` on labels that matter, no `Ellipsis` on the primary action of a dialog.
11. **Every interactive element is reachable without touch.** Keyboard/D-pad/TalkBack all use the same
    focus system: if it is not focusable, it is not accessible.

## Procedure

1. Run the accessibility scanner / `adb shell uiautomator dump` and list unlabelled or duplicate nodes.
2. For each: decide decorative vs meaningful; set `contentDescription` or `null` (rules 1–2).
3. For custom controls: replace `clickable {}` with the correct `role`d modifier (rule 3).
4. Add alternatives / `customActions` for gesture-only behaviour (rule 4).
5. Fix targets to ≥48dp (rule 5).
6. Fix merge/clear semantics where nodes are split or noisy (rule 6).
7. Author focus order if the tree order is wrong (rule 7).
8. Set `liveRegion` on dynamic status text (rule 8).
9. Check contrast in both themes; check font scale 2.0.

## Checklist

- [ ] Every meaningful image has a purpose-describing label; decorative ones are `null`.
- [ ] No double announcement from icon + button label.
- [ ] Custom controls use `toggleable`/`selectable`/`clickable` with a correct `role`.
- [ ] Gesture-only actions have a visible or semantic alternative.
- [ ] All targets ≥48dp.
- [ ] Merge/clear semantics applied where the default is wrong.
- [ ] Focus order verified with TalkBack and a keyboard.
- [ ] Dynamic status text uses `liveRegion`.
- [ ] Contrast ≥4.5:1 (body) / 3:1 (large, icons) in light **and** dark.
- [ ] Renders at font scale 2.0 without clipping the primary action.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| "Unlabelled button" | `IconButton { Icon(painter, null) }` | `IconButton` with `contentDescription` on the icon | no label at all |
| Double announcement | icon description inside a text button | `contentDescription = null` for the icon | TalkBack repeats |
| "Button" for a switch | `clickable { toggle() }` | `toggleable(state, role = Role.Switch)` | no state in announcement |
| Swipe-only delete | drag gesture only | visible action + gesture | inaccessible |
| Tiny target | 24dp icon, 0 padding | `minimumInteractiveComponentSize()` | motor accessibility |
| Wrong order | tree order ≠ visual order | `focusProperties`/`traversalIndex` | confusing navigation |
| Silent update | counter text changes | `liveRegion` | screen reader never says it |
| Low contrast chips | `surfaceVariant` on `surface` | adjust role or token | unreadable in one theme |
| Clipped dialog action | `height(64.dp)` | `heightIn(min = …)` | font scale 2.0 |

## Verify

```bash
adb shell settings put secure enabled_accessibility_services com.google.android.marvin.talkback/...
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml
grep -c "content-desc=\"\"" /tmp/ui.xml     # unlabelled nodes
./gradlew :app:lintDebug                    # ContentDescription, TouchTargetSize
```

Then enable TalkBack and walk one screen end to end: every control must be announced with its role
and state, and every action must be reachable by swiping, without reading anything twice.

## References

- Android accessibility semantics mapping for Compose (`contentDescription`, `role`, `stateDescription`)
- WCAG 2.2 contrast minimums; Android `TouchTargetSizeCheck` lint
