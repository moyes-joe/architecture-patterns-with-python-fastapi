from __future__ import annotations

import threading
import time
import traceback
from collections.abc import Callable
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.domain import model
from src.service_layer import unit_of_work

from ..random_refs import random_batchref, random_orderid, random_sku


def insert_batch(
    session: Session,
    ref: str,
    sku: str,
    qty: int,
    eta: date | None,
    product_version: int = 1,
):
    session.execute(
        text("INSERT INTO products (sku, version_number) VALUES (:sku, :version)"),
        dict(sku=sku, version=product_version),
    )
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, purchased_quantity, eta)"
            " VALUES (:ref, :sku, :qty, :eta)"
        ),
        dict(ref=ref, sku=sku, qty=qty, eta=eta),
    )


def get_allocated_batch_ref(session: Session, orderid: str, sku: str) -> str:
    [[orderlineid]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid=orderid, sku=sku),
    )
    [[batchref]] = session.execute(
        text(
            "SELECT b.reference FROM allocations JOIN batches AS b ON batch_id = b.id"
            " WHERE orderline_id=:orderlineid"
        ),
        dict(orderlineid=orderlineid),
    )
    return batchref


def try_to_allocate(
    session: Session, orderid: str, sku: str, exceptions: list[Exception]
) -> None:
    line = model.OrderLine(orderid=orderid, sku=sku, qty=10)
    try:
        with unit_of_work.SqlAlchemyUnitOfWork(session=session) as uow:
            product = uow.products.get(sku=sku)
            product.allocate(line)
            time.sleep(0.2)
            uow.commit()
    except Exception as e:
        print(traceback.format_exc())
        exceptions.append(e)


def test_uow_can_retrieve_a_batch_and_allocate_to_it(session: Session) -> None:
    insert_batch(
        session=session, ref="batch1", sku="HIPSTER-WORKBENCH", qty=100, eta=None
    )
    session.commit()

    uow = unit_of_work.SqlAlchemyUnitOfWork(session=session)
    with uow:
        product = uow.products.get(sku="HIPSTER-WORKBENCH")
        line = model.OrderLine(orderid="o1", sku="HIPSTER-WORKBENCH", qty=10)
        product.allocate(line)
        uow.commit()

    batchref = get_allocated_batch_ref(
        session=session, orderid="o1", sku="HIPSTER-WORKBENCH"
    )
    assert batchref == "batch1"


def test_rolls_back_uncommitted_work_by_default(session: Session) -> None:
    uow = unit_of_work.SqlAlchemyUnitOfWork(session=session)
    with uow:
        insert_batch(
            session=uow.session, ref="batch1", sku="MEDIUM-PLINTH", qty=100, eta=None
        )

    new_session = session
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def test_rolls_back_on_error(session: Session) -> None:
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session=session)
    with pytest.raises(MyException):
        with uow:
            insert_batch(
                session=uow.session, ref="batch1", sku="LARGE-FORK", qty=100, eta=None
            )
            raise MyException()

    rows = list(session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def emmulate_database_race(sku, session_1, session_2, order1, order2, exceptions):
    line = model.OrderLine(orderid=order1, sku=sku, qty=10)
    line2 = model.OrderLine(orderid=order2, sku=sku, qty=10)
    try:
        with unit_of_work.SqlAlchemyUnitOfWork(session=session_1) as uow:
            with unit_of_work.SqlAlchemyUnitOfWork(session=session_2) as uow2:
                product = uow.products.get(sku=sku)
                product2 = uow2.products.get(sku=sku)
                product.allocate(line)
                product2.allocate(line2)
                uow.commit()
                uow2.commit()
    except Exception as e:
        print(traceback.format_exc())
        exceptions.append(e)


def test_concurrent_updates_to_version_are_not_allowed(
    postgres_session_factory: Callable[[], Session]
) -> None:
    sku, batch = random_sku(), random_batchref()
    session_1 = postgres_session_factory()
    session_2 = postgres_session_factory()
    assert session_1 is not session_2

    insert_batch(session_1, batch, sku, 100, eta=None, product_version=1)
    session_1.commit()

    order1, order2 = random_orderid("1"), random_orderid("2")
    exceptions: list[Exception] = []

    emmulate_database_race(sku, session_1, session_2, order1, order2, exceptions)

    assert len(exceptions) == 1, exceptions

    # thread1 = threading.Thread(
    #     target=try_to_allocate, args=(session_1, order1, sku, exceptions)
    # )
    # thread2 = threading.Thread(
    #     target=try_to_allocate, args=(session_2, order2, sku, exceptions)
    # )
    # thread1.start()
    # thread2.start()
    # thread1.join(timeout=1.0)
    # thread2.join(timeout=1.0)

    [[version]] = session_1.execute(
        text("SELECT version_number FROM products WHERE sku=:sku"),
        dict(sku=sku),
    )

    assert len(exceptions) == 1, exceptions
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(exception)
    assert version == 2

    orders = session_1.execute(
        text(
            "SELECT orderid FROM allocations"
            " JOIN batches ON allocations.batch_id = batches.id"
            " JOIN order_lines ON allocations.orderline_id = order_lines.id"
            " WHERE order_lines.sku=:sku"
        ),
        dict(sku=sku),
    )
    assert orders.rowcount == 1
    new_session = postgres_session_factory()
    with unit_of_work.SqlAlchemyUnitOfWork(new_session) as uow:
        uow.session.execute(text("select 1"))
