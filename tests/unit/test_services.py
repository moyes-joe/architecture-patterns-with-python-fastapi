from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from src.adapters import repository
from src.service_layer import messagebus, services, unit_of_work

if TYPE_CHECKING:
    from src.domain import model


# decouple FakeRepository and TrackingRepository?
class FakeRepository(repository.TrackingRepository):
    def __init__(self, products: list[model.Product]) -> None:
        self.seen: set[model.Product] = set()
        self._products = set(products)

    def add(self, product: model.Product) -> model.Product:
        self.seen.add(product)
        self._products.add(product)
        return product

    def get(self, sku: str) -> model.Product | None:
        product = next((b for b in self._products if b.sku == sku), None)
        if product:
            self.seen.add(product)
        return product

    def list(self) -> list[model.Product]:
        return list(self._products)


# decouple FakeUnitOfWork and EventPublisher?
class FakeUnitOfWork(unit_of_work.UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.products = FakeRepository([])
        self.committed = False

    def __enter__(self) -> FakeUnitOfWork:
        return self

    def __exit__(self, *args) -> None:
        pass

    def commit(self) -> None:
        self.committed = True
        self.publish_events()

    def publish_events(self) -> None:
        for product in self.products.seen:
            while product.events:
                event = product.events.pop(0)
                messagebus.handle(event)

    def rollback(self) -> None:
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch(ref="b1", sku="CRUNCHY-ARMCHAIR", qty=100, eta=None, uow=uow)
    assert uow.products.get(sku="CRUNCHY-ARMCHAIR") is not None
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


def test_sends_email_on_out_of_stock_error():
    uow = FakeUnitOfWork()
    services.add_batch(ref="b1", sku="POPULAR-CURTAINS", qty=9, eta=None, uow=uow)

    with mock.patch("src.adapters.email.send_mail") as mock_send_mail:
        services.allocate(orderid="o1", sku="POPULAR-CURTAINS", qty=10, uow=uow)
        assert mock_send_mail.call_args == mock.call(
            "stock@made.com",
            "Out of stock for POPULAR-CURTAINS",
        )
