from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, Self, TypeVar

from sqlalchemy.orm.session import Session

from src.adapters import repository
from src.domain import commands, events

REPO_TYPE = TypeVar("REPO_TYPE", bound=repository.Repository)


class UnitOfWorkStrategy(Protocol[REPO_TYPE]):
    products: REPO_TYPE

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

    def execute(self, *args, **kwargs) -> Any:
        ...


class SqlAlchemyUnitOfWork(UnitOfWorkStrategy[REPO_TYPE]):
    def __init__(self, session: Session, repo: REPO_TYPE) -> None:
        self.session = session
        self.products = repo  # remove from here and leave in UnitOfWork?

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def execute(self, *args, **kwargs) -> Any:
        return self.session.execute(*args, **kwargs)


class UnitOfWork:
    def __init__(self, uow: UnitOfWorkStrategy[repository.TrackingRepository]) -> None:
        self._uow = uow
        self.products = uow.products

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    def commit(self) -> None:
        self._uow.commit()

    def rollback(self) -> None:
        self._uow.rollback()

    def execute(self, *args, **kwargs) -> Any:
        return self._uow.execute(*args, **kwargs)

    def collect_new_events(self) -> Iterable[commands.Command | events.Event]:
        for product in self.products.seen:
            while product.messages:
                yield product.messages.pop(0)
