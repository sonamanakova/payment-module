# ADR-0002 — Gateway is a synchronous call

- **Status:** **Superseded by [ADR-0003](0003-async-sca-state-machine.md) on 2025-09-30**
- **Date:** 2025-09-19
- **Work item:** PAY-3
- **Author:** Senior dev

## Context

`POST /v1/charges` on the bank sandbox returns the final result in the same
response (verified 2025-09-18, see
[bank-api-notes](../bank-api-notes.md#2025-09-18--charge-endpoint-synchronous-as-expected)).
The bank confirmed in writing on 2025-08-25 that our merchant profile is exempt
from PSD2 strong customer authentication for v1.

## Decision

`gateway.authorise()` is a blocking call. It calls `bank_api.charge()`, maps the
response onto a `PaymentResult`, and returns. Success or failure, decided inside
one request.

No inbound endpoints. No persistence of payment state — the outcome is written
onto the order by the caller and that is the end of it. No background jobs.

## Consequences

- PAY-3 is ~40h: a domain wrapper plus tests.
- `orders` can treat payment as a function call, not a process.
- `checkout` (PAY-5) has two screens to render: paid, and not paid.
- **If SCA ever becomes mandatory, none of this survives.** The whole design
  rests on the outcome being known synchronously. Accepted as a low risk on the
  strength of the bank's written confirmation.

## Why it was superseded

The exemption did not exist. The sandbox was misconfigured and the bank fixed it
on 2025-09-26; production was always going to require SCA. The risk noted above
materialised seven days after this ADR was accepted. See ADR-0003.
