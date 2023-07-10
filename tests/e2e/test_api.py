from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import config

from ..random_refs import random_batchref, random_orderid, random_sku


def post_to_add_batch(
    client: TestClient, ref: str, sku: str, qty: int, eta: str | None
):
    url = config.API_V1_STR
    r = client.post(
        f"{url}/batches", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


def test_happy_path_returns_201_and_allocated_batch(
    client: TestClient,
):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref("1")
    laterbatch = random_batchref("2")
    otherbatch = random_batchref("3")
    post_to_add_batch(client=client, ref=laterbatch, sku=sku, qty=100, eta="2011-01-02")
    post_to_add_batch(client=client, ref=earlybatch, sku=sku, qty=100, eta="2011-01-01")
    post_to_add_batch(client=client, ref=otherbatch, sku=othersku, qty=100, eta=None)

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
