from __future__ import annotations

import abc

from sqlalchemy import select
from sqlalchemy.orm import Session

from src import model


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch) -> model.Batch:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference) -> model.Batch:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
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
