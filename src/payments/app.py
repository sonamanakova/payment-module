"""HTTP surface. PAY-1 (health), PAY-4 (orders)."""

from fastapi import FastAPI

from .orders.models import Order, OrderStatus

app = FastAPI(title="Payment module", version="0.3.0")

orders: dict[str, Order] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders")
def create_order(customer_id: str, amount_czk: int):
    order = Order(order_id=_new_order_id(), customer_id=customer_id,
                  amount_czk=amount_czk)
    orders[order.order_id] = order
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return orders[order_id]


@app.post("/orders/{order_id}/pay")
def pay(order_id: str, return_url: str):
    """Start payment for an order.

    Calls into gateway (PAY-3) through the interface from ADR-0001, so this
    merges before gateway is finished.
    """
    raise NotImplementedError("waiting on PAY-3")


def _new_order_id():
    import uuid

    return f"ord_{uuid.uuid4().hex[:12]}"
