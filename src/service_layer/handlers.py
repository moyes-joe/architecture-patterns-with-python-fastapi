from __future__ import annotations

from typing import TYPE_CHECKING

from src.adapters import email, redis_event_publisher
from src.domain import commands, events, model
from src.domain.model import OrderLine

if TYPE_CHECKING:
    from . import unit_of_work


class InvalidSku(Exception):
    pass


class InvalidRef(Exception):
    pass


def add_batch(
    cmd: commands.CreateBatch,
    uow: unit_of_work.UnitOfWork,
):
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = model.Product(sku=cmd.sku, batches=[])
            uow.products.add(product)
        product.batches.append(
            model.Batch(
                reference=cmd.ref, sku=cmd.sku, purchased_quantity=cmd.qty, eta=cmd.eta
            )
        )
        uow.commit()


def allocate(
    cmd: commands.Allocate,
    uow: unit_of_work.UnitOfWork,
) -> str | None:
    line = OrderLine(orderid=cmd.orderid, sku=cmd.sku, qty=cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def change_batch_quantity(
    cmd: commands.ChangeBatchQuantity,
    uow: unit_of_work.UnitOfWork,
) -> None:
    print("handling command to change batch quantity", cmd)
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        if product is None:
            raise InvalidRef(f"Invalid sku {cmd.ref}")
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    uow: unit_of_work.UnitOfWork,
):
    email.send(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def publish_allocated_event(
    event: events.Allocated,
    uow: unit_of_work.UnitOfWork,
):
    redis_event_publisher.publish("line_allocated", event)
