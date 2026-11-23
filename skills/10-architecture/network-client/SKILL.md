---
name: network-client
description: >-
  Configure the HTTP client layer so timeouts, retries, auth refresh and caching are single
  decisions owned by interceptors instead of being re-implemented at every call site. Use when
  adding OkHttp/Retrofit or Ktor to a project, wiring a 401 token refresh, seeing several
  refresh calls fire at once, deciding between an HTTP cache and an app-level cache, or
  debugging timeouts, retry storms and slow uploads.
license: Apache-2.0
metadata:
  domain: architecture
  level: advanced
  sources:
    - android-developers (network access + OkHttp guides, re-expressed)
    - this-repo (gap analysis: no client-layer skill in round 1)
---

# Network Client

One decision: **which policy the client enforces, and where that policy lives.** All of it lives
in the client instance and its interceptors — never in a repository call, never in a ViewModel.

## Use when

- Adding or changing the HTTP client (`OkHttpClient`, `Retrofit`, Ktor engine) or its config.
- Implementing authentication refresh, retry, backoff, or request logging.
- A user reports "the app times out on mobile data" or "it silently retries forever".
- Editing `core/network/`, `di/NetworkModule.kt`, or any interceptor.
- Deciding where an ETag / `Cache-Control` / pagination token is handled.

## Do not use when

- Deciding DTO field types, nullability, unknown fields or error envelopes → `network-dto-safety`.
- Deciding cache freshness policy and the local store of record → `data-layer`.
- Paging state, page keys and end-of-list detection → `paging`.
- Certificate pinning, cleartext policy, integrity attestation → `app-hardening`.

## Rules

1. **One client instance per base URL, created once.** A client built per call throws away the
   connection pool, the dispatcher and the cache — the three things that make the network fast.
2. **Base URL and every secret come from the build variant, never a literal.** Read it from a
   `BuildConfig` field or a resource resolved per flavor; see `build-variants`.
3. **Auth lives in an interceptor and re-issues the request at most once.** A second 401 after a
   fresh token is a `Failure.Auth`, not another refresh.
4. **Concurrent 401s trigger exactly one refresh.** Guard the refresh with a `Mutex`; other calls
   suspend, then re-issue with the new token. Without the guard, N in-flight calls set off N
   refreshes and many backends invalidate the refresh token on first use — logging the user out.
5. **Retry only transient failures of idempotent requests.** Allowed: connection errors, timeouts,
   `5xx`, `429`. Forbidden: any `4xx` other than `429`, and any non-idempotent write unless the
   request carries an idempotency key. Bound the attempts and jitter the backoff.
6. **Honour `Retry-After` when the server sends it**, and cap the wait so a hostile header cannot
   park a request for minutes.
7. **Set all four timeouts explicitly** — connect, read, write, and a call timeout that bounds the
   whole attempt including redirects. A default read timeout turns a dead endpoint into a hang.
8. **A `2xx` is not success.** Parse the error envelope before mapping; a `200` carrying
   `{"code": 401}` must become `Failure`, or the UI shows an empty screen.
9. **Cancellation is propagated, not swallowed.** Suspend calls cancel the underlying call; if you
   wrap them, `CancellationException` must be rethrown — `runCatching { }.getOrNull()` is a bug
   (see `structured-concurrency`).
10. **JSON config is central and strict:** unknown keys ignored, unknown enums mapped to an
    explicit `UNKNOWN` member, no primitive defaults that hide a missing field.
11. **Interceptor order is a decision:** auth → retry/backoff → logging. Logging last means it
    records the attempt that actually left, including retries.
12. **Release logging never writes bodies, headers or tokens.** A log interceptor is conditional on
    the debuggable flag and emits method, URL host/path, status and duration only.
13. **Use the HTTP cache for GETs and let the server own freshness.** If the server sends no cache
    headers, fix that or build a local store in `data-layer` — do not invent an invisible
    in-memory map in the client.
14. **Uploads stream from a file/`RequestBody`, downloads write to a file.** Buffering a video into
    a `ByteArray` is an OOM with a progress bar.
15. **Streaming transport gets its own policy.** SSE and WebSocket frames must not pass through the
    retry interceptor — replaying a stream duplicates messages; the stream owns its reconnect with
    resume state, and its read timeout is not the request timeout.

## Procedure

1. Define the client in DI (`NetworkModule`) with timeouts and one cache directory.
2. Add interceptors in the order from rule 11; keep each one single-purpose and testable.
3. Implement refresh behind a `Mutex`; add a test that fires N requests against a MockWebServer
   returning `401` and asserts exactly one refresh.
4. Configure the JSON converter once (rule 10) and share it with the test code.
5. Map transport and HTTP errors into the repository's failure type (`data-layer`).

## Checklist

- [ ] One client instance, created in DI, not per call.
- [ ] Base URL and secrets from variant config; no literal host or key in code.
- [ ] Refresh guarded by a mutex; request re-issued at most once.
- [ ] Retry restricted to idempotent + transient, with bounded jittered backoff.
- [ ] connect/read/write/call timeouts all set.
- [ ] Error envelope parsed for `2xx` responses.
- [ ] Log interceptor disabled in release and strips bodies/tokens.
- [ ] MockWebServer test covers: 401 refresh, 500 → retry, 429 `Retry-After`, timeout, malformed body.
- [ ] Uploads/downloads stream; no whole-file byte arrays.
- [ ] SSE/WebSocket bypasses the request-retry interceptor and owns its reconnect.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Logged out at random | refresh per call site | mutex-guarded single refresh | N refreshes invalidate the token |
| Infinite retry | `retry()` on everything | idempotent + transient + bounded | outage amplified into a self-DDoS |
| Hang with no error | default timeouts only | all four set explicitly | read timeout unbounded |
| Blank screen with 200 | treat `2xx` as success | parse envelope → `Failure` | server-side error becomes empty UI |
| Slow list, high battery | client per request | one shared client | no pooling, no cache |
| Token in Logcat | logging body in release | host/path/status only | credential leak in bug reports |
| Half-uploaded file | `body.bytes()` | streaming `RequestBody` | OOM on large media |

## Verify

```bash
./gradlew :core:network:testDebugUnitTest
# the refresh test must assert exactly one refresh for N concurrent 401s
adb -s <serial> shell cmd connectivity airplane-mode enable
adb -s <serial> logcat -d -s OkHttp:* | grep -c '<token>'   # expected: 0
```

Expected: network tests green including the single-refresh assertion; offline runs produce a
`Failure.Network` (not a crash, not an empty success) and no credential appears in Logcat.

## References

- OkHttp `Interceptor`, `Dispatcher`, `Cache`, `retryOnConnectionFailure` semantics
- Retrofit `suspend` call cancellation; Ktor `HttpClient` plugin ordering
- `MockWebServer` for interceptor tests
