---
number: 105
title: "PAY-5: Checkout frontend"
branch: feature/PAY-5-checkout-frontend
base: main
draft: false
state: open
opened: 2025-10-08
author: jana
labels: [blocked-by-PAY-3]
---

## What this is

Checkout page, payment form, result screens.

- [x] Checkout page + cart summary
- [x] Payment form
- [x] Success screen
- [x] Failure screen
- [ ] **Challenge redirect screen** — not in the estimate, see below
- [ ] **Return handler** — same

## Blocked

The estimate assumed two outcomes to render: paid, and not paid. Since ADR-0003
there is a third — "we sent the customer to the bank and do not know yet" — and
it needs a redirect out to the bank's challenge page plus a handler for the
customer coming back, which may be before or after the webhook lands.

I cannot finish the last two boxes until `gateway` settles. 30h of 40h used, and
the remaining work is now bigger than the 10h left.

Opening this anyway so the parts that are done can be reviewed. Can the senior dev
confirm what the return URL contract ends up being?
