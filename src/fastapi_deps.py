from __future__ import annotations

from typing import Generator, Protocol

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src import model, repository
from src.config import config


def get_engine() -> Engine:
    return create_engine(config.POSTGRES_URI, pool_pre_ping=True)


class SessionProtocol(Protocol):
    def commit(self) -> None:
        ...


def get_session(engine: Engine = Depends(get_engine)) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_repository(
    session: Session = Depends(get_session),
) -> repository.AbstractRepository[model.Batch]:
    return repository.SqlAlchemyRepository(session)
