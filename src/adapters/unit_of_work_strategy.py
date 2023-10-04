from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, Self

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters import repository
from src.config import config


class UnitOfWorkStrategy(Protocol):
    products: repository.Repository

    def __enter__(self) -> Self:
        ...

    def __exit__(self, *args) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def execute(self, *args, **kwargs) -> Any:
        ...


class SqlAlchemyUnitOfWork(UnitOfWorkStrategy):
    session: Session
    products: repository.Repository

    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self.session_factory = session_factory or get_session

    def __enter__(self) -> Self:
        self.session = self.session_factory()
        self.products = repository.SqlAlchemyRepository(self.session)
        return self

    def __exit__(self, *args) -> None:
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def execute(self, *args, **kwargs) -> Any:
        return self.session.execute(*args, **kwargs)


def get_engine(url: str | None = None) -> Engine:
    url = url or config.POSTGRES_URI
    return create_engine(url, isolation_level="REPEATABLE READ")


def get_session(
    engine: Engine | None = None,
) -> Session:
    engine = engine or get_engine()
    return sessionmaker(bind=engine)()
