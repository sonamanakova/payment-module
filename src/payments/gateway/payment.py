"""Payment lifecycle. PAY-3 -- IN PROGRESS, do not rely on this yet.

Second version of this file. The first one (ADR-0002) was a synchronous wrapper:
authorise() called the bank, got a final answer, returned it. That version is
gone -- since 2025-09-26 the bank answers with a 3-D Secure challenge instead of
a result, and the actual outcome arrives later on a webhook.

So a payment is no longer a function call, it is a process with a lifecycle that
outlives the request, survives a restart, and can end without anyone telling us.
See ADR-0003.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..bank_api.client import BankClient
from ..bank_api.errors import ScaRequired
from ..config import settings


class PaymentState(str, Enum):
    AUTHORISING = "authorising"
    PENDING_CHALLENGE = "pending_challenge"
    CAPTURED = "captured"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUNDED = "refunded"


TERMINAL = {PaymentState.CAPTURED, PaymentState.FAILED, PaymentState.EXPIRED,
            PaymentState.REFUNDED}

# Events arrive out of order and more than once (bank guide 7.1 claims causal
# ordering; the sandbox does not deliver it -- see bank-api-notes 2025-10-02).
# So this is a lookup of what an event means, not a sequence we walk. Applying
# an event that does not move the state is a no-op rather than an error.
ON_EVENT = {
    ("pending_challenge", "authenticated"): PaymentState.CAPTURED,
    ("pending_challenge", "rejected"): PaymentState.FAILED,
    ("authorising", "authenticated"): PaymentState.CAPTURED,
    ("authorising", "rejected"): PaymentState.FAILED,
}


@dataclass
class Payment:
    payment_id: str
    order_id: str
    amount_czk: int
    state: PaymentState = PaymentState.AUTHORISING
    charge_id: str | None = None
    challenge_id: str | None = None
    challenge_url: str | None = None
    challenge_expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # TODO(PAY-3): the bank requires the original authentication reference to
    # refund an SCA payment. We are not storing it, so refunds of anything above
    # the exemption threshold currently fail. Blocks the refund path entirely.
    authentication_reference: str | None = None

    @property
    def is_terminal(self):
        return self.state in TERMINAL

    def apply(self, outcome):
        """Move the payment on the strength of a webhook outcome.

        Idempotent by construction: a duplicate event maps a terminal state onto
        nothing and is ignored. Ordering does not matter either -- if capture
        arrives before the challenge result, the payment is already captured and
        the later event is a no-op.
        """
        if self.is_terminal:
            return self.state
        next_state = ON_EVENT.get((self.state.value, outcome))
        if next_state is None:
            return self.state
        self.state = next_state
        self.updated_at = datetime.utcnow()
        return self.state


class PaymentGateway:
    """What orders calls. Provider-agnostic by ADR-0001."""

    def __init__(self, repository, client=None):
        self.repository = repository
        self.client = client or BankClient()

    def authorise(self, order_id, amount_czk, customer_return_url):
        """Start a payment.

        Returns a Payment. Note what this no longer does: tell you whether the
        customer paid. Above the exemption threshold the answer does not exist
        yet at the point this returns -- the caller has to send the customer to
        payment.challenge_url and wait for the webhook. Every caller written
        before 2025-09-26 assumes otherwise.
        """
        payment = Payment(
            payment_id=_new_id(),
            order_id=order_id,
            amount_czk=amount_czk,
        )
        self.repository.save(payment)

        try:
            result = self.client.charge(
                amount_czk=amount_czk,
                order_reference=order_id,
                return_url=customer_return_url,
            )
        except ScaRequired as challenge:
            payment.state = PaymentState.PENDING_CHALLENGE
            payment.challenge_id = challenge.challenge_id
            payment.challenge_url = challenge.challenge_url
            payment.challenge_expires_at = datetime.utcnow() + timedelta(
                seconds=challenge.expires_in
            )
            payment.updated_at = datetime.utcnow()
            self.repository.save(payment)
            return payment

        # Under the threshold the bank still settles in one round trip.
        payment.charge_id = result["id"]
        payment.state = (
            PaymentState.CAPTURED
            if result.get("status") == "captured"
            else PaymentState.FAILED
        )
        payment.updated_at = datetime.utcnow()
        self.repository.save(payment)
        return payment

    def refund(self, payment_id, amount_czk=None):
        payment = self.repository.get(payment_id)
        if payment.state is not PaymentState.CAPTURED:
            raise ValueError(f"cannot refund a payment in state {payment.state}")

        # TODO(PAY-3): BLOCKED. The bank rejects refunds of an SCA-authenticated
        # charge unless we pass the authentication reference from the original
        # challenge, and we never stored it (see Payment above). Needs a schema
        # change, a backfill for payments already captured, and the webhook
        # parser to start reading the field. Not started.
        raise NotImplementedError(
            "refunds of SCA payments need the authentication reference -- PAY-3"
        )

    def reconcile(self):
        """Close out payments whose challenge result never arrived.

        A customer who abandons the bank's page produces no terminal event at
        all, and the sandbox does not expire the challenge either, so without
        this the payment sits in pending_challenge forever.

        TODO(PAY-3): NOT IMPLEMENTED. Needs a scheduler, which this project does
        not have -- there was no background work of any kind in the original
        scope. Roughly a day, plus whatever it takes to get a worker deployed.
        """
        stale = self.repository.stale_pending(settings.challenge_timeout_seconds)
        raise NotImplementedError(f"reconciliation job not written ({len(stale)} stale)")


def _new_id():
    import uuid

    return f"pay_{uuid.uuid4().hex[:16]}"
