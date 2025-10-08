"""Checkout screens. PAY-5 -- IN PROGRESS.

Estimated on two outcomes: the customer paid, or they did not. Since ADR-0003
there is a third, and it is the common one -- we sent them to the bank and do
not know yet.
"""

SCREENS = {
    "checkout": "checkout.html",
    "success": "payment_success.html",
    "failure": "payment_failure.html",
    # TODO(PAY-5): the customer has to be sent out to the bank's 3-D Secure page
    # and come back. Not in the estimate -- there was no redirect in the flow
    # this was scoped against.
    "challenge_redirect": None,
    # TODO(PAY-5): and the return can land BEFORE the webhook does, so this
    # cannot assume the payment is resolved. It has to poll or show a pending
    # state. Contract with PAY-3 not settled -- see the PAY-5 pull request.
    "payment_pending": None,
}


def render_payment_start(response):
    """What to show after POST /orders/{id}/pay."""
    if response.get("challenge_url"):
        raise NotImplementedError(
            "challenge redirect screen not built -- PAY-5, blocked on PAY-3"
        )
    return SCREENS["success"] if response["state"] == "captured" else SCREENS["failure"]
