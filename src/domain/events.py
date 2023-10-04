from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)


class Allocated(Event):
    orderid: str
    sku: str
    qty: int
    batchref: str


class Deallocated(Event):
    orderid: str
    sku: str
    qty: int


class AllocatedBatchRef(Event):
    batchref: str


class AllocationsViewed(Event):
    orderid: str
    sku: str
    batchref: str


class OutOfStock(Event):
    sku: str
