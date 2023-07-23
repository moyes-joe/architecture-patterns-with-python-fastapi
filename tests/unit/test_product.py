from __future__ import annotations

from datetime import date, timedelta

from src.domain import events
from src.domain.model import Batch, OrderLine, Product

today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_current_stock_batches_to_shipments() -> None:
    in_stock_batch = Batch(
        reference="in-stock-batch", sku="RETRO-CLOCK", purchased_quantity=100, eta=None
    )
    shipment_batch = Batch(
        reference="shipment-batch",
        sku="RETRO-CLOCK",
        purchased_quantity=100,
        eta=tomorrow,
    )
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine(orderid="oref", sku="RETRO-CLOCK", qty=10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    earliest = Batch(
        reference="speedy-batch",
        sku="MINIMALIST-SPOON",
        purchased_quantity=100,
        eta=today,
    )
    medium = Batch(
        reference="normal-batch",
        sku="MINIMALIST-SPOON",
        purchased_quantity=100,
        eta=tomorrow,
    )
    latest = Batch(
        reference="slow-batch",
        sku="MINIMALIST-SPOON",
        purchased_quantity=100,
        eta=later,
    )
    product = Product(sku="MINIMALIST-SPOON", batches=[medium, earliest, latest])
    line = OrderLine(orderid="order1", sku="MINIMALIST-SPOON", qty=10)

    product.allocate(line)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref() -> None:
    in_stock_batch = Batch(
        reference="in-stock-batch-ref",
        sku="HIGHBROW-POSTER",
        purchased_quantity=100,
        eta=None,
    )
    shipment_batch = Batch(
        reference="shipment-batch-ref",
        sku="HIGHBROW-POSTER",
        purchased_quantity=100,
        eta=tomorrow,
    )
    line = OrderLine(orderid="oref", sku="HIGHBROW-POSTER", qty=10)
    product = Product(sku="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch])
    allocation = product.allocate(line)
    assert allocation == events.AllocatedBatchRef(batchref=in_stock_batch.reference)


def test_raises_out_of_stock_exception_if_cannot_allocate() -> None:
    batch = Batch(
        reference="batch1", sku="SMALL-FORK", purchased_quantity=10, eta=today
    )
    product = Product(sku="SMALL-FORK", batches=[batch])
    product.allocate(OrderLine(orderid="order1", sku="SMALL-FORK", qty=10))

    allocation = product.allocate(OrderLine(orderid="order2", sku="SMALL-FORK", qty=1))
    assert product.messages[-1] == events.OutOfStock(sku="SMALL-FORK")
    assert allocation is None


def test_increments_version_number() -> None:
    line = OrderLine(orderid="oref", sku="SCANDI-PEN", qty=10)
    product = Product(
        sku="SCANDI-PEN",
        batches=[
            Batch(reference="b1", sku="SCANDI-PEN", purchased_quantity=100, eta=None)
        ],
    )
    product.version_number = 7
    product.allocate(line)
    assert product.version_number == 8
