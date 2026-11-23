---
name: rtl-localization
description: >-
  Make layouts and strings survive right-to-left locales, longer translations and plural rules:
  start/end instead of left/right, auto-mirrored icons, bidi text mixing, quantity strings, and
  localized number/date formatting. Use when shipping a locale with RTL text, when a layout breaks
  in German or Arabic, when an icon points the wrong way in RTL, or when a string is assembled from
  fragments.
license: Apache-2.0
metadata:
  domain: compose
  level: advanced
  sources:
    - android-agent-engineering (design-system/rtl-localization)
    - agent-skills-standard (android-resources)
    - agent-skills-standard (android-legacy-state) — legacy `start`/`end` behaviour
    - kotlin-footguns (compose-visuals-footguns)
---

# RTL and Localization

Localization is not translation: it is **layout direction plus text expansion plus grammar**. A
translated string in a left-to-right layout is still broken for an RTL user.

## Use when

- Adding an RTL locale (ar/he/fa/ur) or a locale with much longer strings (de/ru/fi).
- An icon, chevron, or progress indicator points the wrong way in RTL.
- A layout clips or overflows after translation.
- A string is built by concatenating fragments, or a count changes a noun form.
- Dates, numbers, or currency render in the wrong format for a locale.

## Do not use when

- The question is spacing/colour tokens → `design-system`.
- The question is accessibility semantics → `compose-accessibility`.
- The question is string resource *organisation* only → `compose-core` rule 10.

## Rules

1. **Use `start`/`end`, never `left`/`right`, everywhere:** `padding`, `offset`, `Alignment.Start`,
   `horizontalArrangement`. In Compose this is `Arrangement.Start`/`Alignment.Start`; in XML the
   `start`/`end` attributes. A single `left` is a bug in every RTL locale.
2. **Mirror icons that encode direction, never the ones that do not.** Use
   `Icons.AutoMirrored.Filled.ArrowBack`/`Send`/`List`; do not mirror a camera, clock, or logo.
   A chevron rendered with `scaleX = -1` on all icons flips the wrong ones.
3. **Assume text grows ~30% and can shrink.** No fixed-width buttons around a label; `wrapContentWidth`
   with `maxLines`+`Ellipsis`; never `width(200.dp)` on a text container.
4. **Never concatenate translated fragments.** `"$count items"` and `"Delete " + name` are both
   unfixable in languages with different word order or case. Use one resource with placeholders:
   `str(R.string.delete_named, name)` where the resource is `Delete %1$s`.
5. **Quantity uses plurals, not `if (n == 1)`.** `pluralStringResource(R.plurals.items, n, n)`.
   Languages have 2–6 plural categories (zero/one/two/few/many/other); a boolean check is wrong in
   most of them.
6. **Numbers, dates, currency, and percentages go through `Locale`-aware formatters.**
   `NumberFormat.getCurrencyInstance(locale)`, `DateTimeFormatter.ofLocalizedDate(...)`. A hardcoded
   `"%d items"` or `SimpleDateFormat("MM/dd/yyyy")` is a locale bug.
7. **Bidi mixing needs isolation.** A Latin brand name inside Arabic text renders out of order unless
   isolated: wrap with `\u2068…\u2069` (FSI/PDI) or use `BidiFormatter`. Applies to user names, ids,
   file names, and phone numbers.
8. **Direction is a `CompositionLocal`, and previews must exercise it.**
   `CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) { … }` in a
   `@Preview`. Testing only LTR means shipping blind.
9. **Do not rely on the text field's direction to imply the content direction.** An Arabic name typed
   in an LTR field must still lay out RTL: set `textDirection`/`TextAlign` from the content, not the
   form locale.
10. **Pseudo-localization is the cheapest test.** A one-time build with `en-XA` (expanded) and
    `ar-XB` (RTL) surfaces hardcoded strings and clipped layouts before translation starts.
11. **Locale-dependent behaviour is not only UI.** Sorting/collation, first day of week, decimal
    separator, and toast/notification text all follow the same rules — check them in the same pass.

## Procedure

1. Grep for direction bugs:
   ```bash
   grep -rnE "padding\(start|padding\(left|Alignment\.CenterStart|Alignment\.Start" --include=*.kt -- | head
   grep -rnE "\.left|\.right|layout_marginLeft|layout_marginRight" --include=*.kt --include=*.xml . | head
   grep -rn "AutoMirrored" --include=*.kt . | wc -l
   ```
2. Convert `left`/`right` to `start`/`end`.
3. Replace directional icons with `AutoMirrored` variants; leave non-directional ones untouched.
4. Rewrite concatenated strings as single resources with positional placeholders.
5. Replace `if (n == 1)` with `plurals`.
6. Route formatters through `Locale`.
7. Add an RTL `@Preview` per screen; run pseudo-locales once.
8. Verify bidi isolation on free-text fields.

## Checklist

- [ ] No `left`/`right` in layout code or XML.
- [ ] Directional icons use `AutoMirrored`; non-directional icons not mirrored.
- [ ] No fixed widths around translated labels.
- [ ] No concatenated strings; placeholders with positional args.
- [ ] Quantities use `plurals`.
- [ ] Numbers/dates/currency use locale-aware formatters.
- [ ] Bidi-sensitive user content isolated (FSI/PDI or `BidiFormatter`).
- [ ] RTL `@Preview` exists for each screen.
- [ ] Pseudo-locale build (`en-XA`/`ar-XB`) checked once.
- [ ] Input fields set direction from content, not form locale.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Padding on wrong side in RTL | `padding(start = 16.dp)` implemented with left | `start`/`end` API | mirrors |
| Back arrow points right | `Icons.Filled.ArrowBack` | `Icons.AutoMirrored.Filled.ArrowBack` | direction-encoding icon |
| Logo mirrored | global `scaleX = -1` | mirror only directional icons | brand damage |
| German button clipped | `width(140.dp)` | `wrapContentWidth` + ellipsis | text expansion |
| Broken sentence | `"Delete " + name + "?"` | `str(R.string.delete_named, name)` | word order/case |
| Wrong plural | `if (n == 1) "item" else "items"` | `plurals` | 2–6 categories |
| US date in EU | `MM/dd/yyyy` | localized formatter | locale |
| Scrambled mixed text | Latin name in Arabic inline | FSI/PDI isolation | bidi algorithm |
| Blind shipping | only LTR previews | RTL preview + pseudo-locale | never seen |

## Verify

```bash
adb shell "setprop persist.sys.locale ar-EG; stop; start"    # device-level RTL (reboot-ish)
./gradlew :app:assembleDebug
# plus a Rtl preview: CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl)
grep -rn "layout_marginLeft\|paddingLeft" --include=*.xml --include=*.kt .   # must be empty
```

Expected: with the device in an RTL locale, every screen mirrors correctly, directional icons point
the right way, no text clips, and lists/forms remain operable.

## References

- `LocalLayoutDirection`, `Icons.AutoMirrored`, `BidiFormatter`
- Pseudo-locales `en-XA` (expanded) and `ar-XB` (RTL) for pre-translation testing
