from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from sqlalchemy import text

from src.domain import commands, events, model
from src.domain.model import OrderLine

if TYPE_CHECKING:
    from src.adapters import notifications

    from . import unit_of_work


class InvalidSku(Exception):
    pass


class InvalidRef(Exception):
    pass


def add_batch(
    cmd: commands.CreateBatch,
    uow: unit_of_work.UnitOfWork,
) -> None:
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
) -> events.AllocatedBatchRef | None:
    line = OrderLine(orderid=cmd.orderid, sku=cmd.sku, qty=cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def reallocate(
    event: events.Deallocated,
    uow: unit_of_work.UnitOfWork,
) -> None:
    with uow:
        product = uow.products.get(sku=event.sku)
        if not product:
            raise InvalidSku(f"Invalid sku {event.sku}")
        product.messages.append(commands.Allocate(**event.model_dump()))
        uow.commit()


def change_batch_quantity(
    cmd: commands.ChangeBatchQuantity,
    uow: unit_of_work.UnitOfWork,
) -> None:
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        if product is None:
            raise InvalidRef(f"Invalid sku {cmd.ref}")
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    notifications: notifications.NotificationsProtocol,
) -> None:
    notifications.send(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def publish_allocated_event(
    event: events.Allocated,
    publish: Callable,
) -> None:
    publish("line_allocated", event)


def add_allocation_to_read_model(
    event: events.Allocated,
    uow: unit_of_work.UnitOfWork,
) -> None:
    with uow:
        uow.execute(
            text(
                """
            INSERT INTO allocations_view (orderid, sku, batchref)
            VALUES (:orderid, :sku, :batchref)
            """
            ),
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref),
        )
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated,
    uow: unit_of_work.UnitOfWork,
) -> None:
    with uow:
        uow.execute(
            text(
                """
            DELETE FROM allocations_view
            WHERE orderid = :orderid AND sku = :sku
            """
            ),
            dict(orderid=event.orderid, sku=event.sku),
        )
        uow.commit()


EVENT_HANDLERS: dict[type[events.Event], list[Callable]] = {
    events.Allocated: [
        publish_allocated_event,
        add_allocation_to_read_model,
    ],
    events.Deallocated: [
        remove_allocation_from_read_model,
        reallocate,
    ],
    events.OutOfStock: [send_out_of_stock_notification],
}
COMMAND_HANDLERS: dict[type[commands.Command], Callable] = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}
