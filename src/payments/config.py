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
    currency: str = "CZK"


settings = Settings()
