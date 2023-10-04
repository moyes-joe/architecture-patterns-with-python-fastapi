from __future__ import annotations

import logging

import redis

from src.config import config
from src.domain import events

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())  # type: ignore


def publish(channel, event: events.Event) -> None:
    logging.debug("publishing: channel=%s, event=%s", channel, event)
    r.publish(channel, event.model_dump_json())
