from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class OrderLineCreate(BaseModel):
    orderid: str
    sku: str
    qty: int


class BatchRef(BaseModel):
    batchref: str


class BatchCreate(BaseModel):
    sku: str
    qty: int
    eta: str
    reference: str

    def eta_date(self) -> date:
        return datetime.fromisoformat(self.eta).date()
