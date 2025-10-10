#!/usr/bin/env bash
#
# Builds the git history for the demo repository: six branches, backdated
# commits, three of them merged into main, matching the dataset the guardian
# reads (data/github_activity.csv).
#
# The point of the history is that the PAY-3 story is readable in `git log -p`:
# a synchronous gateway added on 2025-09-22 and rewritten away on 2025-09-30,
# and a webhook parser rewritten again on 2025-10-07. Rework you can see rather
# than infer.
#
# Run it from anywhere:
#
#     bash simulation/build_history.sh              # build
#     bash simulation/build_history.sh --resnapshot # refresh sources first
#
# The final content of every file lives in a sources directory NEXT TO the
# repository (../margin-guardian-demo.sources), not inside it. The script only
# ever writes into the repository -- it never deletes the working tree, and
# rerunning it cannot lose work. It does replace .git.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$(cd "$ROOT/.." && pwd)/$(basename "$ROOT").sources"
cd "$ROOT"

if [[ "${1:-}" == "--resnapshot" ]]; then
  rm -rf "$SRC"
fi

if [[ ! -d "$SRC" ]]; then
  echo "Snapshotting the working tree into $SRC ..."
  mkdir -p "$SRC"
  tar --exclude=./.git --exclude=__pycache__ -cf - . | (cd "$SRC" && tar -xf -)
else
  echo "Using existing sources in $SRC (pass --resnapshot to refresh)"
fi

# Refresh the scaffolding from the sources NOW, not at the commit that adds it.
# Doing it later would overwrite this script while bash is still reading it, and
# bash reads a script by byte offset -- the moment the file changes length under
# it, it resumes parsing in the middle of a word.
mkdir -p simulation
cp -r "$SRC/simulation/." simulation/

echo "Resetting git history..."
rm -rf .git
git init -q -b main
git config user.email "delivery@example-agency.cz"
git config user.name "Delivery"

# --- helpers ---------------------------------------------------------------

# put <path-in-sources> <path-in-repo>
put() {
  mkdir -p "$(dirname "$2")"
  cp "$SRC/$1" "$2"
}

# commit <date> <author-key> <message> <path>...
commit() {
  local date="$1" who="$2" message="$3"; shift 3
  local name email
  case "$who" in
    tomas) name="Senior Dev";  email="senior.dev@example-agency.cz" ;;
    petra) name="Medior Dev"; email="medior.dev@example-agency.cz" ;;
    jana)  name="Junior Dev";  email="junior.dev@example-agency.cz" ;;
    marek) name="QA";         email="qa@example-agency.cz" ;;
    sona)  name="PM";         email="pm@example-agency.cz" ;;
    *) echo "unknown author $who" >&2; exit 1 ;;
  esac

  git add -A -- "$@"
  GIT_AUTHOR_NAME="$name" GIT_AUTHOR_EMAIL="$email" \
  GIT_COMMITTER_NAME="$name" GIT_COMMITTER_EMAIL="$email" \
  GIT_AUTHOR_DATE="${date}T10:00:00+02:00" \
  GIT_COMMITTER_DATE="${date}T10:00:00+02:00" \
    git commit -q -m "$message"
}

# merge_pr <date> <branch> <pr-number> <summary>
#
# The pr number is kept in the call sites as documentation of the intended
# ordering, but deliberately not written into the message: GitHub assigns its
# own numbers when the repository is seeded, and a commit message pointing at
# #101 when #101 does not exist is worse than no number at all.
merge_pr() {
  local date="$1" branch="$2" pr="$3" summary="$4"
  GIT_AUTHOR_NAME="PM" GIT_AUTHOR_EMAIL="pm@example-agency.cz" \
  GIT_COMMITTER_NAME="PM" GIT_COMMITTER_EMAIL="pm@example-agency.cz" \
  GIT_AUTHOR_DATE="${date}T17:00:00+02:00" \
  GIT_COMMITTER_DATE="${date}T17:00:00+02:00" \
    git merge -q --no-ff "$branch" -m "Merge branch '${branch}'

${summary}"
}

# ===========================================================================
# main -- project skeleton
# ===========================================================================

put .gitignore .gitignore
put CONTRIBUTING.md CONTRIBUTING.md
put requirements.txt requirements.txt
put .github/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE.md
put docs/scope.md docs/scope.md
commit 2025-09-02 sona "chore: repository, delivery conventions, agreed scope

Fixed-price engagement with Fictional Bank a.s., kick-off 2025-09-01.
docs/scope.md carries the agreed scope and the assumptions each estimate was
built on. Rates and contract value stay out of this repository." \
  .gitignore CONTRIBUTING.md requirements.txt .github/PULL_REQUEST_TEMPLATE.md docs/scope.md

put docs/adr/0001-payment-provider-abstraction.md docs/adr/0001-payment-provider-abstraction.md
commit 2025-09-05 tomas "docs: ADR-0001 separate transport from payment lifecycle

bank_api speaks HTTP to the bank, gateway owns the payment lifecycle, orders
depends on gateway through an interface. Lets PAY-4 merge without waiting for
PAY-3." \
  docs/adr/0001-payment-provider-abstraction.md

# ===========================================================================
# PAY-1 -- module skeleton (merged, PR #101)
# ===========================================================================

git checkout -q -b feature/PAY-1-module-skeleton

put src/payments/__init__.py src/payments/__init__.py
put simulation/history/config_pay1.py src/payments/config.py
commit 2025-09-03 petra "PAY-1: package layout and configuration" \
  src/payments/__init__.py src/payments/config.py

put simulation/history/app_pay1.py src/payments/app.py
put tests/__init__.py tests/__init__.py
put .github/workflows/ci.yml .github/workflows/ci.yml
commit 2025-09-08 petra "PAY-1: health endpoint and CI" \
  src/payments/app.py tests/__init__.py .github/workflows/ci.yml

git checkout -q main
merge_pr 2025-09-10 feature/PAY-1-module-skeleton 101 "PAY-1: Payment module skeleton

28h against a 30h estimate."

# ===========================================================================
# PAY-2 -- bank API integration (merged, PR #102)
# ===========================================================================

git checkout -q -b feature/PAY-2-bank-api

put src/payments/bank_api/__init__.py src/payments/bank_api/__init__.py
put simulation/history/bank_errors_pay2.py src/payments/bank_api/errors.py
commit 2025-09-11 tomas "PAY-2: bank transport package and error types" \
  src/payments/bank_api/__init__.py src/payments/bank_api/errors.py

put simulation/history/bank_client_pay2.py src/payments/bank_api/client.py
commit 2025-09-12 tomas "PAY-2: OAuth2 client credentials, request signing, retries

The API guide v1.4 section 4.2 documents the canonical signing string wrongly:
the sandbox wants the timestamp between path and body, and the path without
the /v1 prefix. Found by brute force against the signature-echo endpoint.
Ticket #4381 raised with the bank, no reply. Cost about a day and a half --
this is the PAY-2 overrun.

Do not 'fix' _sign() back to match the guide." \
  src/payments/bank_api/client.py

put tests/test_bank_client.py tests/test_bank_client.py
commit 2025-09-16 tomas "PAY-2: pin the signing format and the retry behaviour

Also verified charge() against the sandbox: POST /v1/charges returns 200 with
status captured in the same response, ~400ms round trip. Synchronous, which is
what the PAY-3 estimate assumes." \
  tests/test_bank_client.py

git checkout -q main
merge_pr 2025-09-17 feature/PAY-2-bank-api 102 "PAY-2: Bank API integration

68h against a 60h estimate, all of it request signing (#4381). Absorbed."

put docs/adr/0002-synchronous-gateway-client.md docs/adr/0002-synchronous-gateway-client.md
commit 2025-09-19 tomas "docs: ADR-0002 gateway is a synchronous call

The charge settles in one round trip, and the bank confirmed in writing on
2025-08-25 that our merchant profile is exempt from PSD2 strong customer
authentication for v1. So: no inbound endpoints, no persisted payment state,
no background jobs. PAY-3 is a 40h domain wrapper.

Risk noted and accepted: if SCA ever becomes mandatory, none of this survives." \
  docs/adr/0002-synchronous-gateway-client.md

# ===========================================================================
# PAY-3 -- payment gateway (draft, PR #103) -- the one that goes wrong
# ===========================================================================

git checkout -q -b feature/PAY-3-payment-gateway

put src/payments/gateway/__init__.py src/payments/gateway/__init__.py
put simulation/history/payment_sync.py src/payments/gateway/payment.py
commit 2025-09-22 tomas "PAY-3: payment gateway over the bank client

authorise() calls the bank and returns the outcome. A payment is a value, not
an entity -- no lifecycle, nothing to persist (ADR-0002)." \
  src/payments/gateway/__init__.py src/payments/gateway/payment.py

put simulation/history/test_gateway_sync.py tests/test_gateway.py
commit 2025-09-24 tomas "PAY-3: tests for the synchronous flow

Happy path works end to end against the sandbox. Opening the PR as a draft --
refunds still to do, should be out of draft in a couple of days." \
  tests/test_gateway.py

# 2025-09-26 the sandbox starts requiring SCA above 30 CZK.
# 2025-09-29 the bank confirms it is permanent (#4417).
# 2025-09-30 ADR-0003, and the rewrite.

git checkout -q main
put docs/adr/0003-async-sca-state-machine.md docs/adr/0003-async-sca-state-machine.md
commit 2025-09-30 tomas "docs: ADR-0003 gateway becomes an async SCA state machine

Supersedes ADR-0002. The sandbox began requiring 3-D Secure above 30 CZK on
2025-09-26; the bank confirmed on 2025-09-29 (#4417) that the exemption we
estimated against was a misconfiguration on their side and that production
will require SCA at go-live.

Assumptions 1-4 behind the PAY-3 estimate are void. New surface: a persisted
Payment entity, an inbound webhook endpoint with an idempotency store, a
reconciliation job, and a versioned payload parser. None of it is in the 40h.

This has not been re-estimated in Jira." \
  docs/adr/0003-async-sca-state-machine.md

git checkout -q feature/PAY-3-payment-gateway
GIT_AUTHOR_NAME="Senior Dev" GIT_AUTHOR_EMAIL="senior.dev@example-agency.cz" \
GIT_COMMITTER_NAME="Senior Dev" GIT_COMMITTER_EMAIL="senior.dev@example-agency.cz" \
GIT_AUTHOR_DATE="2025-09-30T09:00:00+02:00" \
GIT_COMMITTER_DATE="2025-09-30T09:00:00+02:00" \
  git merge -q --no-ff main -m "Merge main into PAY-3 (ADR-0003)"

put src/payments/config.py src/payments/config.py
put src/payments/bank_api/errors.py src/payments/bank_api/errors.py
put src/payments/bank_api/client.py src/payments/bank_api/client.py
put src/payments/gateway/payment.py src/payments/gateway/payment.py
put src/payments/gateway/repository.py src/payments/gateway/repository.py
put tests/test_gateway.py tests/test_gateway.py
commit 2025-09-30 tomas "PAY-3: rewrite the gateway as an async state machine (ADR-0003)

Deletes the synchronous gateway and everything built on it. A payment is now
an entity with a lifecycle that outlives the request: authorising ->
pending_challenge -> captured / failed / expired, persisted, restart-safe.

Discarded: PaymentResult, the synchronous authorise(), and the tests for both.
orders and checkout were written against that shape. Roughly two days of work.

The e2e tests are skipped rather than deleted -- they are the specification of
what PAY-4 and PAY-5 were built against, and somebody has to decide what
replaces it.

Worth noting: every old fixture charged 25 CZK, under the 30 CZK exemption,
which is why CI stayed green for two days while nothing real worked." \
  src/payments/config.py src/payments/bank_api src/payments/gateway tests/test_gateway.py

put simulation/history/webhooks_v20.py src/payments/gateway/webhooks.py
put src/payments/app.py src/payments/app.py
commit 2025-10-02 tomas "PAY-3: inbound webhook endpoint, signature verification, idempotency

The first inbound endpoint this project has ever had. It has to be publicly
reachable in every environment including local development, which nobody
scoped.

Guide 7.1 promises at-least-once delivery in causal order. We get the first
half: challenge.completed arrives twice, and payment.captured sometimes lands
before it. So the state machine is an event lookup where a duplicate is a
no-op and ordering does not matter, keyed on (challenge_id, event_type).

Also found: an abandoned challenge produces no terminal event at all and the
sandbox never expires it, so those payments hang in pending_challenge forever.
Needs a reconciliation poller, which needs a scheduler this project does not
have." \
  src/payments/gateway/webhooks.py src/payments/app.py

put src/payments/gateway/webhooks.py src/payments/gateway/webhooks.py
put tests/test_webhooks.py tests/test_webhooks.py
commit 2025-10-07 tomas "PAY-3: negotiate the webhook payload version (#4468)

Every webhook started 400ing overnight. The sandbox moved to v2.1 and renamed
the fields with no changelog and no email:

  challenge_result   -> authentication.status
  charge_id          -> payment.id
  result Y/N         -> status authenticated/rejected

The bank says v2.1 was announced in a developer portal we have no access to.
Both shapes are now pinned in tests so it cannot happen silently again.

Second rewrite of this file in a week." \
  src/payments/gateway/webhooks.py tests/test_webhooks.py

# ===========================================================================
# PAY-4 -- order backend (merged, PR #104)
# ===========================================================================

git checkout -q main
git checkout -q -b feature/PAY-4-order-backend

put src/payments/orders/__init__.py src/payments/orders/__init__.py
put simulation/history/app_pay4.py src/payments/app.py
commit 2025-09-25 petra "PAY-4: order endpoints

Talks to gateway through the ADR-0001 interface, so this does not wait for
PAY-3. POST /orders/{id}/pay is stubbed until the gateway lands." \
  src/payments/orders/__init__.py src/payments/app.py

put src/payments/orders/models.py src/payments/orders/models.py
commit 2025-09-30 petra "PAY-4: order model, state machine, payment_id (ADR-0003)

A payment has its own lifecycle now, so the order references it rather than
storing the outcome as a flag. Cheap here because the coupling was already an
interface. PAY-3 is not so lucky." \
  src/payments/orders/models.py

git checkout -q main
merge_pr 2025-10-01 feature/PAY-4-order-backend 104 "PAY-4: Order backend

50h against a 50h estimate."

# PAY-3 catches up with main so it has the order model PAY-4 merged. app.py
# conflicts: PAY-4 stubbed POST /orders/{id}/pay, PAY-3 implements it against
# the async gateway. The PAY-3 version wins.
git checkout -q feature/PAY-3-payment-gateway
git merge --no-ff --no-commit main >/dev/null 2>&1 || true
put src/payments/app.py src/payments/app.py
git add -A -- src/payments/app.py
GIT_AUTHOR_NAME="Senior Dev" GIT_AUTHOR_EMAIL="senior.dev@example-agency.cz" \
GIT_COMMITTER_NAME="Senior Dev" GIT_COMMITTER_EMAIL="senior.dev@example-agency.cz" \
GIT_AUTHOR_DATE="2025-10-08T09:00:00+02:00" \
GIT_COMMITTER_DATE="2025-10-08T09:00:00+02:00" \
  git commit -q -m "Merge main into PAY-3 (PAY-4 order model)

POST /orders/{id}/pay can no longer answer paid or not paid -- above the
exemption threshold the answer does not exist yet when the request returns.
It hands back a challenge_url instead, which nothing in checkout knows how to
render. Flagged on #105."

# ===========================================================================
# PAY-5 -- checkout frontend (open, PR #105)
# ===========================================================================

git checkout -q main
git checkout -q -b feature/PAY-5-checkout-frontend

put src/payments/checkout/__init__.py src/payments/checkout/__init__.py
put src/payments/checkout/views.py src/payments/checkout/views.py
commit 2025-10-08 jana "PAY-5: checkout page, payment form, result screens

Blocked on the last two screens. The estimate assumed two outcomes, paid and
not paid. Since ADR-0003 there is a third -- sent to the bank, outcome not
known yet -- which needs a redirect out and a return handler that may run
before the webhook lands. Neither is in the 40h.

30h of 40h used, and the remaining work is bigger than the 10h left." \
  src/payments/checkout

# ===========================================================================
# PAY-6 -- automated test suite (open, PR #106)
# ===========================================================================

git checkout -q main
git checkout -q -b feature/PAY-6-test-suite

put tests/test_orders.py tests/test_orders.py
commit 2025-10-08 marek "PAY-6: order lifecycle tests, realistic fixture amounts

The one part of the suite that is not blocked on PAY-3.

Fixtures now charge 2400 CZK rather than 25. The old amount sat under the
bank's 30 CZK exemption, so CI stayed green for two days after 2025-09-26
while no real payment worked. Green CI, broken product.

12h of 35h used -- not because it is going well, but because there is no
stable interface to test against. The remaining 23h is still ahead of us." \
  tests/test_orders.py

# ===========================================================================
# main -- the rest of the documentation
# ===========================================================================

git checkout -q main

put docs/bank-api-notes.md docs/bank-api-notes.md
commit 2025-10-09 tomas "docs: sandbox working notes through 2025-10-09

What the sandbox actually does, as opposed to what the guide says it does.
Includes the bank's reply on #4417 and where PAY-3 stands: 20-25h to something
mergeable, and that is a guess, not an estimate." \
  docs/bank-api-notes.md

put README.md README.md
put CHANGELOG.md CHANGELOG.md
commit 2025-10-10 sona "docs: week 6 status

Merged: PAY-1, PAY-2, PAY-4. In review: PAY-5, PAY-6. Blocked: PAY-3, draft
since week 4, rewritten twice, nothing merged against a 40h estimate.

Stopping work on PAY-3 until it is out of draft for review and the remaining
work is broken out. Change request on the SCA scope going to the client." \
  README.md CHANGELOG.md simulation

# ===========================================================================

echo
echo "Branches:"
git branch --format='  %(refname:short)'
echo
git log --graph --all --date=short --pretty='%h %ad %an  %s' | head -45
echo
echo "Sources kept in: $SRC"
echo "Next: python simulation/seed_github.py --repo owner/name"
