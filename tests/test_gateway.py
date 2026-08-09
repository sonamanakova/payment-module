"""Gateway tests. PAY-3 / PAY-6.

Most of this file is skipped. The tests were written against the synchronous
flow in ADR-0002 -- authorise() returned a final result and you asserted on it.
That function signature no longer exists (ADR-0003).

They are skipped rather than deleted on purpose: they are the specification of
the behaviour orders and checkout were both built against, and somebody has to
decide what replaces it before they can be rewritten.

Note the fixture amount. Every one of these used 25 CZK, under the 30 CZK
exemption threshold, so the suite stayed green for two days after 2025-09-26
while no real payment worked at all.
"""

import pytest

from src.payments.gateway.payment import Payment, PaymentState
from src.payments.gateway.repository import InMemoryPaymentRepository

SMALL_AMOUNT_CZK = 25
REAL_AMOUNT_CZK = 2400


@pytest.mark.skip(reason="PAY-3: authorise() no longer returns a final result (ADR-0003)")
def test_authorise_returns_captured_payment():
    ...


@pytest.mark.skip(reason="PAY-3: refunds blocked on the authentication reference")
def test_refund_full_amount():
    ...


@pytest.mark.skip(reason="PAY-3: reconciliation job not written")
def test_abandoned_challenge_expires():
    ...


def test_duplicate_event_is_a_no_op():
    """The sandbox delivers the same event more than once."""
    payment = Payment("pay_1", "ord_1", REAL_AMOUNT_CZK,
                      state=PaymentState.PENDING_CHALLENGE)
    assert payment.apply("authenticated") is PaymentState.CAPTURED
    assert payment.apply("authenticated") is PaymentState.CAPTURED
    assert payment.apply("rejected") is PaymentState.CAPTURED


def test_out_of_order_event_does_not_corrupt_state():
    """Capture sometimes arrives before the challenge result."""
    payment = Payment("pay_2", "ord_2", REAL_AMOUNT_CZK,
                      state=PaymentState.PENDING_CHALLENGE)
    payment.apply("authenticated")
    assert payment.apply("rejected") is PaymentState.CAPTURED


def test_stale_pending_is_found():
    repository = InMemoryPaymentRepository()
    payment = Payment("pay_3", "ord_3", REAL_AMOUNT_CZK,
                      state=PaymentState.PENDING_CHALLENGE)
    repository.save(payment)
    assert repository.stale_pending(timeout_seconds=0) == [payment]
