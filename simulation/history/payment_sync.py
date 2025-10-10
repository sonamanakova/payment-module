"""Payment lifecycle. PAY-3.

Thin domain wrapper over the client PAY-2 built. A charge is one round trip to
the bank: you ask, you get an answer, you write it onto the order. ADR-0002.

This file is the version that was discarded on 2025-09-30 (ADR-0003). It is
here in git history, not in the tree.
"""

from dataclasses import dataclass

from ..bank_api.client import BankClient


@dataclass(frozen=True)
class PaymentResult:
    """The whole payment, as far as anyone outside this module is concerned.

    Note what this is: a value, not an entity. There is no lifecycle, no state
    to persist, nothing that outlives the request. That is the entire premise
    of ADR-0002, and it is what orders (PAY-4) and checkout (PAY-5) were both
    written against.
    """

    paid: bool
    charge_id: str | None
    failure_reason: str | None = None


class PaymentGateway:
    def __init__(self, client=None):
        self.client = client or BankClient()

    def authorise(self, order_id, amount_czk):
        """Charge the customer. Returns the final outcome."""
        result = self.client.charge(amount_czk=amount_czk, order_reference=order_id)
        if result.get("status") == "captured":
            return PaymentResult(paid=True, charge_id=result["id"])
        return PaymentResult(
            paid=False,
            charge_id=result.get("id"),
            failure_reason=result.get("decline_reason", "unknown"),
        )

    def refund(self, charge_id):
        """Full refund. Single call, nothing to track."""
        self.client.refund(charge_id)
        return True
