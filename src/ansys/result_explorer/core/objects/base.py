# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
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
from typing import TYPE_CHECKING, Annotated, Self

from pydantic import AnyUrl, BaseModel, Field, HttpUrl, UrlConstraints, model_validator

if TYPE_CHECKING:
    from ..client import Client


class BaseEntity[PBType]:
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


class NamedBaseEntity[PBType](BaseEntity[PBType]):
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


class SubEntity[PBType, ParentType: BaseEntity](NamedBaseEntity[PBType]):
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


GrpcUrl = Annotated[
    AnyUrl,
    UrlConstraints(
        allowed_schemes=["grpc", "grpcs"],
        host_required=True,
    ),
]


class HpsData(BaseModel):
    """Represents HPS data."""

    resource_name: Annotated[str, Field(alias="resourceName")]


class ConnectionToken(BaseModel):
    """Represents a connection token."""

    http_base_url: Annotated[
        HttpUrl, Field(alias="httpBaseUrl"), UrlConstraints(host_required=True)
    ]
    grpc_base_url: Annotated[GrpcUrl, Field(alias="grpcBaseUrl")]
    hps_data: Annotated[HpsData | None, Field(alias="hpsData")] = None
    session_id: Annotated[str, Field(alias="sessionId")]
    ca_cert_path: Annotated[str, Field(alias="caCertPath")]

    @model_validator(mode="after")
    def validate_ports(self) -> Self:
        """Validate that the base URLs have ports."""
        if self.http_base_url.port is None:
            raise ValueError("HTTP base URL must include a port.")
        if self.grpc_base_url.port is None:
            raise ValueError("gRPC base URL must include a port.")
        return self
