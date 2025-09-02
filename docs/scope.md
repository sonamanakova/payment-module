# Scope and estimates

Agreed with the client on 2025-08-27, before kick-off. Estimates are in hours of
the named role. Fixed price — these numbers are the commercial commitment, not a
forecast.

---

## PAY-1 — Payment module skeleton (30h, medior_dev)

Package layout, configuration, a health endpoint, CI. No business logic.

Assumptions: none of consequence.

Status: **Done**, merged 2025-09-10. 28h actual.

---

## PAY-2 — Bank API integration (60h, senior_dev)

HTTP client for the Fictional Bank sandbox: authentication, request signing,
error mapping, retries. Transport only — no payment lifecycle.

Assumptions:
- The bank's sandbox mirrors production. (Confirmed in writing by the bank on
  2025-08-25.)
- OAuth2 client credentials, token refresh, HMAC request signing. All documented
  in the bank's API guide v1.4.

Status: **Done**, merged 2025-09-17. 68h actual, 8h over. The overrun
was request signing — the bank's guide documents the canonical string format
incorrectly. Absorbed, not escalated.

---

## PAY-3 — Payment gateway (40h, senior_dev)

The payment lifecycle on top of `bank_api`: authorise, capture, refund, and the
`Payment` state model. What `orders` calls when a customer pays.

**Assumptions the 40h was built on:**

1. **The charge endpoint is synchronous.** Request in, final result out, one
   HTTP round trip. `bank_api` already handles the transport, so PAY-3 is a
   thin domain wrapper over an existing client.
2. **No 3-D Secure / SCA handling in v1.** The bank confirmed on 2025-08-25
   that the sandbox merchant profile is exempt from PSD2 strong customer
   authentication, and that SCA would be "a phase two conversation".
3. **No webhooks, no callbacks, no inbound endpoints.** Nothing the bank sends
   us unprompted. The module is outbound-only.
4. **No persistence beyond the order record.** A payment is a field on an
   order, not an entity with a lifecycle of its own.
5. **Refunds are a single call.** Full refunds only; partial refunds are out of
   scope.

40h = roughly 3 days of a senior developer wiring an already-built HTTP client
into the order flow, plus tests.

Status: **In Progress.** See [docs/bank-api-notes.md](bank-api-notes.md) and
[ADR-0003](adr/0003-async-sca-state-machine.md) — assumptions 1, 2, 3 and 4 all
turned out to be false. Not re-estimated.

---

## PAY-4 — Order backend (50h, medior_dev)

Order model, order state machine, REST endpoints, persistence.

Assumptions: talks to `gateway` through an interface, so it can be built and
merged before `gateway` is finished. Held.

Status: **Done**, merged 2025-10-01. 50h actual, on the nose.

---

## PAY-5 — Checkout frontend (40h, junior_dev)

Checkout page, payment form, result screens.

Assumptions: two outcomes to render — success and failure. (This is assumption 1
of PAY-3 restated on the frontend; it does not hold either. A challenge redirect
screen is now needed and is not in the estimate.)

Status: **In Progress**, pull request open since 2025-10-08. 30h actual.

---

## PAY-6 — Automated test suite (35h, qa)

End-to-end test suite over the full payment flow, run in CI.

Assumptions: there is a payment flow to test against by week 5.

Status: **In Progress**, pull request open since 2025-10-08. 12h actual — the suite
cannot be finished while `gateway` has no stable interface. The remaining 23h is
still ahead of us, not saved.

---

## PAY-7 — Project coordination (40h, pm)

Standups, client calls, reporting. No pull request; this is not delivery work.

Status: **In Progress.** 42h actual.
