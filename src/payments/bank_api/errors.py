"""Errors raised by the bank transport layer. PAY-2."""


class BankError(Exception):
    """Anything the bank rejected that we cannot handle."""


class BankAuthError(BankError):
    """Token request failed."""
