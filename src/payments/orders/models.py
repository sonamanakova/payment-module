"""Order model and state machine. PAY-4, merged."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    DRAFT = "draft"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


TRANSITIONS = {
    OrderStatus.DRAFT: {OrderStatus.AWAITING_PAYMENT, OrderStatus.CANCELLED},
    OrderStatus.AWAITING_PAYMENT: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


@dataclass
class Order:
    order_id: str
    customer_id: str
    amount_czk: int
    status: OrderStatus = OrderStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)

    # PAY-4 was written against ADR-0002, where a payment was a result, not an
    # entity: the gateway returned paid or not paid and we wrote it here. Since
    # ADR-0003 a payment has its own lifecycle and its own table, so this is now
    # a reference to it. The rest of PAY-4 did not need to change.
    payment_id: str | None = None

    def transition_to(self, status):
        if status not in TRANSITIONS[self.status]:
            raise ValueError(f"cannot move order from {self.status} to {status}")
        self.status = status
