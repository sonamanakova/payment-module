"""Webhook parser tests. PAY-3.

Written after 2025-10-07, when the sandbox moved to v2.1 and renamed three
fields with no announcement (#4468) and every webhook started 400ing. Both
shapes are pinned here so it cannot happen silently again.
"""

import pytest

from src.payments.gateway.webhooks import UnknownPayloadVersion, parse_event


def test_parses_v2_0_payload():
    event = parse_event(
        {
            "version": "2.0",
            "charge_id": "chg_123",
            "challenge_result": {"challenge_id": "ch_abc", "result": "Y"},
        }
    )
    assert event["outcome"] == "authenticated"
    assert event["charge_id"] == "chg_123"
    # v2.0 never carried it, which is why refunds of older payments are stuck.
    assert event["authentication_reference"] is None


def test_parses_v2_1_payload():
    event = parse_event(
        {
            "version": "2.1",
            "payment": {"id": "chg_123"},
            "authentication": {
                "challenge_id": "ch_abc",
                "status": "authenticated",
                "reference": "auth_ref_xyz",
            },
        }
    )
    assert event["outcome"] == "authenticated"
    assert event["authentication_reference"] == "auth_ref_xyz"


def test_unknown_version_raises_rather_than_guessing():
    with pytest.raises(UnknownPayloadVersion):
        parse_event({"version": "3.0"})
