"""Base entity class for all domain objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from ..client import Client

PBType = TypeVar("PBType")


class BaseEntity(Generic[PBType]):
    """Base class for all domain objects wrapping protobuf messages."""

    def __init__(self, pb_obj: PBType, client: Client):
        self._pb: PBType = pb_obj
        self._client = client

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
    def id(self) -> str:
        """Unique identifier."""
        return self._pb.id

    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._pb.name if hasattr(self._pb, "name") else ""
