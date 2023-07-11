from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)


class OutOfStock(Event):
    sku: str
