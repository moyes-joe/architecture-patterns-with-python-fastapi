from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.adapters import repository
from src.service_layer import services, unit_of_work

if TYPE_CHECKING:
    from src.domain import model


class FakeRepository(repository.RepositoryProtocol):
    def __init__(self, batches: list[model.Batch]) -> None:
        self._batches = set(batches)

    def add(self, batch: model.Batch) -> None:
        self._batches.add(batch)

    def get(self, reference: str) -> model.Batch | None:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> list[model.Batch]:
        return list(self._batches)


class FakeUnitOfWork(unit_of_work.UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None, uow=uow)
    assert uow.batches.get(reference="b1") is not None
    assert uow.committed


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch(ref="batch1", sku="COMPLICATED-LAMP", qty=100, eta=None, uow=uow)
    result = services.allocate(orderid="o1", sku="COMPLICATED-LAMP", qty=10, uow=uow)
    assert result == "batch1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch(ref="b1", sku="AREALSKU", qty=100, eta=None, uow=uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(orderid="o1", sku="NONEXISTENTSKU", qty=10, uow=uow)


def test_allocate_commits():
    uow = FakeUnitOfWork()
    services.add_batch(ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None, uow=uow)
    services.allocate(orderid="o1", sku="OMINOUS-MIRROR", qty=10, uow=uow)
    assert uow.committed
