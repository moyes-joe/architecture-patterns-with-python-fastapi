from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class Entity:
    """An entity is any domain object that has an identity.

    We usually make them mutable.

    Entities have an identity that runs through time and different states.
    """

    reference: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        # replace refernece with id?
        return self.reference == other.reference

    def __hash__(self):
        return hash(self.reference)
