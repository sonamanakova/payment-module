"""Gateway tests. PAY-3, ADR-0002 version -- discarded on 2025-09-30.

Every fixture charges 25 CZK. Nobody thought about why at the time; it was just
a small round number. It is under the bank's 30 CZK low-value exemption, which
is why this suite stayed green for two days after 2025-09-26 while no real
payment worked.
"""

from unittest.mock import Mock

from src.payments.gateway.payment import PaymentGateway

AMOUNT_CZK = 25


def test_authorise_returns_captured_payment():
    client = Mock()
    client.charge.return_value = {"id": "chg_1", "status": "captured"}

    result = PaymentGateway(client=client).authorise("ord_1", AMOUNT_CZK)

    assert result.paid is True
    assert result.charge_id == "chg_1"


def test_authorise_maps_decline():
    client = Mock()
    client.charge.return_value = {
        "id": "chg_2",
        "status": "declined",
        "decline_reason": "insufficient_funds",
    }

    result = PaymentGateway(client=client).authorise("ord_2", AMOUNT_CZK)

    assert result.paid is False
    assert result.failure_reason == "insufficient_funds"


def test_refund_full_amount():
    client = Mock()
    assert PaymentGateway(client=client).refund("chg_1") is True
    client.refund.assert_called_once_with("chg_1")
