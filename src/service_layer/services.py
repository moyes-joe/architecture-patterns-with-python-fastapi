from __future__ import annotations

from datetime import date

from src.adapters import repository, session
from src.domain import model


class InvalidSku(Exception):
    pass


def is_valid_sku(sku: str, batches: list[model.Batch]):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: date | None,
    repo: repository.AbstractRepository,
    session: session.SessionProtocol,
) -> None:
    batch = model.Batch(reference=ref, sku=sku, purchased_quantity=qty, eta=eta)
    repo.add(batch)
    session.commit()


def allocate(
    orderid: str,
    sku: str,
    qty: int,
    repo: repository.AbstractRepository,
    session: session.SessionProtocol,
) -> str:
    line = model.OrderLine(orderid=orderid, sku=sku, qty=qty)
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref
