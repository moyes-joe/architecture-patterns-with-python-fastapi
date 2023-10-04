from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import commands
from . import events as domain_events
from .entity import Entity
from .value_object import ValueObject


@dataclass(kw_only=True)
class Product:
    sku: str
    batches: list[Batch]
    version_number: int = 0
    messages: list[domain_events.Event | commands.Command] = field(default_factory=list)

    def allocate(self, line: OrderLine) -> domain_events.AllocatedBatchRef | None:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            self.messages.append(
                domain_events.Allocated(
                    orderid=line.orderid,
                    sku=line.sku,
                    qty=line.qty,
                    batchref=batch.reference,
                )
            )
            return domain_events.AllocatedBatchRef(batchref=batch.reference)
        except StopIteration:
            self.messages.append(domain_events.OutOfStock(sku=line.sku))
            return None

    def change_batch_quantity(self, ref: str, qty: int):
        batch = next(b for b in self.batches if b.reference == ref)
        batch.purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.messages.append(
                domain_events.Deallocated(
                    orderid=line.orderid, sku=line.sku, qty=line.qty
                )
            )

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

    def __repr__(self):
        return f"<Batch {self.reference}>"

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

    def deallocate_one(self) -> OrderLine:
        return self.allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self.allocations)

    @property
    def available_quantity(self) -> int:
        return self.purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty
