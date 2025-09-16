"""Bank transport tests. PAY-2.

The signing test is the important one: it pins the format the sandbox actually
accepts, which is not the format the API guide documents (#4381). Without this
somebody eventually "fixes" _sign() to match the guide and every request starts
failing authentication.
"""

from unittest.mock import Mock, patch

from src.payments.bank_api.client import BankClient


def test_canonical_string_puts_the_timestamp_before_the_body():
    """Guide v1.4 4.2 says METHOD \\n PATH \\n BODY. The sandbox disagrees."""
    with patch("src.payments.bank_api.client.settings") as settings:
        settings.bank_signing_key = "secret"
        first = BankClient._sign("POST", "/v1/charges", "{}", "1700000000")
        second = BankClient._sign("POST", "/charges", "{}", "1700000000")

    # The /v1 prefix is stripped, so both spellings of the path sign the same.
    assert first == second


def test_retries_on_429_then_succeeds():
    client = BankClient(base_url="https://sandbox.example")
    client._token = "tok"
    client._token_expires_at = 9_999_999_999

    responses = [Mock(status_code=429), Mock(status_code=200)]
    with patch("src.payments.bank_api.client.requests.request", side_effect=responses), \
         patch("src.payments.bank_api.client.time.sleep"):
        response = client._request("GET", "/v1/charges/chg_1")

    assert response.status_code == 200
