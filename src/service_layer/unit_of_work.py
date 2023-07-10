from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm.session import Session

from src.adapters import repository


class UnitOfWorkProtocol(Protocol):
    products: repository.RepositoryProtocol

    def __enter__(self) -> UnitOfWorkProtocol:
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class SqlAlchemyUnitOfWork(UnitOfWorkProtocol):
    products: repository.SqlAlchemyRepository  # move to init?

    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> UnitOfWorkProtocol:
        self.products = repository.SqlAlchemyRepository(self.session)  # move to init?
        return super().__enter__()

    def __exit__(self, *args) -> None:
        self.rollback()
        # super().__exit__(*args)  # don't call methods on protocol
        # Session is closed insession factory
        # self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
