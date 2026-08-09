---
number: 103
title: "PAY-3: Payment gateway"
branch: feature/PAY-3-payment-gateway
base: main
draft: true
state: open
opened: 2025-09-24
author: tomas
labels: [blocked, needs-decision, scope-changed]
---

## What this is

The payment lifecycle on top of `bank_api` — authorise, capture, refund — and
the `Payment` model that `orders` calls. ADR-0001 layer two.

Opened as draft on 2025-09-24 because refunds weren't in yet. Still a draft on
2025-10-09, different reason now, see below.

## 2025-09-24

Thin wrapper over the client PAY-2 already built. Happy path worked end to end
against the sandbox on day one:

- [x] `PaymentGateway.authorise()`
- [x] `PaymentResult` mapping
- [ ] `refund()`
- [ ] tests
- [ ] docs

Figured this would be out of draft by 2025-09-26.

## 2025-09-26 to 2025-09-29

Sandbox started answering `402 sca_required` for every charge above 30 CZK on
the 26th. Bank confirmed on the 29th (#4417) that it's permanent — the written
SCA exemption from August was apparently a sandbox misconfig on their end, and
production will require SCA at go-live too.

So ADR-0002's design doesn't hold. A charge isn't request-in-result-out
anymore — it's a challenge, the customer goes to the bank, and we find out the
outcome later on a webhook we don't have.

[ADR-0003](../../docs/adr/0003-async-sca-state-machine.md) has the full
writeup. Four things needed that weren't in the 40h estimate:

1. A persisted `Payment` entity with a real lifecycle (`pending_challenge` lasts
   up to 15 minutes and survives restarts).
2. An inbound webhook endpoint with signature verification and an idempotency
   store — **this project had no inbound endpoints at all before now**.
3. A reconciliation job, because an abandoned challenge produces no terminal
   event and the payment would otherwise hang forever.
4. A version-negotiating payload parser, after the bank renamed three webhook
   fields overnight on 2025-10-07 with no announcement (#4468).

## Rework

Two rewrites so far:

| When | What was thrown away | Why |
|---|---|---|
| 2025-09-30 | Synchronous gateway + its tests + the `PaymentResult` shape `orders` and `checkout` were written against | ADR-0002 superseded |
| 2025-10-07 | Webhook parser | Sandbox v2.1 renamed `challenge_result` → `authentication.status`, `charge_id` → `payment.id` (#4468) |

## Where it stands, 2025-10-09

Working:
- [x] `authorise()` up to the challenge, challenge redirect URL returned
- [x] Webhook receipt, signature verification, idempotency store
- [x] State machine tolerant of duplicate and out-of-order events
- [x] v2.0 / v2.1 payload negotiation

Not working:
- [ ] **Refunds** — the bank needs the original authentication reference and we
      never stored it. Needs a schema change plus a backfill.
- [ ] **Persistence** — the repository is in-memory. A deploy loses every
      in-flight payment. Not shippable as is.
- [ ] **Reconciliation job** — not started. Needs a scheduler; this project has
      no background worker of any kind.
- [ ] **Partial capture** — never in scope, but `orders` now assumes it exists.
- [ ] **Tests** — the e2e suite is skipped. It asserts on a function signature
      that no longer exists.

## Why still draft, not review

Nothing here merges cleanly right now — without persistence it loses payments,
without reconciliation it strands them. Kept working instead of opening for
review because the requirements underneath it kept moving. In hindsight should
have opened this for review earlier. Three weeks of hours in against a 40h
estimate, nothing merged.

## What I need

1. **A decision on scope.** The estimate describes a job that no longer exists.
   Minimum mergeable gateway is my guess at 20–25h — persistence, refunds, and
   the reconciliation job — but nobody has broken it out properly.
2. **Whether the SCA work is a change order.** The exemption was confirmed by
   the client's bank in writing before we estimated. Fixed price means every one
   of these hours is ours unless somebody has that conversation.
3. **A heads-up to PAY-5 and PAY-6.** Checkout needs a redirect screen it does
   not have in its estimate; the test suite is blocked on this interface
   settling.

/cc medior dev, PM
