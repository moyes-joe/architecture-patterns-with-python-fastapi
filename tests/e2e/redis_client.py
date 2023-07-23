from __future__ import annotations

from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from redis.client import PubSub

    from src.service_layer import messagebus

from src.config import config

r = redis.Redis(**config.get_redis_host_and_port())  # type: ignore


def subscribe_to(channel) -> PubSub:
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    confirmation = pubsub.get_message(timeout=3)
    assert confirmation is not None
    assert confirmation["type"] == "subscribe"
    return pubsub


def publish_message(channel, message: messagebus.Message) -> None:
    r.publish(channel, message.model_dump_json())
