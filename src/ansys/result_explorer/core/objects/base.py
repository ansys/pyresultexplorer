# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base entity class for all domain objects."""

from __future__ import annotations

import weakref
from collections.abc import Sequence
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from ..client import Client

PBType = TypeVar("PBType")
ParentType = TypeVar("ParentType", bound="BaseEntity")


class BaseEntity(Generic[PBType]):
    """Base class for all domain objects wrapping protobuf messages."""

    def __init__(self, pb_obj: PBType, client: Client):
        """Initialize base entity."""
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
        """Initialize sub-entity."""
        super().__init__(pb_obj, client)
        self._parent_ref = weakref.ref(parent)

    @property
    def parent(self) -> ParentType:
        """Parent entity."""
        parent = self._parent_ref()
        if parent is None:
            raise RuntimeError(f"Parent of {self} has been garbage collected.")
        return parent


def _pb_to_dataclass(pb_obj, dataclass_type: type):
    """Convert a protobuf object to a dataclass instance."""
    # if pb_obj is None, return None
    if pb_obj is None:
        return None

    # if pb_obj is a repeated field, convert each item
    # Use Sequence check to handle protobuf repeated fields, but exclude strings
    if isinstance(pb_obj, Sequence) and not isinstance(pb_obj, str):
        return [_pb_to_dataclass(item, dataclass_type) for item in pb_obj]

    field_names = {f.name for f in dataclass_type.__dataclass_fields__.values()}
    init_kwargs = {field: getattr(pb_obj, field) for field in field_names if hasattr(pb_obj, field)}
    return dataclass_type(**init_kwargs)
