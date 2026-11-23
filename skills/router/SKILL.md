---
name: router
description: >-
  Route an Android task to the correct domain skill before doing any work, and refuse to start when
  the task is under-specified. Use at the start of any Android, Kotlin, Jetpack Compose, Gradle,
  Play release, or device-automation request when you are unsure which skill applies, when several
  could apply, or when the request is a symptom ("it's slow", "it crashes") rather than a task.
  Use when starting any such request and the owning skill is not obvious.
license: Apache-2.0
metadata:
  domain: meta
  level: core
  sources:
    - chrisbanes/skills (using-chrisbanes-skills)
    - android-skill (official-android-skills)
    - agent-skills-standard (metadata)
---

# Router

Do not start work from a symptom. Name the artefact that must change, then load the one skill that
owns it. Loading two domain skills for one change usually means the change should be split.

## Use when

- The request is vague ("make it faster", "it's broken", "add a screen").
- Two or more skills might apply and you must pick one.
- The request spans domains (e.g. "add a screen and release it") — split it first.

## Do not use when

- The owning skill is already obvious — load it directly. The router is a fallback, not a ritual.

## Routing table

**Workflow — deciding what to build**

| Request shape | Load | Not |
|---|---|---|
| vague/single-sentence feature request, unstated assumptions | `requirements-grill` | `feature-to-spec` |
| requirements decided, need state machine + error matrix | `feature-to-spec` | `implementation-plan` |
| spec exists, need ordered verifiable tasks | `implementation-plan` | `code-review` |
| review a diff/PR, or a thread stuck on style | `code-review` | `bug-fix` |
| crash / ANR / wrong value / build error | `bug-fix` | `code-review` |
| restructure without behaviour change | `refactor` | `code-review` |
| finished work → pull request, merge strategy | `deliver-pr` | `code-review` |

**Architecture**

| Request shape | Load | Not |
|---|---|---|
| "where does this class go?" / layer violation | `layering` | `modularization` |
| "should we split into modules?" / build time | `modularization` | `layering` |
| repository / Room / DataStore / offline / Flow emission | `data-layer` | `layering` |
| screen state design, MVVM vs MVI, SavedStateHandle | `state-holders` | `compose-state-effects` |
| DI wiring, scope, MissingBinding, Hilt↔Koin | `dependency-injection` | `layering` |
| start a new feature end to end | `feature-scaffold` | `layering` |
| HTTP client config, 401 refresh, retry, timeouts | `network-client` | `network-dto-safety` |
| entity/DAO change, Migration, slow query, index | `room-persistence` | `data-layer` |
| paged list, PagingSource, RemoteMediator, duplicate pages | `paging` | `lazy-layouts` |
| scope ownership, cancellation, StateFlow vs Channel, async | `structured-concurrency` | `compose-state-effects` |

**Compose**

| Request shape | Load | Not |
|---|---|---|
| write/refactor a Composable's structure, params, preview | `compose-core` | `compose-component-api` |
| design a reusable component's API (slots vs booleans) | `compose-component-api` | `design-system` |
| theme tokens, hardcoded colour/dp, dark mode | `design-system` | `compose-component-api` |
| state ownership, effects, rotation loss | `compose-state-effects` | `state-holders` |
| add screen, args, deep link, back behaviour | `compose-navigation` | `compose-state-effects` |
| transitions, enter/exit, gesture animation | `compose-animation` | `recomposition` |
| TalkBack, roles, touch targets, focus order | `compose-accessibility` | `rtl-localization` |
| RTL, translation overflow, plurals, bidi | `rtl-localization` | `design-system` |
| tablet/foldable/split-window layout, two-pane, size class | `adaptive-layout` | `tv-and-focus` |
| chart, ring, custom drawing, jank while animating | `compose-graphics` | `modifier-and-layout` |

**Performance**

| Request shape | Load | Not |
|---|---|---|
| "slow", "janky", "recomposes too much" | `recomposition` | `baseline-profiles` |
| Modifier order, custom layout, double measure | `modifier-and-layout` | `recomposition` |
| list jank, lost item state, paging re-fetch | `lazy-layouts` | `recomposition` |
| cold start, first frame, Perfetto | `startup-and-perfetto` | `baseline-profiles` |
| first-scroll jank after install, startup AOT | `baseline-profiles` | `startup-and-perfetto` |
| release-only crash, shrinking, mapping | `r8-for-compose` | `release-flow` |
| APK/AAB too large, split/download size, asset delivery | `app-size` | `r8-for-compose` |

**Build / Quality / Security / Release / Device / Migration**

| Request shape | Load | Not |
|---|---|---|
| dependency versions, catalog, BOM | `version-catalog` | `agp9-migration` |
| AGP 8→9, removed variant API | `agp9-migration` | `version-catalog` |
| duplicated build config, build-logic, plugin ids | `gradle-conventions` | `version-catalog` |
| JDK toolchain, jvmTarget, Kotlin/Compose compiler version | `kotlin-toolchain` | `agp9-migration` |
| annotation processor, generated code missing, kapt→KSP | `ksp-processing` | `kotlin-toolchain` |
| build takes minutes, config cache problems | `build-performance` | `ci-pipeline` |
| CI workflow, caching, managed devices, release job | `ci-pipeline` | `release-flow` |
| JVM test for VM/repo/mapper, flaky test | `unit-testing` | `compose-ui-testing` |
| Compose interaction test, tag strategy, restoration | `compose-ui-testing` | `unit-testing` |
| screenshot / visual regression | `screenshot-testing` | `compose-ui-testing` |
| E2E flow across app/OS boundaries | `e2e-device-testing` | `compose-ui-testing` |
| lint/detekt/ktlint noise, baselines, CI gate | `static-analysis` | `code-review` |
| prove a perf claim, benchmark gate | `benchmark-testing` | `startup-and-perfetto` |
| token storage, crypto, secret leak | `keystore-and-crypto` | `component-exposure` |
| exported component, PendingIntent, WebView, deep link | `component-exposure` | `network-dto-safety` |
| DTO nullability, unknown enum, error body | `network-dto-safety` | `data-layer` |
| ship to Play, tracks, staged rollout | `release-flow` | `r8-for-compose` |
| keystore, upload key, Play App Signing, rotation | `signing-and-play-signing` | `release-flow` |
| listing text/images, locales, changelogs | `play-metadata` | `data-safety-compliance` |
| Data Safety form, privacy policy, sensitive permissions | `data-safety-compliance` | `keystore-and-crypto` |
| crash/ANR rate, frozen frames, halt or hotfix | `vitals-and-reports` | `bug-fix` |
| automate a device flow, reproduce on hardware | `adb-automation` | `compose-ui-testing` |
| convert XML layout to Compose, View/Compose interop | `xml-to-compose` | `compose-navigation` |
| MASVS-style audit of your own app | `masvs-audit` | `component-exposure` |
| AVD will not boot, clean state, parallel emulators | `emulator-management` | `adb-automation` |
| environments/flavors, BuildConfig, variant source sets | `build-variants` | `gradle-conventions` |
| Espresso/Fragment test, flaky instrumented test, system dialog | `view-ui-testing` | `compose-ui-testing` |
| anti-tamper, integrity verdict, root/debug detection, secret placement | `app-hardening` | `masvs-audit` |
| crash SDK, mapping upload, unreadable stack, ANR capture | `crash-reporting` | `vitals-and-reports` |
| subscription/one-off purchase, entitlement, acknowledgement | `billing-and-subscriptions` | `play-metadata` |
| analytics event, funnel, consent gate, exposure event | `analytics-instrumentation` | `crash-reporting` |
| feature flag, kill switch, remote value, experiment rollout | `remote-config` | `release-flow` |
| targetSdk bump, edge-to-edge breakage, predictive back, Play deadline | `targetsdk-bump` | `adaptive-layout` |

**Platform and specialized**

| Request shape | Load | Not |
|---|---|---|
| KMP source sets, expect/actual, shared UI decision | `kmp` | `cocoapods-to-spm` |
| CocoaPods → SPM for a KMP iOS target | `cocoapods-to-spm` | `kmp` |
| Wear OS module, tiles, ambient mode, data layer | `wear-os` | `compose-core` |
| Android TV, D-pad focus, Back on TV | `tv-and-focus` | `compose-accessibility` |
| camera capture, preview, lens switch | `camera` | `media3` |
| audio/video playback, background session, focus | `media3` | `notifications-fcm` |
| push, channels, FCM token, tap intent | `notifications-fcm` | `deep-links` |
| App Links, custom scheme, assetlinks verification | `deep-links` | `component-exposure` |
| RxJava → coroutines/Flow | `rxjava-to-coroutines` | `unit-testing` |
| Java class/module → Kotlin, Java callers | `java-to-kotlin` | `refactor` |
| NavHost/NavController → Nav3 back stack | `nav2-to-nav3` | `compose-navigation` |
| Hilt → Koin, scope mapping, graph verify | `hilt-to-koin` | `dependency-injection` |
| legal APK analysis of your own build | `reverse-engineering` | `masvs-audit` |
| Kotlin/Compose traps scan of a diff | `kotlin-footguns` | `code-review` |
| Android kernel module (KO/LKM), vermagic, GKI | `kernel-lkm` | `mainline-port` |
| port mainline Linux to an Android device | `mainline-port` | `kernel-lkm` |
| sync/upload job, worker never runs, foreground service type | `background-work` | `structured-concurrency` |
| permission request, denial path, photo/file picker, URI grant | `permissions-and-pickers` | `app-hardening` |
| image display, rotated photo, OOM in an image list, cache key | `image-loading` | `app-size` |
| home-screen widget, Glance, stale widget, widget tap | `app-widgets` | `background-work` |
| native library, JNI crash, ABI, tombstone, symbolication | `ndk-jni` | `crash-reporting` |
| android:process, AIDL, bound service, TransactionTooLarge | `ipc-and-multiprocess` | `background-work` |

Names marked `(roadmap)` are planned, not present. If a `## Do not use when` section of another skill
points at a `(roadmap)` neighbour, treat it as "a different domain owns this" and stop — do not
stretch the current skill to cover it.

## Rules

1. **One skill per change.** If two skills genuinely apply, split the change into two commits and
   route each separately.
2. **Symptom ≠ task.** Convert to an artefact first: "it's slow" → which screen, which interaction,
   measured how? If the user cannot answer, ask exactly one clarifying question.
3. **Order matters for symptoms:** measure → diagnose → fix; never route a perf complaint straight
   to a fix skill.
4. **Respect the do-not-use lists.** Every skill names its neighbours; those lists are the routing
   contract and override your intuition about the topic.
5. **Versions never come from a skill.** Any version mentioned in a skill is a catalog key or a URL;
   the project's `gradle/libs.versions.toml` wins.
6. **Missing coverage is an answer too.** If no skill covers the task, say so and use the platform
   docs — do not stretch a neighbour. A neighbour labelled `(roadmap)` does not exist yet.
7. **Spec before code, code before release.** A request that skips a step (build it *and* ship it)
   is two or three routes, in that order.

## Checklist

- [ ] Exactly one domain skill chosen and named out loud.
- [ ] The task is an artefact ("edit X in file Y"), not a symptom.
- [ ] No version literal taken from skill prose.
- [ ] Multi-domain request split into ordered commits.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Vague request | guess and start editing | ask one clarifying question | wrong artefact changed |
| Two skills loaded | read both, mix rules | split the change | contradictory checklists |
| Perf complaint | jump to `recomposition` | measure first | optimise the wrong thing |
| No matching skill | force-fit the nearest | state the gap, use docs | fabricated rules |
| Ship request | start with `release-flow` | spec → implement → release | releasing nothing |

## Verify

State in one line: `<skill-name> — because <artefact>`. If that line cannot be written, the routing
is not done.

Expected: one skill name plus the artefact that made it the right choice; if that line cannot be written, routing is not done.

