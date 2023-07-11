from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)


class BatchCreated(Event):
    ref: str
    sku: str
    qty: int
    eta: date | None


class BatchQuantityChanged(Event):
    ref: str
    qty: int


class AllocationRequired(Event):
    orderid: str
    sku: str
    qty: int


class OutOfStock(Event):
    sku: str
