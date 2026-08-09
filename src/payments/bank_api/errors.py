"""Errors raised by the bank transport layer. PAY-2, plus one addition in PAY-3."""


class BankError(Exception):
    """Anything the bank rejected that we cannot handle."""


class BankAuthError(BankError):
    """Token request failed."""


class ScaRequired(BankError):
    """The bank will not settle this charge without a 3-D Secure challenge.

    Added 2025-09-30 (PAY-3, ADR-0003). Modelled as an exception rather than a
    return value on purpose: every caller written before 2025-09-26 assumed
    charge() returns a final result, and there is no correct default for them.
    Failing loudly is better than silently treating a pending challenge as a
    successful payment.
    """

    def __init__(self, challenge_id, challenge_url, expires_in):
        super().__init__(f"strong customer authentication required: {challenge_id}")
        self.challenge_id = challenge_id
        self.challenge_url = challenge_url
        self.expires_in = expires_in
