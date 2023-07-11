from __future__ import annotations

from pydantic import BaseModel


class BatchRef(BaseModel):
    batchref: str
