from __future__ import annotations

from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain import model

from . import orm

ModelType = TypeVar("ModelType")


class Repository(Protocol[ModelType]):
    def add(self, product: ModelType) -> ModelType:
        ...

    def get(self, sku: str) -> ModelType | None:
        ...

    def get_by_batchref(self, batchref: str) -> ModelType | None:
        ...


class SqlAlchemyRepository(Repository[model.Product]):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, product: model.Product) -> model.Product:
        self.session.add(product)
        return product

    def get(self, sku: str) -> model.Product | None:
        query = select(model.Product).where(model.Product.sku == sku)  # type: ignore[arg-type]
        return self.session.scalar(query)

    def get_by_batchref(self, batchref: str) -> model.Product | None:
        query = (
            select(model.Product)
            .join(model.Batch)
            .where(orm.batches.c.reference == batchref)
        )
        return self.session.scalar(query)


class TrackingRepository(Repository[model.Product]):
    seen: set[model.Product]

    def __init__(self, repo: Repository[model.Product]) -> None:
        self.seen: set[model.Product] = set()
        self._repo = repo

    def add(self, product: model.Product) -> model.Product:
        self._repo.add(product)
        self.seen.add(product)
        return product

    def get(self, sku) -> model.Product | None:
        product = self._repo.get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref) -> model.Product | None:
        product = self._repo.get_by_batchref(batchref)
        if product:
            self.seen.add(product)
        return product
