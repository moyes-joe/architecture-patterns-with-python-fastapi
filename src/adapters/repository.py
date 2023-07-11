from __future__ import annotations

from typing import Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain import model

ModelType = TypeVar("ModelType")


class RepositoryProtocol(Protocol[ModelType]):
    def add(self, product: ModelType) -> ModelType:
        ...

    def get(self, sku: str) -> ModelType | None:
        ...


# TODO: Make generic
class SqlAlchemyRepository(RepositoryProtocol):
    def __init__(self, session: Session):
        self.session = session

    def add(self, product: model.Product) -> model.Product:
        self.session.add(product)
        return product

    def get(self, sku: str) -> model.Product | None:
        query = select(model.Product).where(model.Product.sku == sku)  # type: ignore[arg-type]
        return self.session.scalar(query)

    def list(self) -> list[model.Product]:
        query = select(model.Product)
        return list(self.session.execute(query).scalars().all())


class TrackingRepository(RepositoryProtocol[model.Product]):
    seen: set[model.Product]

    def __init__(self, repo: RepositoryProtocol):
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
