from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.domain import model

if TYPE_CHECKING:
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
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku=sku, batches=[])
            uow.products.add(product)
        product.batches.append(
            model.Batch(reference=ref, sku=sku, purchased_quantity=qty, eta=eta)
        )
        uow.commit()


def allocate(
    orderid: str,
    sku: str,
    qty: int,
    uow: UnitOfWorkProtocol,
) -> str | None:
    line = model.OrderLine(orderid=orderid, sku=sku, qty=qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
    return batchref
