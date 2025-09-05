# ADR-0001 — Separate transport from payment lifecycle

- **Status:** Accepted
- **Date:** 2025-09-05
- **Work item:** PAY-1 / PAY-2
- **Author:** Senior dev

## Context

The client has one bank today and has said they may add a card acquirer later.
We need to decide how tightly the payment code is bound to Fictional Bank.

## Decision

Two layers.

- `src/payments/bank_api/` — transport. Speaks HTTP to Fictional Bank: auth,
  signing, retries, error mapping. Knows nothing about orders or payments.
  This is PAY-2.
- `src/payments/gateway/` — domain. Owns the payment lifecycle and exposes a
  provider-agnostic interface to `orders`. This is PAY-3.

`orders` depends on `gateway` through an interface, never on `bank_api`.

## Consequences

- PAY-4 (order backend) can be built and merged against the interface without
  waiting for PAY-3. This held — PAY-4 merged on time.
- PAY-3 was estimated as a thin layer, because at the time of this ADR the
  transport was believed to carry all the complexity. See ADR-0003 for how that
  turned out.
