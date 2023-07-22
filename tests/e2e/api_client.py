from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import config


def post_to_add_batch(
    client: TestClient, ref: str, sku: str, qty: int, eta: str | None
):
    url = config.API_V1_STR
    r = client.post(
        f"{url}/batches", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


def post_to_allocate(
    client: TestClient, orderid: str, sku: str, qty: int, expect_success: bool = True
):
    url = config.API_V1_STR
    r = client.post(
        f"{url}/allocations",
        json={
            "orderid": orderid,
            "sku": sku,
            "qty": qty,
        },
    )
    if expect_success:
        assert r.status_code == 201
    return r
