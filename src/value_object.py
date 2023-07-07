from __future__ import annotations

from dataclasses import dataclass


@dataclass(unsafe_hash=True, kw_only=True)
class ValueObject:
    """A value object is any domain object that is uniquely identified by the data it holds.

    We usually make them immutable.

    Value objects do not have an identity, they are defined by the values they hold.
    """

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__
