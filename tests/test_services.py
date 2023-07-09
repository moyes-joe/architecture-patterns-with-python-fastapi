from __future__ import annotations

import pytest

from src import model, repository, services, session


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches: list[model.Batch]):
        self._batches = set(batches)

    def add(self, batch: model.Batch) -> model.Batch:
        self._batches.add(batch)
        return batch

    def get(self, reference: str) -> model.Batch:
        return next(b for b in self._batches if b.reference == reference)

    def list(self) -> list[model.Batch]:
        return list(self._batches)


class FakeSession(session.SessionProtocol):
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    line = model.OrderLine(orderid="o1", sku="COMPLICATED-LAMP", qty=10)
    batch = model.Batch(
        reference="b1", sku="COMPLICATED-LAMP", purchased_quantity=100, eta=None
    )
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine(orderid="o1", sku="NONEXISTENTSKU", qty=10)
    batch = model.Batch(
        reference="b1", sku="AREALSKU", purchased_quantity=100, eta=None
    )
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine(orderid="o1", sku="OMINOUS-MIRROR", qty=10)
    batch = model.Batch(
        reference="b1", sku="OMINOUS-MIRROR", purchased_quantity=100, eta=None
    )
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed is True
