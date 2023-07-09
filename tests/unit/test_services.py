import pytest

from src.adapters import repository, session
from src.service_layer import services


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeSession(session.SessionProtocol):
    committed = False

    def commit(self):
        self.committed = True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch(
        ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None, repo=repo, session=session
    )
    assert repo.get("b1") is not None
    assert session.committed


def test_allocate_returns_allocation():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch(
        ref="batch1",
        sku="COMPLICATED-LAMP",
        qty=100,
        eta=None,
        repo=repo,
        session=session,
    )
    result = services.allocate(
        orderid="o1", sku="COMPLICATED-LAMP", qty=10, repo=repo, session=session
    )
    assert result == "batch1"


def test_allocate_errors_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch(
        ref="b1", sku="AREALSKU", qty=100, eta=None, repo=repo, session=session
    )

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        services.allocate(
            orderid="o1", sku="NONEXISTENTSKU", qty=10, repo=repo, session=FakeSession()
        )


def test_commits():
    repo, session = FakeRepository([]), FakeSession()
    session = FakeSession()
    services.add_batch(
        ref="b1", sku="OMINOUS-MIRROR", qty=100, eta=None, repo=repo, session=session
    )
    services.allocate(
        orderid="o1", sku="OMINOUS-MIRROR", qty=10, repo=repo, session=session
    )
    assert session.committed is True
