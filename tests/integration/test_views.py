from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import date
from unittest import mock

import pytest
from sqlalchemy.orm import Session, clear_mappers

from src import bootstrap, views
from src.adapters import unit_of_work_strategy
from src.domain import commands, events
from src.service_layer import messagebus

today = date.today()


@pytest.fixture
def sqlite_bus(
    session_factory: Callable[[], Session]
) -> Generator[messagebus.MessageBus, None, None]:
    clear_mappers()
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work_strategy.SqlAlchemyUnitOfWork(session_factory),
        notifications=mock.Mock(),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()


def test_allocations_view(sqlite_bus: messagebus.MessageBus) -> None:
    sqlite_bus.handle(
        commands.CreateBatch(ref="sku1batch", sku="sku1", qty=50, eta=None)
    )
    sqlite_bus.handle(
        commands.CreateBatch(ref="sku2batch", sku="sku2", qty=50, eta=today)
    )
    sqlite_bus.handle(commands.Allocate(orderid="order1", sku="sku1", qty=20))
    sqlite_bus.handle(commands.Allocate(orderid="order1", sku="sku2", qty=20))
    # add a spurious batch and order to make sure we're getting the right ones
    sqlite_bus.handle(
        commands.CreateBatch(ref="sku1batch-later", sku="sku1", qty=50, eta=today)
    )
    sqlite_bus.handle(commands.Allocate(orderid="otherorder", sku="sku1", qty=30))
    sqlite_bus.handle(commands.Allocate(orderid="otherorder", sku="sku2", qty=10))

    allocations = views.allocations("order1", sqlite_bus.uow)
    assert allocations == [
        events.AllocationsViewed(orderid="order1", sku="sku1", batchref="sku1batch"),
        events.AllocationsViewed(orderid="order1", sku="sku2", batchref="sku2batch"),
    ]


def test_deallocation(sqlite_bus: messagebus.MessageBus) -> None:
    sqlite_bus.handle(commands.CreateBatch(ref="b1", sku="sku1", qty=50, eta=None))
    sqlite_bus.handle(commands.CreateBatch(ref="b2", sku="sku1", qty=50, eta=today))
    sqlite_bus.handle(commands.Allocate(orderid="o1", sku="sku1", qty=40))
    sqlite_bus.handle(commands.ChangeBatchQuantity(ref="b1", qty=10))

    assert views.allocations("o1", sqlite_bus.uow) == [
        events.AllocationsViewed(orderid="o1", sku="sku1", batchref="b2"),
    ]
