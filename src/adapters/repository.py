from __future__ import annotations

import abc
from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain import model

ModelType = TypeVar("ModelType")


class RepositoryProtocol(Protocol[ModelType]):
    def add(self, batch: ModelType) -> ModelType:
        ...

    @abc.abstractmethod
    def get(self, reference) -> ModelType:
        ...

    @abc.abstractmethod
    def list(self) -> list[ModelType]:
        ...


# TODO: Make generic
class SqlAlchemyRepository(RepositoryProtocol):
    def __init__(self, session: Session):
        self.session = session

    def add(self, batch) -> model.Batch:
        self.session.add(batch)
        return batch

    def get(self, reference) -> model.Batch:
        query = select(model.Batch).where(model.Batch.reference == reference)
        [db_model] = self.session.execute(query).one()
        return db_model

    def list(self) -> list[model.Batch]:
        return self.session.query(model.Batch).all()
