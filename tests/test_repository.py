from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from src import model, repository


def insert_order_line(session: Session) -> int:
    session.execute(
        text(
            "INSERT INTO order_lines (orderid, sku, qty)"
            " VALUES (:orderid, :sku, :qty)"
        ),
        {"orderid": "order1", "sku": "GENERIC-SOFA", "qty": 12},
    )
    [[orderline_id]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        {"orderid": "order1", "sku": "GENERIC-SOFA"},
    )
    return orderline_id


def insert_batch(session: Session, reference: str) -> int:
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            ' VALUES (:reference, "GENERIC-SOFA", 100, null)'
        ),
        {"reference": reference},
    )
    [[batch_id]] = session.execute(
        text(
            'SELECT id FROM batches WHERE reference=:reference AND sku="GENERIC-SOFA"'
        ),
        {"reference": reference},
    )
    return batch_id


def insert_allocation(session: Session, orderline_id: int, batch_id: int) -> None:
    session.execute(
        text(
            "INSERT INTO allocations (orderline_id, batch_id)"
            " VALUES (:orderline_id, :batch_id)"
        ),
        {"orderline_id": orderline_id, "batch_id": batch_id},
    )


def test_repository_can_save_a_batch(session: Session) -> None:
    batch = model.Batch(
        reference="batch1",
        sku="RUSTY-SOAPDISH",
        purchased_quantity=100,
        eta=None,
        allocations=set(),
    )
    repo = repository.SqlAlchemyRepository(session=session)
    repo.add(batch)
    session.commit()

    rows = session.execute(
        text('SELECT reference, sku, purchased_quantity, eta FROM "batches"')
    )
    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]


def test_repository_can_retrieve_a_batch_with_allocations(session: Session) -> None:
    orderline_id = insert_order_line(session)
    batch1_id = insert_batch(session=session, reference="batch1")
    insert_batch(session=session, reference="batch2")
    insert_allocation(session=session, orderline_id=orderline_id, batch_id=batch1_id)
    repo = repository.SqlAlchemyRepository(session=session)
    retrieved = repo.get(reference="batch1")
    expected = model.Batch(
        reference="batch1", sku="GENERIC-SOFA", purchased_quantity=100, eta=None
    )
    assert retrieved == expected  # Batch.__eq__ only compares reference
    assert retrieved.sku == expected.sku
    assert retrieved.purchased_quantity == expected.purchased_quantity
    assert retrieved.allocations == {
        model.OrderLine(orderid="order1", sku="GENERIC-SOFA", qty=12),
    }
