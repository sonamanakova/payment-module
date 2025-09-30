# ADR-0003 — Gateway becomes an asynchronous SCA state machine

- **Status:** Accepted
- **Date:** 2025-09-30
- **Supersedes:** [ADR-0002](0002-synchronous-gateway-client.md)
- **Work item:** PAY-3
- **Author:** Senior dev
- **Reviewed by:** Medior dev

## Context

On 2025-09-26 the sandbox began requiring 3-D Secure v2 strong customer
authentication for every charge above 30 CZK. The bank confirmed on 2025-09-29
(ticket #4417) that this is not a temporary sandbox state — the previous
behaviour was a misconfiguration, and production will require SCA at go-live.

The written exemption from 2025-08-25 that ADR-0002 and the PAY-3 estimate were
built on does not survive this. Assumptions 1, 2, 3 and 4 in
[docs/scope.md](../scope.md#pay-3--payment-gateway-40h-senior_dev) are all void.

Waiting is not an option: the sandbox will not be reverted, and there is no
synchronous path left above 30 CZK.

## Decision

Rewrite `gateway` as an asynchronous state machine.

```
        authorise()
             |
             v
    +------------------+   under 30 CZK    +-----------+
    |  AUTHORISING     |------------------>| CAPTURED  |
    +------------------+                   +-----------+
             | 402 sca_required                  ^
             v                                   |
    +------------------+   webhook: authenticated|
    | PENDING_CHALLENGE|--------------------------+
    +------------------+
       |            |
       | rejected   | no event within 15 min
       v            v
    +--------+   +-----------+
    | FAILED |   | EXPIRED   |  (closed by the reconciliation job)
    +--------+   +-----------+
```

Four pieces of new surface, none of which existed in the estimate:

1. **A `Payment` entity with its own table.** `pending_challenge` can last ten
   minutes and must survive a restart, so payment state cannot live as a field
   on the order.
2. **An inbound webhook endpoint** (`POST /webhooks/bank`), publicly reachable,
   with signature verification, plus an idempotency store keyed on
   `(challenge_id, event_type)` — the sandbox delivers duplicates and delivers
   out of causal order despite what guide §7.1 says.
3. **A reconciliation job.** Abandoned challenges produce no terminal event at
   all. Without a poller, those payments never resolve.
4. **A versioned webhook parser.** The payload shape changed under us on
   2025-10-07 with no announcement (#4468); the parser now negotiates on a
   version field rather than trusting one shape.

## Consequences

- **Roughly two days of PAY-3 work is discarded** — the synchronous client, its
  tests, and the `PaymentResult` shape that `orders` and `checkout` were both
  written against.
- **PAY-3 as estimated no longer describes the work.** 40h was scoped as "wrap
  an existing HTTP client". The actual work is a persisted asynchronous state
  machine with an inbound integration surface. **This has not been re-estimated
  in Jira, and the hours have kept being logged against the original 40h.**
- **PAY-5 is affected and does not know it.** Checkout now needs a redirect to
  the bank's challenge page and a return handler. Not in its 40h either.
- **PAY-6 is blocked.** The e2e suite was written against the synchronous flow.
  Those tests are skipped, not deleted, until the interface settles.
- **This is a change of requirement, not a delivery failure.** The commercial
  conversation with the client has not happened. It should — under a fixed-price
  contract every one of these hours is the agency's.

## Alternatives considered

- **Stay under the 30 CZK exemption.** Not viable, the client sells goods priced
  in the thousands.
- **Wait for the bank to revert.** They confirmed there is nothing to revert.
- **Hand SCA to a third-party PSP.** Would remove the state machine from our
  side, but the contract names Fictional Bank as the acquirer. Would need a
  change order and a new integration — larger, not smaller.
