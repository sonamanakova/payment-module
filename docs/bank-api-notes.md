# Fictional Bank sandbox — working notes

Running log of what the sandbox actually does, as opposed to what the API guide
says it does. Kept by the senior dev because the two kept diverging.

Bank API guide version referenced throughout: **v1.4** (2025-06).

---

### 2025-09-08 — auth works

OAuth2 client credentials against `https://sandbox.fictionalbank.cz/oauth/token`.
Token TTL 900s. Refresh is straightforward.

### 2025-09-12 — request signing is documented wrong

The guide (§4.2) says the canonical string is
`METHOD + "\n" + PATH + "\n" + BODY`. The sandbox actually expects the timestamp
between path and body, and the path *without* the `/v1` prefix. Found it by
brute-forcing the combinations against a signature-echo endpoint.

Cost: about a day and a half. This is the PAY-2 overrun. Reported to the bank
(ticket **#4381**), no reply.

### 2025-09-18 — charge endpoint, synchronous, as expected

`POST /v1/charges` returns `200` with `status: "captured"` in the same response.
Round trip ~400ms. This is the flow PAY-3 was estimated against, and it works.

### 2025-09-22 — starting PAY-3

Thin wrapper. `Payment.authorise()` -> `bank_api.charge()` -> done.

### 2025-09-24 — draft PR opened

Happy path works end to end against the sandbox. Opened as draft because refunds
aren't in yet. Expected to finish inside the week.

### 2025-09-26 — sandbox started returning 402

Every charge above 30 CZK now comes back:

```json
{
  "status": "sca_required",
  "challenge_url": "https://sandbox.fictionalbank.cz/3ds/challenge/{id}",
  "challenge_id": "ch_...",
  "expires_in": 600
}
```

Charges under 30 CZK still complete synchronously, which is why the test suite
(all fixtures use 25 CZK) stayed green for two days while nothing real worked.

Raised with the bank — ticket **#4417**.

### 2025-09-29 — bank replies to #4417

Quoting the reply:

> The sandbox merchant profile was migrated to the PSD2-compliant configuration
> on 2025-09-26. Strong customer authentication is mandatory for all transactions
> above the 30 CZK low-value exemption threshold. This matches the production
> configuration your merchant account will receive at go-live. The previous
> behaviour was a sandbox misconfiguration on our side.

So the exemption we were told about on 2025-08-25 was never real — it was a
misconfigured sandbox, and now it is fixed. This is not a temporary sandbox
issue we can wait out; production will behave the same way.

What this means concretely for PAY-3:

- The charge is now **two-phase and asynchronous**: we get a challenge, the
  customer authenticates at the bank, and the bank tells us the result *later*.
- The result arrives on a **webhook** we have to expose, authenticate and make
  publicly reachable. We had no inbound endpoint at all.
- A payment now has a **lifecycle** — `pending_challenge` is a state that can
  last ten minutes and survive a process restart. It needs to be persisted as
  its own entity, not as a field on an order.
- The **frontend has to redirect** the customer to the challenge URL and handle
  their return. That is PAY-5's problem, and it is not in PAY-5's estimate.

None of this is in the 40h.

### 2025-09-30 — decision

ADR-0003. Rewrite `gateway` as an asynchronous state machine. ADR-0002 (the
synchronous client) is superseded, roughly two days of work thrown away.

### 2025-10-02 — webhooks are unordered and duplicated

The sandbox delivers `challenge.completed` more than once, and sometimes
`payment.captured` arrives *before* `challenge.completed`. Guide §7.1 promises
"at-least-once delivery in causal order". The first half is true.

Consequence: we need an idempotency store keyed on `(challenge_id, event_type)`
and the state machine has to accept events out of order rather than assume a
sequence. Another day.

### 2025-10-06 — reconciliation

Some challenges are simply never reported. The customer abandons the bank page,
and no terminal event ever arrives — the payment sits in `pending_challenge`
forever. Sandbox does not expire them. We need a periodic job that polls
`GET /v1/charges/{id}` for stale payments and closes them out. Not in scope,
still necessary.

### 2025-10-07 — sandbox v2.1, payload changed without notice

Webhook payloads changed shape overnight:

| v2.0 | v2.1 |
|---|---|
| `challenge_result` | `authentication.status` |
| `charge_id` | `payment.id` |
| `result: "Y" / "N"` | `status: "authenticated" / "rejected"` |

No changelog entry, no email. Found it because every webhook started 400ing in
the integration tests. Ticket **#4468** — reply says v2.1 was "announced in the
developer portal", which we do not have access to.

Second rewrite of the webhook parser in a week. Version negotiation added so
this cannot happen again silently.

### 2025-10-09 — where PAY-3 stands

Working: authorise up to challenge, challenge redirect URL, webhook receipt and
verification, idempotency store, state machine for the happy path.

Not working: refunds against SCA payments (the bank requires the original
authentication reference and we are not storing it yet), reconciliation job (not
started), partial capture (never in scope, but `orders` now assumes it).

Best guess to something mergeable: 20–25h. That is a guess, not an estimate —
nobody has sat down and broken it out.
