"""Inbound webhook from the bank. PAY-3 -- IN PROGRESS.

New surface, added by ADR-0003. Before this the project had no inbound
endpoints at all: we called the bank, the bank never called us.

Sandbox delivers the same event more than once, and sometimes delivers the
capture before the challenge result, despite guide 7.1 promising causal
ordering. Hence the idempotency store and the event lookup below.
"""

import hashlib
import hmac

from ..config import settings
from .payment import PaymentState


def verify_signature(raw_body: bytes, header_signature: str) -> bool:
    expected = hmac.new(
        settings.webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_signature or "")


def parse_event(payload: dict) -> dict:
    """Normalise a webhook payload into {challenge_id, outcome, charge_id}."""
    result = payload.get("challenge_result", {})
    return {
        "challenge_id": result.get("challenge_id"),
        "outcome": "authenticated" if result.get("result") == "Y" else "rejected",
        "charge_id": payload.get("charge_id"),
    }


class WebhookHandler:
    def __init__(self, repository, seen=None):
        self.repository = repository
        self.seen = seen if seen is not None else set()

    def handle(self, raw_body: bytes, header_signature: str, payload: dict):
        if not verify_signature(raw_body, header_signature):
            return {"status": "rejected", "reason": "bad signature"}

        event = parse_event(payload)
        key = (event["challenge_id"], event["outcome"])
        if key in self.seen:
            return {"status": "ignored", "reason": "duplicate"}
        self.seen.add(key)

        payment = self.repository.get_by_challenge(event["challenge_id"])
        if payment is None:
            # TODO(PAY-3): decide what happens here. No dead-letter queue.
            return {"status": "ignored", "reason": "unknown challenge"}

        state = payment.apply(event["outcome"])
        if state is PaymentState.CAPTURED and event.get("charge_id"):
            payment.charge_id = event["charge_id"]
        self.repository.save(payment)

        return {"status": "ok", "payment_state": state.value}
