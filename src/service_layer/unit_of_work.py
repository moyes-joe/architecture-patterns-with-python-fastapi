from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm.session import Session

from src.adapters import repository


class UnitOfWorkProtocol(Protocol):
    batches: repository.RepositoryProtocol

    def __enter__(self) -> UnitOfWorkProtocol:
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class SqlAlchemyUnitOfWork(UnitOfWorkProtocol):
    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> UnitOfWorkProtocol:
        self.batches = repository.SqlAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args) -> None:
        super().__exit__(*args)
        # Session is closed insession factory
        # self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
