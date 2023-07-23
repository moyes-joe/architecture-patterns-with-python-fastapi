from __future__ import annotations

import logging

import redis

from src import bootstrap
from src.config import config
from src.domain import commands
from src.service_layer import messagebus

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())  # type: ignore


def main() -> None:
    logger.info("Redis pubsub starting")
    bus = bootstrap.bootstrap()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m: dict[str, str], bus: messagebus.MessageBus) -> None:
    logging.debug("handling %s", m)
    cmd = commands.ChangeBatchQuantity.model_validate_json(m["data"])
    bus.handle(cmd)


if __name__ == "__main__":
    main()
