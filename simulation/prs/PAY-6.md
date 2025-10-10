---
number: 106
title: "PAY-6: Automated test suite"
branch: feature/PAY-6-test-suite
base: main
draft: false
state: open
opened: 2025-10-08
author: marek
labels: [blocked-by-PAY-3]
---

## What this is

End-to-end suite over the full payment flow, in CI.

- [x] CI wiring, fixtures, sandbox test account
- [x] Order lifecycle tests (PAY-4)
- [ ] Payment happy path — blocked
- [ ] SCA challenge flow — blocked
- [ ] Refund flow — blocked
- [ ] Webhook replay / duplicate handling — blocked

## Blocked, and one thing worth flagging

12h of 35h used. Not because the work is going well — because there is nothing
stable to test against. The remaining 23h is all still ahead of us.

The thing worth flagging: **every fixture in the old suite charged 25 CZK**,
under the bank's 30 CZK low-value exemption. When the sandbox started requiring
SCA on 2025-09-26, those tests kept passing for two days while no real payment
worked at all. Green CI, broken product.

Fixtures now use realistic amounts. That is the only reason this is worth
merging before `gateway` is finished.
