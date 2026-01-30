"""Base entity class for all domain objects."""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from ..client import Client

PBType = TypeVar("PBType")
ParentType = TypeVar("ParentType", bound="BaseEntity")


class BaseEntity(Generic[PBType]):
    """Base class for all domain objects wrapping protobuf messages."""

    def __init__(self, pb_obj: PBType, client: Client):
        self._pb: PBType = pb_obj
        self._client = client

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        return f"{self.__class__.__name__}(id={self.id!r})"

    def __str__(self) -> str:
        """Return user-friendly string representation."""
        return f"{self.__class__.__name__}({self.id})"

    @property
    def id(self) -> str:
        """Unique identifier."""
        return self._pb.id


class NamedBaseEntity(BaseEntity[PBType]):
    """Base class for entities that include a name field."""

    def __repr__(self) -> str:
        """Return developer-friendly representation."""
        name_str = f'"{self.name}"' if self.name else "<unnamed>"
        return f"{self.__class__.__name__}(id={self.id!r}, name={name_str})"

    def __str__(self) -> str:
        """Return user-friendly string representation."""
        if self.name:
            return f"{self.__class__.__name__}: {self.name}"
        return f"{self.__class__.__name__}({self.id})"

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._pb.name if hasattr(self._pb, "name") else ""


class SubEntity(NamedBaseEntity[PBType], Generic[PBType, ParentType]):
    """Base class for entities that are sub-entities of a parent entity."""

    def __init__(self, pb_obj: PBType, client: Client, parent: ParentType):
        super().__init__(pb_obj, client)
        self._parent_ref = weakref.ref(parent)

    @property
    def parent(self) -> ParentType:
        """Parent entity."""
        parent = self._parent_ref()
        if parent is None:
            raise RuntimeError(f"Parent of {self} has been garbage collected.")
        return parent
