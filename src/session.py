from __future__ import annotations

from typing import Protocol


class SessionProtocol(Protocol):
    def commit(self) -> None:
        ...
