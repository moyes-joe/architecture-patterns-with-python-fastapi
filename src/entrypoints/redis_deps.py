from __future__ import annotations

from collections.abc import Generator
from typing import Protocol

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


def get_engine(url: str = config.POSTGRES_URI) -> Engine:  # noqa: B008
    return create_engine(url, isolation_level="REPEATABLE READ")


def get_session() -> Generator[Session, None, None]:
    engine: Engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_repository() -> repository.Repository[model.Product]:
    session = next(get_session())
    return repository.SqlAlchemyRepository(session)


def get_repository() -> repository.TrackingRepository:
    return repository.TrackingRepository(repo=_get_repository())


def _get_unit_of_work() -> unit_of_work.UnitOfWorkStrategy:
    session: Session = next(get_session())
    repo: repository.Repository[model.Product] = get_repository()
    return unit_of_work.SqlAlchemyUnitOfWork(session=session, repo=repo)


def get_unit_of_work() -> unit_of_work.UnitOfWork:
    uow: unit_of_work.UnitOfWorkStrategy = _get_unit_of_work()
    return unit_of_work.UnitOfWork(uow=uow)
