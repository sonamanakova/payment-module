"""Order lifecycle tests. PAY-6.

The one part of the suite that is not blocked on PAY-3, because orders talks to
the gateway through an interface (ADR-0001) rather than to the bank.
"""

import pytest

from src.payments.orders.models import Order, OrderStatus

REAL_AMOUNT_CZK = 2400


def make_order():
    return Order(order_id="ord_1", customer_id="cus_1", amount_czk=REAL_AMOUNT_CZK)


def test_order_starts_as_draft():
    assert make_order().status is OrderStatus.DRAFT


def test_happy_path():
    order = make_order()
    order.transition_to(OrderStatus.AWAITING_PAYMENT)
    order.transition_to(OrderStatus.PAID)
    assert order.status is OrderStatus.PAID


def test_cannot_pay_a_cancelled_order():
    order = make_order()
    order.transition_to(OrderStatus.CANCELLED)
    with pytest.raises(ValueError):
        order.transition_to(OrderStatus.PAID)


def test_refund_only_from_paid():
    order = make_order()
    with pytest.raises(ValueError):
        order.transition_to(OrderStatus.REFUNDED)
