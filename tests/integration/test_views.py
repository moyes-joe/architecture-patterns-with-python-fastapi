from __future__ import annotations

from datetime import date

from src import views
from src.domain import commands, events
from src.service_layer import messagebus, unit_of_work

today = date.today()


def test_allocations_view(uow: unit_of_work.UnitOfWork) -> None:
    messagebus.handle(
        commands.CreateBatch(ref="sku1batch", sku="sku1", qty=50, eta=None), uow
    )
    messagebus.handle(
        commands.CreateBatch(ref="sku2batch", sku="sku2", qty=50, eta=today), uow
    )
    messagebus.handle(commands.Allocate(orderid="order1", sku="sku1", qty=20), uow)
    messagebus.handle(commands.Allocate(orderid="order1", sku="sku2", qty=20), uow)
    # add a spurious batch and order to make sure we're getting the right ones
    messagebus.handle(
        commands.CreateBatch(ref="sku1batch-later", sku="sku1", qty=50, eta=today), uow
    )
    messagebus.handle(commands.Allocate(orderid="otherorder", sku="sku1", qty=30), uow)
    messagebus.handle(commands.Allocate(orderid="otherorder", sku="sku2", qty=10), uow)

    allocations = views.allocations("order1", uow)
    assert allocations == [
        events.AllocationsViewed(orderid="order1", sku="sku1", batchref="sku1batch"),
        events.AllocationsViewed(orderid="order1", sku="sku2", batchref="sku2batch"),
    ]


def test_deallocation(uow: unit_of_work.UnitOfWork) -> None:
    messagebus.handle(commands.CreateBatch(ref="b1", sku="sku1", qty=50, eta=None), uow)
    messagebus.handle(
        commands.CreateBatch(ref="b2", sku="sku1", qty=50, eta=today), uow
    )
    messagebus.handle(commands.Allocate(orderid="o1", sku="sku1", qty=40), uow)
    messagebus.handle(commands.ChangeBatchQuantity(ref="b1", qty=10), uow)

    assert views.allocations("o1", uow) == [
        events.AllocationsViewed(orderid="o1", sku="sku1", batchref="b2"),
    ]
