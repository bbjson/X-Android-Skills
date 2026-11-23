---
name: billing-and-subscriptions
description: >-
  Implement Play Billing so entitlement comes from the server and local state is only a cache:
  connection lifecycle, product/offer queries, purchase acknowledgement, consumables, pending
  purchases and real-time developer notifications. Use when adding a subscription or one-off
  purchase, when users report paying without access, when purchases disappear after reinstall, or
  when deciding what the client may trust.
license: Apache-2.0
metadata:
  domain: release
  level: advanced
  sources:
    - android-developers (Play Billing + subscriptions, re-expressed)
    - this-repo (gap analysis: monetisation absent; only Play console metadata existed)
---

# Billing and Subscriptions

One decision: **where entitlement is computed.** It is computed on your server from a verified
purchase token; the client renders what the server says and never unlocks anything by itself.

## Use when

- Adding a subscription, a one-off purchase, or a consumable (credits, coins).
- A user paid but has no access, or access vanishes after reinstall/device change.
- Purchases must be verified, acknowledged, restored, or reconciled with a backend.
- Handling pending payments, grace periods, account holds, upgrades/downgrades or offers.
- Deciding whether to use real-time developer notifications.

## Do not use when

- Play Console product/price setup and listing text → `play-metadata`.
- Track/rollout mechanics for the release that contains billing → `release-flow`.
- Data Safety declaration for purchase data → `data-safety-compliance`.
- Token and credential storage on device → `keystore-and-crypto`.

## Rules

1. **The entitlement source of truth is the server.** The client stores a cached entitlement with
   an expiry and a "last verified" timestamp; it may show a paid UI from the cache, but any
   sensitive action re-verifies with the server.
2. **Never grant from the client-side purchase object.** The purchase object is attacker-controlled
   input; send the purchase token to the server, verify it with the Play Developer API, then store
   the entitlement.
3. **Query existing purchases on every app start and on resume after a purchase flow.** Local
   persistence alone loses purchases across reinstall, device change and account switch.
4. **Acknowledge every non-consumable purchase.** An unacknowledged purchase is refunded
   automatically after a few days; acknowledgement is a server-side or explicit client step and must
   be idempotent.
5. **Consumables are consumed exactly once, after the server credits the balance.** `consumeAsync`
   before the credit means a crash loses the purchase; after the credit means a retry does not
   double-credit only if the server keys on the token.
6. **Handle `PENDING` purchases as a state, not an error.** Pending payments complete later; the UI
   must say "waiting for payment" and the entitlement appears via the server notification or the
   next query, not from the current call.
7. **Bind purchases to the user with `obfuscatedAccountId`/`obfuscatedProfileId`.** Without it,
   support cannot prove which account a token belongs to and cross-account sharing becomes a
   chargeback.
8. **Treat the connection as a state machine with reconnection.** Connect on start, reconnect with
   backoff on service disconnect, and never call `launchBillingFlow` or `queryProductDetails` before
   the client is ready.
9. **Prices and offers come from Play, never from strings or config.** Query `ProductDetails` and
   render its formatted price; a hardcoded price is a policy problem the moment pricing changes.
10. **Real-time developer notifications are the out-of-app truth.** Renewals, cancellations, grace
    periods, holds, revocations and refunds arrive by RTDN; without it, access persists until the
    next client query, which may be days.
11. **Base plans and offers are addressed by id, and the code tolerates new ones appearing.** A
    subscription id is not a single price; offers and phases change without an app update.
12. **Every failure path has a user-visible outcome**: already owned, purchase failed, network lost
    mid-flow, pending, deferred. A silent `Log.e` on `ITEM_ALREADY_OWNED` produces "I paid twice".

## Procedure

1. Define the products in Play Console (base plans/offers), then mirror the ids in a server-side
   table — the client never owns the catalogue.
2. Client: connect → `queryProductDetails` → `launchBillingFlow` → send token to server.
3. Server: verify token → store entitlement keyed by (user, product, token) → acknowledge → credit.
4. Client: re-query purchases at start/resume; reconcile with entitlement endpoint.
5. Backend: subscribe to RTDN for renewals/refunds; update entitlement.
6. Test with licence testers: purchase, cancel, refund, pending, reinstall, second device.

## Checklist

- [ ] Entitlement computed server-side; client cache has expiry and last-verified timestamp.
- [ ] Purchase token sent to server before any unlock.
- [ ] Purchases queried at start and after the flow returns.
- [ ] Acknowledgement idempotent and retried.
- [ ] Consumable credited before consumed; server dedupes by token.
- [ ] `PENDING` modelled as a state with a waiting UI.
- [ ] `obfuscatedAccountId` set on the flow.
- [ ] Connection state machine with reconnect/backoff.
- [ ] Price rendered from `ProductDetails`.
- [ ] RTDN handled for renew/cancel/grace/hold/refund.
- [ ] All failure paths have visible outcomes.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Paid, no access | unlock from purchase callback | server verify then entitlement | client object is spoofable |
| "I paid twice" | ignore `ITEM_ALREADY_OWNED` | restore + show owned state | silent failure |
| Purchase vanished | rely on local cache | query purchases at start | reinstall/device change |
| Auto-refunded purchase | never acknowledge | acknowledge idempotently | Play refunds unacknowledged |
| Lost consumable | consume before credit | credit then consume | crash between steps |
| Wrong price shown | hardcoded price string | `ProductDetails.formattedPrice` | pricing changes server-side |
| Access after refund | no RTDN | subscribe to notifications | out-of-app change |

## Verify

```bash
./gradlew :app:assembleDebug
adb -s <serial> shell pm list packages | grep -i '<pkg>'
# with a licence tester account, exercise: buy, cancel, refund, reinstall, second device
adb -s <serial> logcat -d | grep -iE 'BillingClient|BillingFlow' | tail -30
```

Expected: after each of buy/cancel/refund/reinstall the server entitlement matches Play's state,
`PENDING` shows a waiting UI rather than an error, and Logcat shows a connected client with no
unacknowledged-purchase warnings.

## References

- Play Billing Library: `BillingClient`, `queryProductDetails`, `launchBillingFlow`,
  `queryPurchasesAsync`, `acknowledgePurchase`, `consumeAsync`
- Play Developer API `purchases.subscriptionsv2`, `purchases.products`
- Real-time developer notifications (Pub/Sub)
