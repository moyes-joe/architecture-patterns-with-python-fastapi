from __future__ import annotations

import logging

import redis

from src.adapters.orm import start_mappers
from src.config import config
from src.domain import commands
from src.service_layer import messagebus

from .redis_deps import get_unit_of_work

logger = logging.getLogger(__name__)

r = redis.Redis(**config.get_redis_host_and_port())  # type: ignore


def main():
    start_mappers()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    # TODO: Configure logging
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m)


def handle_change_batch_quantity(m: dict[str, str]):
    logging.debug("handling %s", m)
    cmd = commands.ChangeBatchQuantity.model_validate_json(m["data"])
    uow = get_unit_of_work()
    messagebus.handle(cmd, uow=uow)


if __name__ == "__main__":
    main()
