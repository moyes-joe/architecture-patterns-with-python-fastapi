from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Self

import pytest

from src import bootstrap
from src.adapters import notifications, repository, unit_of_work_strategy
from src.domain import commands, model
from src.service_layer import handlers, messagebus


class FakeRepository(repository.Repository[model.Product]):
    def __init__(self, products: list[model.Product]) -> None:
        self._products = set(products)

    def add(self, product: model.Product) -> model.Product:
        self._products.add(product)
        return product

    def get(self, sku: str) -> model.Product | None:
        return next((b for b in self._products if b.sku == sku), None)

    def get_by_batchref(self, batchref: str) -> model.Product | None:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


class FakeUnitOfWorkStrategy(unit_of_work_strategy.UnitOfWorkStrategy):
    def __init__(self) -> None:
        self.products = repository.TrackingRepository(FakeRepository([]))
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: tuple, **kwargs: dict) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def execute(self, *args, **kwargs) -> Any:
        pass


class FakeNotifications(notifications.NotificationsProtocol):
    def __init__(self) -> None:
        self.sent: dict[str, list[str]] = defaultdict(list)

    def send(self, destination, message) -> None:
        self.sent[destination].append(message)


def bootstrap_test_app() -> messagebus.MessageBus:
    return bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOfWorkStrategy(),
        notifications=FakeNotifications(),
        publish=lambda *args: None,
    )


class TestAddBatch:
    def test_for_new_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(
            message=commands.CreateBatch(
                ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None
            )
        )
        assert bus.uow.products.get(sku="CRUNCHY-ARMCHAIR") is not None
        assert bus.uow._uow.committed  # type: ignore[attr-defined]

    def test_for_existing_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch(ref="b1", sku="GARISH-RUG", qty=100, eta=None))
        bus.handle(commands.CreateBatch(ref="b2", sku="GARISH-RUG", qty=99, eta=None))
        assert "b2" in [b.reference for b in bus.uow.products.get("GARISH-RUG").batches]  # type: ignore[union-attr]


class TestAllocate:
    def test_allocates(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(
            commands.CreateBatch(
                ref="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None
            )
        )
        bus.handle(commands.Allocate(orderid="o1", sku="COMPLICATED-LAMP", qty=10))
        product = bus.uow.products.get("COMPLICATED-LAMP")
        assert product is not None
        [batch] = product.batches
        assert batch.available_quantity == 90

    def test_errors_for_invalid_sku(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch(ref="b1", sku="AREALSKU", qty=100, eta=None))

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            bus.handle(commands.Allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10))

    def test_commits(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(
            commands.CreateBatch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None)
        )
        assert bus.uow._uow.committed  # type: ignore[attr-defined]

    def test_sends_email_on_out_of_stock_error(self) -> None:
        fake_notifs = FakeNotifications()
        bus = bootstrap.bootstrap(
            start_orm=False,
            uow=FakeUnitOfWorkStrategy(),
            notifications=fake_notifs,
            publish=lambda *args: None,
        )
        bus.handle(
            commands.CreateBatch(ref="b1", sku="POPULAR-CURTAINS", qty=9, eta=None)
        )
        bus.handle(commands.Allocate(orderid="o1", sku="POPULAR-CURTAINS", qty=10))
        assert fake_notifs.sent["stock@made.com"] == [
            "Out of stock for POPULAR-CURTAINS",
        ]


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(
            commands.CreateBatch(ref="batch1", sku="ADORABLE-SETTEE", qty=100, eta=None)
        )
        product = bus.uow.products.get("ADORABLE-SETTEE")
        assert product is not None
        [batch] = product.batches
        assert batch.available_quantity == 100

        bus.handle(commands.ChangeBatchQuantity(ref="batch1", qty=50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self) -> None:
        bus = bootstrap_test_app()
        history = [
            commands.CreateBatch(
                ref="batch1", sku="INDIFFERENT-TABLE", qty=50, eta=None
            ),
            commands.CreateBatch(
                ref="batch2", sku="INDIFFERENT-TABLE", qty=50, eta=date.today()
            ),
            commands.Allocate(orderid="order1", sku="INDIFFERENT-TABLE", qty=20),
            commands.Allocate(orderid="order2", sku="INDIFFERENT-TABLE", qty=20),
        ]
        for msg in history:
            bus.handle(msg)
        product = bus.uow.products.get("INDIFFERENT-TABLE")
        assert product is not None
        [batch1, batch2] = product.batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(commands.ChangeBatchQuantity(ref="batch1", qty=25))

        # order1 or order2 will be deallocated, so we'll have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be reallocated to the next batch
        assert batch2.available_quantity == 30
