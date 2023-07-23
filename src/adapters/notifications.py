from __future__ import annotations

import smtplib
from typing import Protocol

from src.config import config


class NotificationsProtocol(Protocol):
    def send(self, destination: str, message: str) -> None:
        raise NotImplementedError


DEFAULT_HOST = config.get_email_host_and_port()["host"]
DEFAULT_PORT = config.get_email_host_and_port()["port"]


class EmailNotifications(NotificationsProtocol):
    def __init__(self, smtp_host=DEFAULT_HOST, port=DEFAULT_PORT) -> None:
        self.server = smtplib.SMTP(host=smtp_host, port=port)
        self.server.noop()

    def send(self, destination, message) -> None:
        msg = f"Subject: allocation service notification\n{message}"
        self.server.sendmail(
            from_addr="allocations@example.com",
            to_addrs=[destination],
            msg=msg,
        )
