# Payment module — Fictional Bank a.s.

Payment module for Fictional Bank's e-shop platform, project key `PAY`.
Kick-off 2025-09-01, planned delivery 2025-10-24 (week 8).

This repository is the delivery side of the project: what actually shipped, and
when. Estimates, worklogs, rates and commercial terms live in Jira and in the
contract — this repo is the record of merged work.

## Scope

Seven work items, estimated up front — see [docs/scope.md](docs/scope.md) for
the full breakdown and the assumptions each estimate was built on.

| Key | Summary | Role | Estimate |
|---|---|---|---|
| PAY-1 | Payment module skeleton | medior_dev | 30h |
| PAY-2 | Bank API integration | senior_dev | 60h |
| PAY-3 | Payment gateway | senior_dev | 40h |
| PAY-4 | Order backend | medior_dev | 50h |
| PAY-5 | Checkout frontend | junior_dev | 40h |
| PAY-6 | Automated test suite | qa | 35h |
| PAY-7 | Project coordination | pm | 40h |

PAY-7 is coordination work and produces no pull request.

## Architecture

```
checkout (PAY-5)
      |
      v
orders (PAY-4)  ---->  gateway (PAY-3)  ---->  bank_api (PAY-2)  ---->  Fictional Bank sandbox
                            |
                            +--> webhooks (PAY-3, added week 5 — see ADR-0003)
```

`bank_api` is the transport layer: it speaks HTTP to the bank and knows nothing
about our domain. `gateway` is the domain layer: it owns the payment lifecycle
(authorise, capture, refund) and is what `orders` calls. Everything downstream
of `gateway` is blocked until it lands.

## Documentation

- [docs/scope.md](docs/scope.md) — scope, estimates and the assumptions behind them
- [docs/bank-api-notes.md](docs/bank-api-notes.md) — running log of what the bank's sandbox actually does
- [docs/adr/](docs/adr/) — architecture decision records
- [CONTRIBUTING.md](CONTRIBUTING.md) — branch and pull request conventions
- [CHANGELOG.md](CHANGELOG.md) — what has shipped

## Status (as of 2025-10-10, week 6)

Merged: PAY-1, PAY-2, PAY-4.
In review: PAY-5, PAY-6.
**Blocked: PAY-3** — draft since week 4, rewritten twice, see
[ADR-0003](docs/adr/0003-async-sca-state-machine.md).

## Running it

```bash
pip install -r requirements.txt
```

```bash
uvicorn src.payments.app:app --reload
```

```bash
pytest
```

Tests touching the gateway are currently skipped — the flow they were written
against no longer exists.
