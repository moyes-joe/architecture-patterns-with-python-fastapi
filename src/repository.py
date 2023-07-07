from __future__ import annotations

import abc

from sqlalchemy import select
from sqlalchemy.orm import Session

from src import model, orm


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
        # jsonable_encoder is used to convert pydantic model to dict but it is not compatible with sets
        # batch_dict = jsonable_encoder(batch)
        batch_dict = batch.model_dump()
        db_model = orm.Batch(**batch_dict)
        self.session.add(db_model)
        return model.Batch.model_validate(db_model, from_attributes=True)

    def get(self, reference) -> model.Batch:
        query = select(orm.Batch).where(orm.Batch.reference == reference)
        [db_model] = self.session.execute(query).one()
        return model.Batch.model_validate(db_model, from_attributes=True)

    def list(self) -> list[model.Batch]:
        db_batches = self.session.query(orm.Batch).all()
        return [
            model.Batch.model_validate(db_batch, from_attributes=True)
            for db_batch in db_batches
        ]
