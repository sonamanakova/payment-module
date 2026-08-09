"""Inbound webhook from the bank. PAY-3 -- IN PROGRESS.

None of this was in the estimate. Before ADR-0003 this project had no inbound
endpoints at all: it called the bank and the bank never called us. Making one
endpoint work meant signature verification, an idempotency store, a publicly
reachable URL in every environment, and a parser that survives the bank changing
the payload shape without telling anyone.

Rewritten once already, on 2025-10-07, when the sandbox moved to v2.1 and
renamed three fields overnight (ticket #4468). Hence the version negotiation
below -- trusting a single payload shape is what broke the first time.
"""

import hashlib
import hmac

from ..config import settings
from .payment import PaymentState

SUPPORTED_VERSIONS = {"2.0", "2.1"}


class UnknownPayloadVersion(Exception):
    """The bank sent a shape we have never seen. Do not guess -- guessing is
    what silently marked payments captured for two days in October."""


def verify_signature(raw_body: bytes, header_signature: str) -> bool:
    expected = hmac.new(
        settings.webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_signature or "")


def parse_event(payload: dict) -> dict:
    """Normalise a webhook payload into {challenge_id, outcome, charge_id}.

    v2.0 and v2.1 disagree about the name of every field involved:

        v2.0                      v2.1
        challenge_result          authentication.status
        charge_id                 payment.id
        result: "Y" / "N"         status: "authenticated" / "rejected"
    """
    version = payload.get("version", "2.0")
    if version not in SUPPORTED_VERSIONS:
        raise UnknownPayloadVersion(version)

    if version == "2.1":
        authentication = payload.get("authentication", {})
        return {
            "challenge_id": authentication.get("challenge_id"),
            "outcome": authentication.get("status"),
            "charge_id": payload.get("payment", {}).get("id"),
            "authentication_reference": authentication.get("reference"),
        }

    result = payload.get("challenge_result", {})
    return {
        "challenge_id": result.get("challenge_id"),
        "outcome": "authenticated" if result.get("result") == "Y" else "rejected",
        "charge_id": payload.get("charge_id"),
        # v2.0 does not carry it at all, which is part of why refunds are stuck.
        "authentication_reference": None,
    }


class WebhookHandler:
    def __init__(self, repository, seen=None):
        self.repository = repository
        # Idempotency: the sandbox delivers the same event more than once, and
        # sometimes delivers the capture before the challenge result.
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
            # Out-of-order arrival, or a challenge we never started. Both are
            # real in the sandbox. Swallowing it loses the event; there is no
            # dead-letter queue to put it on yet.
            # TODO(PAY-3): decide what happens here.
            return {"status": "ignored", "reason": "unknown challenge"}

        if event.get("authentication_reference"):
            payment.authentication_reference = event["authentication_reference"]
        state = payment.apply(event["outcome"])
        if state is PaymentState.CAPTURED and event.get("charge_id"):
            payment.charge_id = event["charge_id"]
        self.repository.save(payment)

        return {"status": "ok", "payment_state": state.value}
