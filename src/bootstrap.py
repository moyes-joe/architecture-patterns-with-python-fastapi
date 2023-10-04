import inspect
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import clear_mappers

from src.adapters import orm, redis_event_publisher, unit_of_work_strategy
from src.adapters.notifications import EmailNotifications, NotificationsProtocol
from src.service_layer import handlers, messagebus, unit_of_work


def bootstrap(
    start_orm: bool = True,
    uow: unit_of_work_strategy.UnitOfWorkStrategy | None = None,
    notifications: NotificationsProtocol | None = None,
    publish: Callable = redis_event_publisher.publish,
) -> messagebus.MessageBus:
    uow = uow or unit_of_work_strategy.SqlAlchemyUnitOfWork()
    uow_ = unit_of_work.UnitOfWork(uow=uow)
    notifications = notifications or EmailNotifications()
    if start_orm:
        clear_mappers()
        orm.start_mappers()

    dependencies = {"uow": uow_, "notifications": notifications, "publish": publish}
    injected_event_handlers = {
        event_type: [
            inject_dependencies(handler, dependencies) for handler in event_handlers
        ]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return messagebus.MessageBus(
        uow=uow_,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
    )


def inject_dependencies(handler: Callable, dependencies: dict) -> Callable[[Any], Any]:
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency for name, dependency in dependencies.items() if name in params
    }
    return lambda message: handler(message, **deps)
