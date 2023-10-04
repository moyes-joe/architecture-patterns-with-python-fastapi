from __future__ import annotations

from collections.abc import Callable, Generator

import httpx
import pytest
from sqlalchemy.orm import Session, clear_mappers

from src import bootstrap
from src.adapters import notifications, unit_of_work_strategy
from src.config import config
from src.domain import commands
from src.service_layer import messagebus

from ..random_refs import random_sku


@pytest.fixture
def sqlite_bus(
    session_factory: Callable[[], Session]
) -> Generator[messagebus.MessageBus, None, None]:
    bus = bootstrap.bootstrap(
        start_orm=True,
        uow=unit_of_work_strategy.SqlAlchemyUnitOfWork(session_factory),
        notifications=notifications.EmailNotifications(),
        publish=lambda *args: None,
    )
    yield bus
    clear_mappers()


def get_email_from_mailhog(sku: str) -> dict:
    host, port = map(config.get_email_host_and_port().get, ["host", "http_port"])
    all_emails = httpx.get(f"http://{host}:{port}/api/v2/messages").json()
    return next(m for m in all_emails["items"] if sku in str(m))


def test_out_of_stock_email(sqlite_bus: messagebus.MessageBus) -> None:
    sku = random_sku()
    sqlite_bus.handle(commands.CreateBatch(ref="batch1", sku=sku, qty=9, eta=None))
    sqlite_bus.handle(commands.Allocate(orderid="order1", sku=sku, qty=10))
    email = get_email_from_mailhog(sku)
    assert email["Raw"]["From"] == "allocations@example.com"
    assert email["Raw"]["To"] == ["stock@made.com"]
    assert f"Out of stock for {sku}" in email["Raw"]["Data"]
