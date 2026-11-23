---
name: java-to-kotlin
description: >-
  Convert Java classes to idiomatic Kotlin without changing behaviour or breaking Java callers:
  nullability boundaries, properties vs accessors, statics, interop annotations, and the platform-type
  traps. Use when converting a file or module, when a converted class throws
  NullPointerException, when Java callers break after conversion, or when deciding how far to "Kotlinise".
license: Apache-2.0
metadata:
  domain: migration
  level: migration
  sources:
    - kotlin-agent-skills (kotlin-tooling-java-to-kotlin)
    - mobile-agent-skillpack (kotlin-null-safety)
    - agent-skills-standard (java, kotlin)
    - kotlin-footguns (engineering-method-footguns)
---

# Java to Kotlin

The converter produces compilable Kotlin. This skill produces Kotlin that **Java callers can still
use** and that does not turn a compile-time story into a runtime nullability story.

## Use when

- Converting a class/module from Java to Kotlin (converter output needs review).
- A converted class throws `NullPointerException` where the Java version did not.
- Java code in the same module fails to compile after a conversion.
- Deciding how much Kotlin idiom to apply in a mixed codebase.

## Do not use when

- The target is a coroutine migration → `rxjava-to-coroutines`.
- The class is dependency-injection wiring → `dependency-injection`.
- The issue is Kotlin/JVM version alignment → `kotlin-toolchain`.

## Rules

1. **Convert one class at a time, keeping the public signature stable.** A module-wide conversion hides
   which change broke Java callers; a class-wide one has a reviewable diff.
2. **Java callers see platform types (`T!`), not `T`.** Parameters coming from Java are `!` and can be
   null at runtime. Annotate the Java source with `@Nullable`/`@NonNull` (or convert the *callers*
   first), otherwise Kotlin's non-null parameters will throw on data that used to flow through.
3. **Properties are not accessors with a different name in interop.** `val x` generates `getX()`;
   `var x` generates `getX()/setX()` — but a Java caller calling `setX` on a `val` breaks. Convert
   fields to properties only when the accessor pair is complete.
4. **Static members need `@JvmStatic`/`@JvmField`/`const` for Java callers.** A top-level function or a
   `companion object` member without `@JvmStatic` is `FooKt.foo()` / `Foo.Companion.foo()` from Java —
   a compile break that looks like a missing method.
5. **No `!!` as a conversion shortcut.** `!!` converts a Java nullability risk into a guaranteed crash.
   Use `?:`, `requireNotNull` with a message, or make the type nullable and handle it. Grep your own
   diff for `!!` before review.
6. **Checked exceptions become unchecked.** A Kotlin function does not declare `throws`; Java callers
   that relied on the compiler to force a catch will now fail to compile. Add `@Throws(IOException::class)`
   where Java callers must catch.
7. **Overload resolution changes.** Kotlin's `Int`/`Long`/`String` overloads and default arguments can
   make a Java call ambiguous or select a different overload. Keep the original overload set, or add
   `@JvmOverloads`/`@JvmName` deliberately.
8. **Do not "improve" in the same commit.** Replacing getters with properties is conversion; changing a
   loop to `map` is a refactor; changing a default is a behaviour change. Separate commits.
9. **Generics: Kotlin's declaration-site variance can confuse Java call sites.** `List<out T>` becomes
   `List<? extends T>` for Java; if Java code passes a `List<T>`, it still compiles, but a
   `MutableList` invariant break shows up as a type error. Keep the original variance until Java callers
   are gone.
10. **Verify with the Java callers compiled, not just the Kotlin module.** `:module:compileDebugJavaWithJavac`
    after conversion; a green Kotlin compile with a broken Java caller is a half-migration.

## Procedure

1. Inventory: `find . -name "*.java" | wc -l`, and identify Java callers of the class.
2. Ask the converter (IDE) for the file; do not hand-write the first pass.
3. Review the output for the seven interop rules; fix annotations, statics, `!!`, `@Throws`.
4. Compile the module including Java callers.
5. Run the class's tests; compare behaviour (same results, same exceptions).
6. Commit conversion only; move idioms to a second commit.

## Checklist

- [ ] One class per commit; public signature unchanged.
- [ ] Java-origin parameters annotated (`@Nullable`/`@NonNull`) or made nullable.
- [ ] Properties only where the accessor pair matches.
- [ ] `@JvmStatic`/`@JvmField`/`const` on members used by Java.
- [ ] No `!!` in the converted file (or each one justified).
- [ ] `@Throws` where Java callers catch.
- [ ] Overload set preserved (or `@JvmName`/`@JvmOverloads` deliberate).
- [ ] No refactor/bugfix mixed into the conversion commit.
- [ ] Variance unchanged until Java callers are gone.
- [ ] Module compiles including Java sources; tests green.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| NPE after conversion | `!!` on Java-origin value | `?:`/`requireNotNull`/nullable | platform type was nullable |
| Java compile break | top-level/companion without `@JvmStatic` | add annotation | different call syntax |
| Uncaught now-unchecked | remove `throws` silently | `@Throws` | Java callers lost the contract |
| Wrong overload | keep only the Kotlin-canonical one | keep the set | ambiguity |
| Mixed commit | convert + rewrite loop | two commits | unreviewable |
| Green Kotlin, broken Java | compile only Kotlin | compile module incl. Java | half-migrated |

## Verify

```bash
./gradlew :module:compileDebugJavaWithJavac :module:compileDebugKotlin
./gradlew :module:test
grep -rn "!!" src/main/kotlin/... | grep -v test
```

Expected: Java and Kotlin sources both compile, the class's tests pass with identical results, and the
`!!` grep is empty or justified per line.

## References

- Kotlin/Java interop: platform types, `@JvmStatic`, `@JvmField`, `@Throws`, `@JvmName`
- Kotlin declaration-site variance vs Java use-site wildcards
