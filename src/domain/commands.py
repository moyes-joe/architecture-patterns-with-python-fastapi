from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class Command(BaseModel):
    model_config = ConfigDict(frozen=True)


class CreateBatch(Command):
    ref: str
    sku: str
    qty: int
    eta: date | None


class ChangeBatchQuantity(Command):
    ref: str
    qty: int


class Allocate(Command):
    orderid: str
    sku: str
    qty: int
