from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

from src.domain import commands, events

from . import handlers

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = commands.Command | events.Event


def handle(
    message: Message,
    uow: unit_of_work.UnitOfWork,
):
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")
    return results


def handle_event(
    event: events.Event,
    queue: list[Message],
    uow: unit_of_work.UnitOfWork,
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug("handling event %s with handler %s", event, handler)
            handler(event=event, uow=uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logger.exception("Exception handling event %s", event)
            continue


def handle_command(
    command: commands.Command,
    queue: list[Message],
    uow: unit_of_work.UnitOfWork,
):
    logger.debug("handling command %s", command)
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(cmd=command, uow=uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception("Exception handling command %s", command)
        raise


class EventHandler(Protocol):
    def __call__(self, event: Any, uow: unit_of_work.UnitOfWork) -> Any:
        ...


class CommandHandler(Protocol):
    def __call__(self, cmd: Any, uow: unit_of_work.UnitOfWork) -> Any:
        ...


EVENT_HANDLERS: dict[type[events.Event], list[EventHandler]] = {
    events.Allocated: [handlers.publish_allocated_event],
    events.OutOfStock: [handlers.send_out_of_stock_notification],
}
COMMAND_HANDLERS: dict[type[commands.Command], CommandHandler] = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}
