from __future__ import annotations

import traceback
from collections.abc import Callable, Generator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.adapters import repository
from src.domain import model
from src.service_layer import unit_of_work

from ..random_refs import random_batchref, random_orderid, random_sku


@pytest.fixture
def uow_factory(
    session: Session,
) -> Generator[Callable[[], unit_of_work.UnitOfWork], None, None]:
    def get_uow() -> unit_of_work.UnitOfWork:
        repo = repository.SqlAlchemyRepository(session)
        tracking_repo = repository.TrackingRepository(repo)
        sql_alchemy_uow = unit_of_work.SqlAlchemyUnitOfWork(
            session=session, repo=tracking_repo
        )
        return unit_of_work.UnitOfWork(uow=sql_alchemy_uow)

    yield get_uow


@pytest.fixture
def uow(uow_factory: Callable[[], unit_of_work.UnitOfWork]) -> unit_of_work.UnitOfWork:
    return uow_factory()


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
    session: Session, uow: unit_of_work.UnitOfWork
) -> None:
    insert_batch(
        session=session, ref="batch1", sku="HIPSTER-WORKBENCH", qty=100, eta=None
    )
    session.commit()

    with uow:
        product = uow.products.get(sku="HIPSTER-WORKBENCH")
        line = model.OrderLine(orderid="o1", sku="HIPSTER-WORKBENCH", qty=10)
        product.allocate(line)  # type: ignore[union-attr]
        uow.commit()

    batchref = get_allocated_batch_ref(
        session=session, orderid="o1", sku="HIPSTER-WORKBENCH"
    )
    assert batchref == "batch1"


def test_rolls_back_uncommitted_work_by_default(
    session: Session, uow: unit_of_work.UnitOfWork
) -> None:
    with uow:
        insert_batch(
            session=session,
            ref="batch1",
            sku="MEDIUM-PLINTH",
            qty=100,
            eta=None,
        )

    new_session = session
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def test_rolls_back_on_error(session: Session, uow: unit_of_work.UnitOfWork) -> None:
    class MyException(Exception):
        pass

    with pytest.raises(MyException):
        with uow:
            insert_batch(
                session=session, ref="batch1", sku="LARGE-FORK", qty=100, eta=None
            )
            raise MyException()

    rows = list(session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def emmulate_database_race(
    sku: str, session_1: Session, session_2: Session, exceptions: list[Exception]
) -> None:
    order1, order2 = random_orderid("1"), random_orderid("2")
    line = model.OrderLine(orderid=order1, sku=sku, qty=10)
    line2 = model.OrderLine(orderid=order2, sku=sku, qty=10)
    repo = repository.SqlAlchemyRepository(session=session_1)
    tracking_repo = repository.TrackingRepository(repo)
    sql_alchemy_uow = unit_of_work.SqlAlchemyUnitOfWork(
        session=session_1, repo=tracking_repo
    )
    uow = unit_of_work.UnitOfWork(uow=sql_alchemy_uow)
    repo2 = repository.SqlAlchemyRepository(session=session_2)
    tracking_repo2 = repository.TrackingRepository(repo2)
    sql_alchemy_uow2 = unit_of_work.SqlAlchemyUnitOfWork(
        session=session_2, repo=tracking_repo2
    )
    uow2 = unit_of_work.UnitOfWork(uow=sql_alchemy_uow2)
    try:
        with uow:
            with uow2:
                product = uow.products.get(sku=sku)
                product2 = uow2.products.get(sku=sku)
                product.allocate(line)  # type: ignore[union-attr]
                product2.allocate(line2)  # type: ignore[union-attr]
                uow.commit()
                uow2.commit()
    except Exception as e:
        print(traceback.format_exc())
        exceptions.append(e)


def test_concurrent_updates_to_version_are_not_allowed(
    postgres_session_factory: Callable[[], Session]
) -> None:
    sku, ref = random_sku(), random_batchref()
    session_1 = postgres_session_factory()
    session_2 = postgres_session_factory()
    assert session_1 is not session_2

    insert_batch(
        session=session_1, ref=ref, sku=sku, qty=100, eta=None, product_version=1
    )
    session_1.commit()

    exceptions: list[Exception] = []

    emmulate_database_race(
        sku=sku, session_1=session_1, session_2=session_2, exceptions=exceptions
    )

    assert len(exceptions) == 1, exceptions

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
    assert orders.rowcount == 1  # type: ignore[attr-defined]
    new_session = postgres_session_factory()
    repo = repository.SqlAlchemyRepository(session=new_session)
    tracking_repo = repository.TrackingRepository(repo)
    sql_alchemy_uow = unit_of_work.SqlAlchemyUnitOfWork(
        session=session_1, repo=tracking_repo
    )
    uow = unit_of_work.UnitOfWork(uow=sql_alchemy_uow)
    with uow:
        uow._uow.session.execute(text("select 1"))  # type: ignore[attr-defined]
