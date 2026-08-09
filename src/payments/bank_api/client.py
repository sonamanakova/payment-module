"""HTTP client for the Fictional Bank sandbox. PAY-2, merged.

Transport only: authentication, request signing, retries, error mapping. It
knows nothing about orders or the payment lifecycle -- that is gateway's job
(ADR-0001).
"""

import base64
import hashlib
import hmac
import time

import requests

from ..config import settings
from .errors import BankAuthError, BankError, ScaRequired

TOKEN_PATH = "/oauth/token"
CHARGES_PATH = "/v1/charges"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class BankClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or settings.bank_base_url
        self._token = None
        self._token_expires_at = 0.0

    # -- auth ---------------------------------------------------------------

    def _access_token(self):
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        response = requests.post(
            f"{self.base_url}{TOKEN_PATH}",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.bank_client_id,
                "client_secret": settings.bank_client_secret,
            },
            timeout=15,
        )
        if response.status_code != 200:
            raise BankAuthError(f"token request failed: {response.status_code}")

        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload.get("expires_in", 900)
        return self._token

    # -- signing ------------------------------------------------------------

    @staticmethod
    def _sign(method, path, body, timestamp):
        """HMAC-SHA256 over the canonical request string.

        The bank's API guide v1.4 section 4.2 documents this as
        METHOD \\n PATH \\n BODY. That is wrong. The sandbox wants the timestamp
        between the path and the body, and the path without the /v1 prefix.
        Ticket #4381, no reply. Do not "fix" this back to match the guide.
        """
        canonical_path = path[3:] if path.startswith("/v1") else path
        canonical = f"{method}\n{canonical_path}\n{timestamp}\n{body}"
        digest = hmac.new(
            settings.bank_signing_key.encode(), canonical.encode(), hashlib.sha256
        ).digest()
        return base64.b64encode(digest).decode()

    def _request(self, method, path, body=""):
        timestamp = str(int(time.time()))
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "X-Timestamp": timestamp,
            "X-Signature": self._sign(method, path, body, timestamp),
            "Content-Type": "application/json",
        }

        last = None
        for attempt in range(MAX_RETRIES):
            response = requests.request(
                method, f"{self.base_url}{path}", headers=headers, data=body, timeout=30
            )
            if response.status_code not in RETRYABLE_STATUS:
                return response
            last = response
            time.sleep(2**attempt)
        return last

    # -- charges ------------------------------------------------------------

    def charge(self, amount_czk, order_reference, return_url=None):
        """Create a charge.

        Under the low-value exemption threshold this settles in one round trip
        and returns a captured charge. Above it, since 2025-09-26, the bank
        answers 402 with a 3-D Secure challenge instead and the result arrives
        later on a webhook -- see ScaRequired and ADR-0003.
        """
        body = {
            "amount": amount_czk,
            "currency": settings.currency,
            "reference": order_reference,
        }
        if return_url:
            body["return_url"] = return_url

        response = self._request("POST", CHARGES_PATH, _json(body))

        if response.status_code == 402:
            payload = response.json()
            if payload.get("status") == "sca_required":
                raise ScaRequired(
                    challenge_id=payload["challenge_id"],
                    challenge_url=payload["challenge_url"],
                    expires_in=payload.get("expires_in", 600),
                )
        if response.status_code >= 400:
            raise BankError(f"charge failed: {response.status_code} {response.text}")

        return response.json()

    def get_charge(self, charge_id):
        """Current state of a charge.

        Needed by the reconciliation job: abandoned challenges never produce a
        terminal webhook, so polling is the only way those payments ever close.
        Job is not written yet -- PAY-3.
        """
        response = self._request("GET", f"{CHARGES_PATH}/{charge_id}")
        if response.status_code >= 400:
            raise BankError(f"charge lookup failed: {response.status_code}")
        return response.json()

    def refund(self, charge_id, amount_czk=None):
        body = {"amount": amount_czk} if amount_czk is not None else {}
        response = self._request(
            "POST", f"{CHARGES_PATH}/{charge_id}/refunds", _json(body)
        )
        if response.status_code >= 400:
            raise BankError(f"refund failed: {response.status_code} {response.text}")
        return response.json()


def _json(payload):
    import json

    return json.dumps(payload, separators=(",", ":"))
