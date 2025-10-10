---
number: 104
title: "PAY-4: Order backend"
branch: feature/PAY-4-order-backend
base: main
draft: false
state: merged
opened: 2025-09-24
merged: 2025-10-01
author: petra
labels: []
---

## What this is

Order model, order state machine, REST endpoints, persistence.

- [x] `Order` + `OrderStatus` with explicit transitions
- [x] `POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/pay`
- [x] Persistence

## Notes

50h against 50h.

Merged against the `gateway` interface rather than the implementation, per
ADR-0001, so this did not have to wait for PAY-3. That decision paid for itself.

One change on the way in: `Order.payment_id` is now a reference to a payment
entity rather than a `paid: bool`, following ADR-0003. Cheap here because the
coupling was already through an interface.

`POST /orders/{id}/pay` currently returns a `challenge_url` that nothing in
checkout knows how to use yet — flagged on PAY-5.
