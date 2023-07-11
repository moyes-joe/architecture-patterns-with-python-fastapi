from __future__ import annotations

from collections.abc import Generator
from typing import Protocol

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters import repository
from src.config import config
from src.domain import model
from src.service_layer import unit_of_work


class SessionProtocol(Protocol):
    def commit(self) -> None:
        ...


def get_engine(url: str = Depends(lambda: config.POSTGRES_URI)) -> Engine:  # noqa: B008
    return create_engine(url, isolation_level="REPEATABLE READ")


def get_session(
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_repository(
    session: Session = Depends(get_session),  # noqa: B008
) -> repository.Repository[model.Product]:
    return repository.SqlAlchemyRepository(session)


def get_repository(
    repo: repository.Repository[model.Product] = Depends(_get_repository),  # noqa: B008
) -> repository.TrackingRepository:
    return repository.TrackingRepository(repo=repo)


def _get_unit_of_work(
    session: Session = Depends(get_session),  # noqa: B008
    repo: repository.Repository[model.Product] = Depends(get_repository),  # noqa: B008
) -> unit_of_work.UnitOfWorkStrategy:
    return unit_of_work.SqlAlchemyUnitOfWork(session=session, repo=repo)


def get_unit_of_work(
    uow: unit_of_work.UnitOfWorkStrategy = Depends(_get_unit_of_work),  # noqa: B008
) -> unit_of_work.UnitOfWork:
    return unit_of_work.UnitOfWork(uow=uow)
