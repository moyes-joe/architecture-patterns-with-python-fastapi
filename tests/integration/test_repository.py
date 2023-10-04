from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.adapters import repository
from src.domain import model

pytestmark = pytest.mark.usefixtures("mappers")


def test_get_by_batchref(session: Session) -> None:
    repo = repository.SqlAlchemyRepository(session)
    b1 = model.Batch(reference="b1", sku="sku1", purchased_quantity=100, eta=None)
    b2 = model.Batch(reference="b2", sku="sku1", purchased_quantity=100, eta=None)
    b3 = model.Batch(reference="b3", sku="sku2", purchased_quantity=100, eta=None)
    p1 = model.Product(sku="sku1", batches=[b1, b2])
    p2 = model.Product(sku="sku2", batches=[b3])
    repo.add(p1)
    repo.add(p2)
    assert repo.get_by_batchref("b2") == p1
    assert repo.get_by_batchref("b3") == p2
