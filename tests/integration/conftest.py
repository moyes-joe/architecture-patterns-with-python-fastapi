from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from sqlalchemy.orm import Session

from src.adapters import repository
from src.service_layer import unit_of_work


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
