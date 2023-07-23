from __future__ import annotations

import pytest

from src.adapters import repository
from src.domain import commands, events, model
from src.service_layer import handlers, messagebus, unit_of_work


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


class FakeUnitOfWorkStrategy(
    unit_of_work.UnitOfWorkStrategy[repository.TrackingRepository]
):
    def __init__(self) -> None:
        self.products = repository.TrackingRepository(FakeRepository([]))
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class TestAddBatch:
    def test_for_new_product(self) -> None:
        uow = unit_of_work.UnitOfWork(FakeUnitOfWorkStrategy())
        messagebus.handle(
            message=commands.CreateBatch(
                ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None
            ),
            uow=uow,
        )
        assert uow.products.get(sku="CRUNCHY-ARMCHAIR") is not None
        assert uow._uow.committed  # type: ignore[union-attr]

    def test_for_existing_product(self) -> None:
        uow = unit_of_work.UnitOfWork(FakeUnitOfWorkStrategy())
        messagebus.handle(
            commands.CreateBatch(ref="b1", sku="GARISH-RUG", qty=100, eta=None), uow
        )
        messagebus.handle(
            commands.CreateBatch(ref="b2", sku="GARISH-RUG", qty=99, eta=None), uow
        )
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]  # type: ignore[union-attr]


class TestAllocate:
    def test_returns_allocation(self) -> None:
        uow = unit_of_work.UnitOfWork(FakeUnitOfWorkStrategy())
        messagebus.handle(
            commands.CreateBatch(
                ref="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None
            ),
            uow,
        )
        results = messagebus.handle(
            commands.Allocate(orderid="o1", sku="COMPLICATED-LAMP", qty=10),
            uow,
        )
        assert results.pop(0) == events.AllocatedBatchRef(batchref="batch1")

    def test_errors_for_invalid_sku(self) -> None:
        uow = unit_of_work.UnitOfWork(FakeUnitOfWorkStrategy())
        messagebus.handle(
            commands.CreateBatch(ref="b1", sku="AREALSKU", qty=100, eta=None), uow
        )

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
            messagebus.handle(
                commands.Allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10),
                uow,
            )

    def test_commits(self) -> None:
        uow = unit_of_work.UnitOfWork(FakeUnitOfWorkStrategy())
        messagebus.handle(
            commands.CreateBatch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None),
            uow,
        )
