"""Configuration. PAY-1."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bank_base_url: str = os.environ.get(
        "BANK_BASE_URL", "https://sandbox.fictionalbank.cz"
    )
    bank_client_id: str = os.environ.get("BANK_CLIENT_ID", "")
    bank_client_secret: str = os.environ.get("BANK_CLIENT_SECRET", "")
    bank_signing_key: str = os.environ.get("BANK_SIGNING_KEY", "")

    # PAY-3, added 2025-09-30 (ADR-0003). The bank posts challenge results here,
    # so it has to be reachable from outside -- which nothing in this project
    # was, before.
    webhook_secret: str = os.environ.get("BANK_WEBHOOK_SECRET", "")
    webhook_public_url: str = os.environ.get("BANK_WEBHOOK_PUBLIC_URL", "")

    # Below this the bank still settles synchronously (PSD2 low-value exemption).
    # Above it, every charge goes through a 3-D Secure challenge.
    sca_exemption_threshold_czk: int = 30

    # How long we wait for a challenge result before the reconciliation job
    # closes the payment out. Not implemented yet -- PAY-3.
    challenge_timeout_seconds: int = 900

    currency: str = "CZK"


settings = Settings()
