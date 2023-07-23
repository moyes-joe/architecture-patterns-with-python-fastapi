from __future__ import annotations

from datetime import date

from src.domain.model import Batch, OrderLine


def test_allocating_to_a_batch_reduces_the_available_quantity() -> None:
    batch = Batch(
        reference="batch-001",
        sku="SMALL-TABLE",
        purchased_quantity=20,
        eta=date.today(),
    )
    line = OrderLine(orderid="order-ref", sku="SMALL-TABLE", qty=2)

    batch.allocate(line)

    assert batch.available_quantity == 18


def make_batch_and_line(sku, batch_qty, line_qty) -> tuple[Batch, OrderLine]:
    return (
        Batch(
            reference="batch-001",
            sku=sku,
            purchased_quantity=batch_qty,
            eta=date.today(),
        ),
        OrderLine(orderid="order-123", sku=sku, qty=line_qty),
    )


def test_can_allocate_if_available_greater_than_required() -> None:
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert large_batch.can_allocate(line=small_line)


def test_cannot_allocate_if_available_smaller_than_required() -> None:
    small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
    assert small_batch.can_allocate(line=large_line) is False


def test_can_allocate_if_available_equal_to_required() -> None:
    batch, line = make_batch_and_line("ELEGANT-LAMP", 2, 2)
    assert batch.can_allocate(line=line)


def test_cannot_allocate_if_skus_do_not_match() -> None:
    batch = Batch(
        reference="batch-001",
        sku="UNCOMFORTABLE-CHAIR",
        purchased_quantity=100,
        eta=None,
    )
    different_sku_line = OrderLine(orderid="order-123", sku="EXPENSIVE-TOASTER", qty=10)
    assert batch.can_allocate(line=different_sku_line) is False


def test_allocation_is_idempotent() -> None:
    batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line=line)
    batch.allocate(line=line)
    assert batch.available_quantity == 18
