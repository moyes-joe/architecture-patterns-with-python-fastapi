from __future__ import annotations

from typing import TYPE_CHECKING

from src.adapters import email
from src.domain import events, model
from src.domain.model import OrderLine

if TYPE_CHECKING:
    from . import unit_of_work


class InvalidSku(Exception):
    pass


class InvalidRef(Exception):
    pass


def add_batch(
    event: events.BatchCreated,
    uow: unit_of_work.UnitOfWork,
):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(sku=event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(
            model.Batch(
                reference=event.ref,
                sku=event.sku,
                purchased_quantity=event.qty,
                eta=event.eta,
            )
        )
        uow.commit()


def allocate(
    event: events.AllocationRequired,
    uow: unit_of_work.UnitOfWork,
) -> str | None:
    line = OrderLine(orderid=event.orderid, sku=event.sku, qty=event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def change_batch_quantity(
    event: events.BatchQuantityChanged,
    uow: unit_of_work.UnitOfWork,
):
    with uow:
        product = uow.products.get_by_batchref(batchref=event.ref)
        if product is None:
            raise InvalidRef(f"Invalid batch ref {event.ref}")
        product.change_batch_quantity(ref=event.ref, qty=event.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    uow: unit_of_work.UnitOfWork,
):
    email.send(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )
