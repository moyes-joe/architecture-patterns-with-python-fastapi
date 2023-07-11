from __future__ import annotations

from typing import Protocol, TypeVar

from sqlalchemy.orm.session import Session

from src.adapters import repository

from . import messagebus

REPO_TYPE = TypeVar("REPO_TYPE", bound=repository.RepositoryProtocol)


class UnitOfWorkProtocol(Protocol[REPO_TYPE]):
    products: REPO_TYPE

    def __enter__(self) -> UnitOfWorkProtocol:
        ...

    def __exit__(self, *args) -> None:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class SqlAlchemyUnitOfWork(UnitOfWorkProtocol):
    def __init__(self, session: Session, repo: repository.RepositoryProtocol) -> None:
        self.session = session
        self.products = repo

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        return self

    def __exit__(self, *args) -> None:
        self.rollback()
        # super().__exit__(*args)  # don't call methods on protocol
        # Session is closed insession factory
        # self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


class EventPublishingUnitOfWork(UnitOfWorkProtocol[repository.TrackingRepository]):
    def __init__(self, uow: UnitOfWorkProtocol) -> None:
        self.uow = uow
        self.products = uow.products

    def __enter__(self) -> EventPublishingUnitOfWork:
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    def commit(self) -> None:
        self.uow.commit()
        self.publish_events()

    def publish_events(self) -> None:
        for product in self.products.seen:
            while product.events:
                event = product.events.pop(0)
                messagebus.handle(event)

    def rollback(self) -> None:
        self.uow.rollback()
