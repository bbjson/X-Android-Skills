---
name: network-dto-safety
description: >-
  Make a JSON API contract fail loudly and locally instead of silently poisoning the UI: nullability,
  missing and unknown fields, type drift, unknown enum values, money and time precision, error
  bodies, and R8 rules that keep serialization working. Use when defining or changing a DTO,
  handling an API error, adding a serializer, seeing "field is null but should not be", or when a
  release build crashes in deserialization but debug does not.
license: Apache-2.0
metadata:
  domain: security
  level: advanced
  sources:
    - mobile-agent-skillpack (android-api-dto-safety)
    - agent-skills-standard (android-networking)
    - awesome-android-agent-skills (android-retrofit)
    - kotlin-footguns (remote-api-footguns)
---

# Network DTO Safety

A DTO is a **decoder for untrusted input**, not a description of the server. Assume every field can
be absent, null, a different type, or a string where you expect a number.

## Use when

- Adding or changing a `@Serializable`/`@SerialName` DTO.
- Parsing an error response body.
- Adding an enum that comes from the server.
- Debug-only crash at deserialization, or a null field in release.
- Handling money, dates, ids, or pagination from an API.

## Do not use when

- The mapping layer/ownership question → `data-layer`.
- The trust boundary is a component/Intent/WebView → `component-exposure`.
- The failure has no reproduction yet → `bug-fix`.
- Transport policy around the DTO (timeouts, retries, 401 refresh) → `network-client`.

## Rules

1. **DTO and domain model are separate types, and the mapper declares every field.** No `@Serializable`
   class used as a UI or domain type. (See `layering` rule 3 — this skill adds *how* the decoder
   behaves.)
2. **Only genuinely-optional fields are nullable.** A field the server always sends is
   non-nullable, and a missing value must throw at decode time (fail fast, at the boundary) rather
   than become `null` deep in the UI. Decide per field, and record the decision in the mapper.
3. **Give every collection a safe default, never `null`.** `val items: List<Item> = emptyList()`
   — servers routinely send `null`, omit the key, or send `{}` instead of `[]`.
4. **Enable `ignoreUnknownKeys = true`.** Server adds a field; the app must not crash. Unknown keys
   are not errors.
5. **Do not enable `coerceInputValues` to paper over type drift.** It silently converts wrong types
   to defaults. A `null` in a non-null field should be visible in logs and tests, not coerced.
6. **Enums from the server need a fallback branch.** Either deserialize as `String` and map in one
   `when` with `else -> Unknown(raw)`, or use a custom serializer. A new server enum value must not
   throw in a shipped app.
7. **Money is integer minor units (or a decimal type), never `Double`.** `0.1 + 0.2` is not `0.3`;
   currency amounts in `Double` are a rounding defect waiting for finance.
8. **Ids are `String` unless the server guarantees a range.** An `Int` id overflows on a growing
   table; a `Long` id overflows into JSON precision in JS-based backends.
9. **Time is an ISO-8601 instant + explicit timezone, parsed with a fixed formatter**, not a locale
   default. Never parse with `SimpleDateFormat` and default locale; never store a local time without
   a zone.
10. **Pagination is part of the contract.** `nextCursor`/`hasMore`/`total` are nullable-by-design;
    a page without `hasMore` is a client-side assumption and will loop forever on the last page.
11. **Error bodies are a separate schema and must be parsed defensively.** `suspend fun x(): Response<Body>`
    and read `errorBody()` with its own DTO, or use a sealed result. Returning a success-typed DTO
    for an error response is how "Unknown error" reaches users.
12. **R8 must keep serialization metadata.** Kotlin serialization needs `@Serializable` classes not
    stripped, and Retrofit/Gson need their annotations kept. Verify with a **release** build, not
    debug — this is the classic debug-passes/release-crashes split.

## Procedure

1. Write the DTO with rule-1 separation; annotate `@SerialName` explicitly so a Kotlin rename is not
   a wire change.
2. Mark nullability per field with the server contract; default collections (rule 3).
3. Configure the `Json` instance once: `ignoreUnknownKeys = true`, explicit `isLenient = false`.
4. Map DTO → domain in one place; every field handled, unknown-enum fallback included (rule 6).
5. Model failures: `ApiResult<T>` with `Http(code, errorBody)`, `Io`, `Parse`; parse error bodies
   with their own DTO (rule 11).
6. Add R8 keep rules for the serialization library and for DTOs if not already covered.
7. Test with hostile fixtures: missing fields, `null` collection, unknown enum, extra fields,
   wrong types, huge payload, empty body, HTML error page.
8. Run `assembleRelease` and exercise decoding once on a device.

## Checklist

- [ ] DTO separate from domain; mapper covers every field.
- [ ] `@SerialName` explicit where the Kotlin name could change.
- [ ] Non-null fields are genuinely guaranteed; collections default to `emptyList()`.
- [ ] `ignoreUnknownKeys = true`; `coerceInputValues` not used to hide drift.
- [ ] Server enums have an `Unknown` fallback path.
- [ ] Money not `Double`; ids `String` unless range-guaranteed.
- [ ] Times parsed as instants with explicit zone.
- [ ] Pagination has an explicit termination flag.
- [ ] Error body parsed with its own type; `ApiResult` distinguishes parse/io/http.
- [ ] Hostile-fixture tests exist.
- [ ] Release build verified (R8 keeps serialization working).

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Crash on new field | no `ignoreUnknownKeys` | enable it | additive server changes |
| "null everywhere" | all fields nullable "to be safe" | contract-driven nullability | nullability is information |
| Silent zero amounts | `coerceInputValues` | fail/log at the boundary | hides a real contract break |
| Enum crash in prod | `enum class Status` direct | `Unknown(raw)` fallback | server adds values |
| 0.01 missing | `Double` price | integer minor units | float rounding |
| Time off by hours | `SimpleDateFormat` default locale | explicit ISO formatter + zone | locale/TZ dependent |
| Infinite scroll | `while (items.size > 0)` | `while (hasMore)` | last page repeats |
| Debug ok, release crash | test only `assembleDebug` | `assembleRelease` + R8 rules | serialization stripped |

## Verify

```bash
./gradlew :core:network:test          # hostile fixtures must all decode or fail predictably
./gradlew :app:assembleRelease
adb -s <serial> install -r app/build/outputs/apk/release/app-release.apk   # exercise one API path
```

Expected: every hostile fixture either decodes to a sensible default or produces a modelled
`ApiResult.Parse` — never an uncaught exception; and the release build decodes real responses.

## References

- `kotlinx.serialization` `Json { ignoreUnknownKeys, coerceInputValues }` semantics
- Retrofit `Response.errorBody()`, `CallAdapter` for sealed results
