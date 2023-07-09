from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from src.config import config


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_sku(name: str = "") -> str:
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name: str = "") -> str:
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name: str = "") -> str:
    return f"order-{name}-{random_suffix()}"


def test_happy_path_returns_201_and_allocated_batch(
    client: TestClient,
    add_stock: Callable[[list[tuple[str, str, int, str | None]]], None],
):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref("1")
    laterbatch = random_batchref("2")
    otherbatch = random_batchref("3")
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (otherbatch, othersku, 100, None),
        ]
    )
    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    url = config.API_V1_STR

    response = client.post(f"{url}/allocations", json=data)

    assert response.status_code == 201
    assert response.json()["batchref"] == earlybatch


def test_unhappy_path_returns_400_and_error_message(client: TestClient):
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.API_V1_STR
    response = client.post(f"{url}/allocations", json=data)
    assert response.status_code == 400
    assert response.json()["detail"] == f"Invalid sku {unknown_sku}"
