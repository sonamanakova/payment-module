---
number: 102
title: "PAY-2: Bank API integration"
branch: feature/PAY-2-bank-api
base: main
draft: false
state: merged
opened: 2025-09-10
merged: 2025-09-17
author: tomas
labels: []
---

## What this is

The HTTP client for the Fictional Bank sandbox. Transport only — no payment
lifecycle, that is PAY-3 (ADR-0001).

- [x] OAuth2 client credentials + token refresh
- [x] HMAC request signing
- [x] Retry with backoff on 429 / 5xx
- [x] Error mapping
- [x] `charge()`, `get_charge()`, `refund()`

## The overrun

68h against 60h. All eight hours went into request signing: the bank's API
guide v1.4 §4.2 documents the canonical string as `METHOD \n PATH \n BODY`, and
the sandbox actually wants the timestamp between path and body, with the `/v1`
prefix stripped. Found by brute-forcing combinations against a signature-echo
endpoint.

Raised as ticket #4381. No reply.

There is a comment in `_sign()` saying not to "fix" it back to match the guide.
Please leave it.

## Verified against the sandbox

`POST /v1/charges` returns 200 with `status: "captured"` in the same response,
~400ms round trip. Synchronous, as the estimate assumed. PAY-3 can be a thin
wrapper over this.
