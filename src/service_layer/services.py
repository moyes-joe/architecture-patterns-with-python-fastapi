from __future__ import annotations

from src.adapters import repository, session
from src.domain import model


class InvalidSku(Exception):
    pass


def is_valid_sku(sku: str, batches: list[model.Batch]):
    return sku in {b.sku for b in batches}


def allocate(
    line: model.OrderLine,
    repo: repository.AbstractRepository,
    session: session.SessionProtocol,
) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref
