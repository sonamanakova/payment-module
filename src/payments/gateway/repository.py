"""Persistence for payments. PAY-3 -- IN PROGRESS.

There was no payment store in the original design: a payment was a result you
wrote onto the order and forgot (ADR-0002). pending_challenge changed that --
it is a state that lasts up to fifteen minutes, spans two HTTP requests from
two different parties, and has to survive a restart.

In-memory for now, which means a deploy loses every in-flight payment. A real
table plus a migration is still to do.
"""

from datetime import datetime, timedelta

from .payment import PaymentState


class InMemoryPaymentRepository:
    def __init__(self):
        self._by_id = {}
        self._by_challenge = {}

    def save(self, payment):
        self._by_id[payment.payment_id] = payment
        if payment.challenge_id:
            self._by_challenge[payment.challenge_id] = payment
        return payment

    def get(self, payment_id):
        return self._by_id[payment_id]

    def get_by_challenge(self, challenge_id):
        return self._by_challenge.get(challenge_id)

    def stale_pending(self, timeout_seconds):
        """Payments stuck in pending_challenge past the timeout."""
        cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
        return [
            payment
            for payment in self._by_id.values()
            if payment.state is PaymentState.PENDING_CHALLENGE
            and payment.updated_at < cutoff
        ]


# TODO(PAY-3): SqlPaymentRepository. Needs a payments table, a migration, and a
# decision on whether the order still owns the amount or the payment does. Not
# started -- everything above is lost on restart, which is not shippable.
