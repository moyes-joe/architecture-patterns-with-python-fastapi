from dataclasses import dataclass


class Event:
    pass


@dataclass(frozen=True, unsafe_hash=True)
class OutOfStock(Event):
    sku: str
