"""HTTP surface. PAY-1."""

from fastapi import FastAPI

app = FastAPI(title="Payment module", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}
