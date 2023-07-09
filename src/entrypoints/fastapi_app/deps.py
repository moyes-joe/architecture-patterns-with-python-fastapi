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


def get_engine() -> Engine:
    return create_engine(config.POSTGRES_URI, pool_pre_ping=True)


class SessionProtocol(Protocol):
    def commit(self) -> None:
        ...


def get_session(
    engine: Engine = Depends(get_engine),  # noqa: B008
) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_unit_of_work(
    session: Session = Depends(get_session),  # noqa: B008
) -> unit_of_work.UnitOfWorkProtocol:
    return unit_of_work.SqlAlchemyUnitOfWork(session=session)


def get_repository(
    session: Session = Depends(get_session),  # noqa: B008
) -> repository.RepositoryProtocol[model.Batch]:
    return repository.SqlAlchemyRepository(session)
