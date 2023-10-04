from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Self

from src.adapters import repository, unit_of_work_strategy
from src.domain import commands, events


class UnitOfWork:
    def __init__(self, uow: unit_of_work_strategy.UnitOfWorkStrategy) -> None:
        self._uow = uow

    def __enter__(self) -> Self:
        self._uow.__enter__()
        self.products = repository.TrackingRepository(self._uow.products)
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
