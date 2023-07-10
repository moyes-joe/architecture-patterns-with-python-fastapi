from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .entity import Entity
from .value_object import ValueObject


class OutOfStock(Exception):
    pass


@dataclass(kw_only=True)
class Product:
    sku: str
    batches: list[Batch]
    version_number: int = 0

    def allocate(self, line: OrderLine) -> str:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            return batch.reference
        except StopIteration as e:
            raise OutOfStock(f"Out of stock for sku {line.sku}") from e

    def __hash__(self) -> int:
        return hash(self.sku)


@dataclass(unsafe_hash=True, kw_only=True)
class OrderLine(ValueObject):
    orderid: str
    sku: str
    qty: int


@dataclass(kw_only=True)
class Batch(Entity):
    reference: str
    sku: str
    eta: date | None
    purchased_quantity: int
    allocations: set[OrderLine] = field(default_factory=set)

    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)

    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def allocate(self, line: OrderLine):
        if self.can_allocate(line):
            self.allocations.add(line)

    def deallocate(self, line: OrderLine):
        if line in self.allocations:
            self.allocations.remove(line)

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self.allocations)

    @property
    def available_quantity(self) -> int:
        return self.purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty
