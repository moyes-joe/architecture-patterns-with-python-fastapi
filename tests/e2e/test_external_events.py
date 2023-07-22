from __future__ import annotations

import json

from fastapi.testclient import TestClient
from tenacity import Retrying, stop_after_delay

from ..random_refs import random_batchref, random_orderid, random_sku
from . import api_client, redis_client


# TODO: Configure this fixture
# @pytest.mark.usefixtures("restart_redis_pubsub")
def test_change_batch_quantity_leading_to_reallocation(postgres_client: TestClient):
    # start with two batches and an order allocated to one of them
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    api_client.post_to_add_batch(
        client=postgres_client, ref=earlier_batch, sku=sku, qty=10, eta="2011-01-01"
    )
    api_client.post_to_add_batch(
        client=postgres_client, ref=later_batch, sku=sku, qty=10, eta="2011-01-02"
    )
    response = api_client.post_to_allocate(
        client=postgres_client, orderid=orderid, sku=sku, qty=10
    )
    assert response.json()["batchref"] == earlier_batch

    subscription = redis_client.subscribe_to("line_allocated")

    # change quantity on allocated batch so it's less than our order
    redis_client.publish_message(
        "change_batch_quantity",
        {"ref": earlier_batch, "qty": 5},
    )

    # wait until we see a message saying the order has been reallocated
    messages = []
    found = False
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                found = True
                messages.append(message)
                print(messages)
                data = json.loads(messages[-1]["data"])
                break

    assert found  # ensure that the loop completed (i.e. didn't time out)
    assert data["orderid"] == orderid
    assert data["batchref"] == later_batch
