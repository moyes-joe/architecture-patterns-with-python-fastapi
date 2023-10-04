from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from sqlalchemy.orm import Session

from src.adapters import unit_of_work_strategy
from src.service_layer import unit_of_work


@pytest.fixture
def uow_factory(
    session: Session,
) -> Generator[Callable[[], unit_of_work.UnitOfWork], None, None]:
    def get_uow() -> unit_of_work.UnitOfWork:
        sql_alchemy_uow = unit_of_work_strategy.SqlAlchemyUnitOfWork(
            session_factory=lambda: session
        )
        return unit_of_work.UnitOfWork(uow=sql_alchemy_uow)

    yield get_uow


@pytest.fixture
def uow(uow_factory: Callable[[], unit_of_work.UnitOfWork]) -> unit_of_work.UnitOfWork:
    return uow_factory()
