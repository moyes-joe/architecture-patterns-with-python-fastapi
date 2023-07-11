from __future__ import annotations

from datetime import date

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
    eta: date | None
    ref: str

    def eta_date(self) -> date | None:
        if self.eta is None:
            return None
        return self.eta
