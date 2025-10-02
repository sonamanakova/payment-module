"""HTTP surface. PAY-1 (health), PAY-4 (orders), PAY-3 (payments, webhook)."""

from fastapi import FastAPI, Header, Request

from .gateway.payment import PaymentGateway
from .gateway.repository import InMemoryPaymentRepository
from .gateway.webhooks import WebhookHandler
from .orders.models import Order, OrderStatus

app = FastAPI(title="Payment module", version="0.4.0")

repository = InMemoryPaymentRepository()
gateway = PaymentGateway(repository)
webhooks = WebhookHandler(repository)
orders: dict[str, Order] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders/{order_id}/pay")
def pay(order_id: str, return_url: str):
    """Start payment for an order. PAY-4 calling into PAY-3.

    This used to answer "paid" or "not paid". It cannot any more -- above the
    exemption threshold the customer has to authenticate at the bank first, so
    the honest answer is "go here and we will find out later". PAY-5 has to
    render that redirect, which is not in its estimate either.
    """
    order = orders[order_id]
    payment = gateway.authorise(order_id, order.amount_czk, return_url)
    order.transition_to(OrderStatus.AWAITING_PAYMENT)
    order.payment_id = payment.payment_id

    return {
        "payment_id": payment.payment_id,
        "state": payment.state.value,
        "challenge_url": payment.challenge_url,
    }


@app.post("/webhooks/bank")
async def bank_webhook(request: Request, x_signature: str = Header(default="")):
    """Where the bank tells us how a challenge ended. PAY-3, added by ADR-0003.

    The first inbound endpoint this project has ever had. It needs to be
    publicly reachable in every environment including local development, which
    is a deployment problem nobody scoped.
    """
    raw = await request.body()
    return webhooks.handle(raw, x_signature, await request.json())
