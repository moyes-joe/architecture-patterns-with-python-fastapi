from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.domain import model


def test_orderline_mapper_can_load_lines(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO order_lines (orderid, sku, qty) VALUES "
            "(:orderid1, :sku1, :qty1),"
            "(:orderid2, :sku2, :qty2),"
            "(:orderid3, :sku3, :qty3)"
        ),
        {
            "orderid1": "order1",
            "orderid2": "order1",
            "orderid3": "order2",
            "sku1": "RED-CHAIR",
            "sku2": "RED-TABLE",
            "sku3": "BLUE-LIPSTICK",
            "qty1": 12,
            "qty2": 13,
            "qty3": 14,
        },
    )
    expected = [
        model.OrderLine(orderid="order1", sku="RED-CHAIR", qty=12),
        model.OrderLine(orderid="order1", sku="RED-TABLE", qty=13),
        model.OrderLine(orderid="order2", sku="BLUE-LIPSTICK", qty=14),
    ]
    assert session.query(model.OrderLine).all() == expected


def test_orderline_mapper_can_save_lines(session: Session) -> None:
    new_line = model.OrderLine(orderid="order1", sku="DECORATIVE-WIDGET", qty=12)
    session.add(new_line)
    session.commit()

    rows = list(session.execute(text('SELECT orderid, sku, qty FROM "order_lines"')))
    assert rows == [("order1", "DECORATIVE-WIDGET", 12)]


def test_retrieving_batches(session: Session):
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            " VALUES (:ref1, :sku1, :qty1, :eta1)"
        ),
        {"ref1": "batch1", "sku1": "sku1", "qty1": 100, "eta1": None},
    )
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            " VALUES (:ref2, :sku2, :qty2, :eta2)"
        ),
        {
            "ref2": "batch2",
            "sku2": "sku2",
            "qty2": 200,
            "eta2": date(2011, 4, 11),
        },
    )
    expected = [
        model.Batch(reference="batch1", sku="sku1", purchased_quantity=100, eta=None),
        model.Batch(
            reference="batch2",
            sku="sku2",
            purchased_quantity=200,
            eta=date(2011, 4, 11),
        ),
    ]

    assert session.query(model.Batch).all() == expected


def test_saving_batches(session: Session) -> None:
    batch = model.Batch(
        reference="batch1", sku="sku1", purchased_quantity=100, eta=None
    )
    session.add(batch)
    session.commit()
    rows = session.execute(
        text('SELECT reference, sku, purchased_quantity, eta FROM "batches"')
    )
    assert list(rows) == [("batch1", "sku1", 100, None)]


def test_saving_allocations(session: Session) -> None:
    batch = model.Batch(
        reference="batch1", sku="sku1", purchased_quantity=100, eta=None
    )
    line = model.OrderLine(orderid="order1", sku="sku1", qty=10)
    batch.allocate(line=line)
    session.add(batch)
    session.commit()
    rows = list(
        session.execute(text('SELECT orderline_id, batch_id FROM "allocations"'))
    )
    assert rows == [(batch.id, line.id)]


def test_retrieving_allocations(session: Session) -> None:
    session.execute(
        text(
            "INSERT INTO order_lines (orderid, sku, qty) VALUES (:orderid, :sku, :qty)"
        ),
        {"orderid": "order1", "sku": "sku1", "qty": 12},
    )
    [[olid]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        {"orderid": "order1", "sku": "sku1"},
    )
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            " VALUES (:ref, :sku, :qty, :eta)"
        ),
        {"ref": "batch1", "sku": "sku1", "qty": 100, "eta": None},
    )
    [[bid]] = session.execute(
        text("SELECT id FROM batches WHERE reference=:ref AND sku=:sku"),
        {"ref": "batch1", "sku": "sku1"},
    )
    session.execute(
        text("INSERT INTO allocations (orderline_id, batch_id) VALUES (:olid, :bid)"),
        {"olid": olid, "bid": bid},
    )

    batch = session.query(model.Batch).one()

    # OrderLine is hashable, mypy is not aware of that
    assert batch.allocations == {model.OrderLine(orderid="order1", sku="sku1", qty=12)}  # type: ignore
