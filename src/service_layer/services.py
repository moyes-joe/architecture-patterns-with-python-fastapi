from __future__ import annotations

from datetime import date

from src.domain import model

from .unit_of_work import UnitOfWorkProtocol


class InvalidSku(Exception):
    pass


def is_valid_sku(sku: str, batches: list[model.Batch]):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: date | None,
    uow: UnitOfWorkProtocol,
) -> None:
    with uow:
        batch = model.Batch(reference=ref, sku=sku, purchased_quantity=qty, eta=eta)
        uow.batches.add(batch)
        uow.commit()


def allocate(
    orderid: str,
    sku: str,
    qty: int,
    uow: UnitOfWorkProtocol,
) -> str:
    with uow:
        line = model.OrderLine(orderid=orderid, sku=sku, qty=qty)
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = model.allocate(line, batches)
        uow.commit()
    return batchref
