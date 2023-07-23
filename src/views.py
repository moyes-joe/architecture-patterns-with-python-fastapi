from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from src.domain import events

if TYPE_CHECKING:
    from src.service_layer import unit_of_work


def allocations(
    orderid: str, uow: unit_of_work.UnitOfWork
) -> list[events.AllocationsViewed]:
    with uow:
        results = uow.execute(
            text("SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid"),
            dict(orderid=orderid),
        )
    return [
        events.AllocationsViewed(orderid=orderid, sku=r[0], batchref=r[1])
        for r in results
    ]
