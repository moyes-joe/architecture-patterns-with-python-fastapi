# pylint: disable=broad-except
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


def test_uow_can_retrieve_a_batch_and_allocate_to_it(
    session_factory: Callable[[], Session]
) -> None:
    session = session_factory()
    insert_batch(
        session=session, ref="batch1", sku="HIPSTER-WORKBENCH", qty=100, eta=None
    )
    session.commit()
    new_session = session_factory()
    uow = unit_of_work.SqlAlchemyUnitOfWork(session=new_session)
    with uow:
        product = uow.products.get(sku="HIPSTER-WORKBENCH")
        line = model.OrderLine(orderid="o1", sku="HIPSTER-WORKBENCH", qty=10)
        product.allocate(line)
        uow.commit()

    batchref = get_allocated_batch_ref(
        session=session, orderid="o1", sku="HIPSTER-WORKBENCH"
    )
    assert batchref == "batch1"


def test_rolls_back_uncommitted_work_by_default(
    session_factory: Callable[[], Session]
) -> None:
    uow = unit_of_work.SqlAlchemyUnitOfWork(session=session_factory())
    with uow:
        insert_batch(
            session=uow.session, ref="batch1", sku="MEDIUM-PLINTH", qty=100, eta=None
        )

    new_session = session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def test_rolls_back_on_error(session_factory: Callable[[], Session]):
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session=session_factory())
    with pytest.raises(MyException):
        with uow:
            insert_batch(uow.session, "batch1", "LARGE-FORK", 100, None)
            raise MyException()

    new_session = session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


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


# FIXME: Replace session_factory with postgres_session_factory
def test_concurrent_updates_to_version_are_not_allowed(
    session_factory: Callable[[], Session]
):
    sku, batch = random_sku(), random_batchref()
    session = session_factory()
    insert_batch(session, batch, sku, 100, eta=None, product_version=1)
    session.commit()

    order1, order2 = random_orderid("1"), random_orderid("2")
    exceptions: list[Exception] = []
    try_to_allocate_order1 = lambda: try_to_allocate(
        session=session, orderid=order1, sku=sku, exceptions=exceptions
    )
    try_to_allocate_order2 = lambda: try_to_allocate(
        session=session, orderid=order2, sku=sku, exceptions=exceptions
    )
    thread1 = threading.Thread(target=try_to_allocate_order1)
    thread2 = threading.Thread(target=try_to_allocate_order2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    [[version]] = session.execute(
        text("SELECT version_number FROM products WHERE sku=:sku"),
        dict(sku=sku),
    )
    assert version == 2
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(exception)

    orders = session.execute(
        text(
            "SELECT orderid FROM allocations"
            " JOIN batches ON allocations.batch_id = batches.id"
            " JOIN order_lines ON allocations.orderline_id = order_lines.id"
            " WHERE order_lines.sku=:sku"
        ),
        dict(sku=sku),
    )
    assert orders.rowcount == 1
    new_session = session_factory()
    with unit_of_work.SqlAlchemyUnitOfWork(new_session) as uow:
        uow.session.execute(text("select 1"))
