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

"""Data models and protobuf converters for named selections.

Integer annotations describe protobuf bounds without runtime validation.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Annotated

from annotated_types import Ge, Le

from .. import models

Int32 = Annotated[int, Ge(-(2**31)), Le(2**31 - 1)]


class NamedSelectionType(IntEnum):
    """Defines supported named selection types."""

    SOLVER_NAMED_SELECTION = 0
    BODY = 1
    NODE = 2
    ELEMENT = 3
    MESH_PROPERTY = 4


@dataclass(eq=False, repr=False)
class Range:
    """Describes an optional numeric range."""

    min: float | None = None
    max: float | None = None


@dataclass(eq=False, repr=False)
class IdsScoping:
    """Stores explicit IDs or a numeric range."""

    values: list[Int32] = field(default_factory=list)
    range: Range | None = None


@dataclass(eq=False, repr=False)
class PropertyScoping:
    """Groups ID scopings under a mesh property name."""

    name: str
    ids: list[IdsScoping]


@dataclass(eq=False, repr=False)
class NamedSelection:
    """Represents a named selection returned by the server."""

    id: str
    type: NamedSelectionType
    name: str | None
    description: str | None
    solver_named_selections: list[str]
    bodies: list[dict[str, str]]
    node_ids: list[IdsScoping]
    element_ids: list[IdsScoping]
    property_ids: PropertyScoping | None = None
    creation_time: str | None = None
    location: str | None = None
    size: Int32 | None = None
    readonly: bool | None = None


@dataclass(eq=False, repr=False)
class NamedSelectionCreate:
    """Describes a named selection to create or update."""

    type: NamedSelectionType
    solver_named_selections: list[str]
    bodies: list[dict[str, str]]
    node_ids: list[IdsScoping]
    element_ids: list[IdsScoping]
    name: str | None = None
    description: str | None = None
    property_ids: PropertyScoping | None = None
    id: str | None = None
    readonly: bool | None = None


def _range_to_proto(value: Range) -> models.Range:
    proto = models.Range()
    if value.min is not None:
        proto.min = value.min
    if value.max is not None:
        proto.max = value.max
    return proto


def _ids_scoping_to_proto(value: IdsScoping) -> models.IdsScoping:
    proto = models.IdsScoping(values=value.values)
    if value.range is not None:
        proto.range.CopyFrom(_range_to_proto(value.range))
    return proto


def _proto_to_ids_scoping(proto: models.IdsScoping) -> IdsScoping:
    value_range = None
    if proto.HasField("range"):
        value_range = Range(
            min=proto.range.min if proto.range.HasField("min") else None,
            max=proto.range.max if proto.range.HasField("max") else None,
        )
    return IdsScoping(values=list(proto.values), range=value_range)


def _property_scoping_to_proto(value: PropertyScoping) -> models.PropertyScoping:
    proto = models.PropertyScoping(name=value.name)
    proto.ids.extend(_ids_scoping_to_proto(item) for item in value.ids)
    return proto


def _proto_to_property_scoping(proto: models.PropertyScoping) -> PropertyScoping:
    return PropertyScoping(
        name=proto.name,
        ids=[_proto_to_ids_scoping(item) for item in proto.ids],
    )


def named_selection_create_to_proto(
    named_selection: NamedSelectionCreate,
) -> models.NamedSelectionCreate:
    """Convert a named selection creation model to protobuf.

    Examples
    --------
    >>> selection = NamedSelectionCreate(
    ...     type=NamedSelectionType.ELEMENT,
    ...     solver_named_selections=[],
    ...     bodies=[],
    ...     node_ids=[],
    ...     element_ids=[],
    ...     name="Elements",
    ... )
    >>> named_selection_create_to_proto(selection).name
    'Elements'

    """
    proto = models.NamedSelectionCreate(
        type=getattr(
            models.NamedSelectionType,
            f"NAMED_SELECTION_TYPE_{named_selection.type.name}",
        ),
    )
    for field_ in ("name", "description", "id", "readonly"):
        value = getattr(named_selection, field_)
        if value is not None:
            setattr(proto, field_, value)

    proto.solver_named_selections.extend(named_selection.solver_named_selections)
    for body in named_selection.bodies:
        proto.bodies.add().string_map.update(body)
    proto.node_ids.extend(_ids_scoping_to_proto(value) for value in named_selection.node_ids)
    proto.element_ids.extend(_ids_scoping_to_proto(value) for value in named_selection.element_ids)
    if named_selection.property_ids is not None:
        proto.property_ids.CopyFrom(_property_scoping_to_proto(named_selection.property_ids))
    return proto


def proto_to_named_selection_create(
    proto: models.NamedSelectionCreate,
) -> NamedSelectionCreate:
    """Convert a protobuf creation message to the object model.

    Examples
    --------
    >>> proto = models.NamedSelectionCreate(
    ...     type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
    ...     name="Elements",
    ... )
    >>> proto_to_named_selection_create(proto).name
    'Elements'

    """
    property_ids = None
    if proto.HasField("property_ids"):
        property_ids = _proto_to_property_scoping(proto.property_ids)

    return NamedSelectionCreate(
        type=NamedSelectionType[
            models.NamedSelectionType.Name(proto.type).removeprefix("NAMED_SELECTION_TYPE_")
        ],
        solver_named_selections=list(proto.solver_named_selections),
        bodies=[dict(body.string_map) for body in proto.bodies],
        node_ids=[_proto_to_ids_scoping(value) for value in proto.node_ids],
        element_ids=[_proto_to_ids_scoping(value) for value in proto.element_ids],
        name=proto.name if proto.HasField("name") else None,
        description=proto.description if proto.HasField("description") else None,
        property_ids=property_ids,
        id=proto.id if proto.HasField("id") else None,
        readonly=proto.readonly if proto.HasField("readonly") else None,
    )


def named_selection_to_proto(named_selection: NamedSelection) -> models.NamedSelection:
    """Convert a named selection to its protobuf representation.

    Examples
    --------
    >>> selection = NamedSelection(
    ...     id="ns-1",
    ...     type=NamedSelectionType.ELEMENT,
    ...     name=None,
    ...     description=None,
    ...     solver_named_selections=[],
    ...     bodies=[],
    ...     node_ids=[],
    ...     element_ids=[],
    ... )
    >>> named_selection_to_proto(selection).id
    'ns-1'

    """
    proto = models.NamedSelection(
        id=named_selection.id,
        type=getattr(
            models.NamedSelectionType,
            f"NAMED_SELECTION_TYPE_{named_selection.type.name}",
        ),
    )
    for field_ in ("name", "description", "creation_time", "location", "size", "readonly"):
        value = getattr(named_selection, field_)
        if value is not None:
            setattr(proto, field_, value)

    proto.solver_named_selections.extend(named_selection.solver_named_selections)
    for body in named_selection.bodies:
        proto.bodies.add().string_map.update(body)
    proto.node_ids.extend(_ids_scoping_to_proto(value) for value in named_selection.node_ids)
    proto.element_ids.extend(_ids_scoping_to_proto(value) for value in named_selection.element_ids)
    if named_selection.property_ids is not None:
        proto.property_ids.name = named_selection.property_ids.name
        proto.property_ids.ids.extend(
            _ids_scoping_to_proto(value) for value in named_selection.property_ids.ids
        )
    return proto


def proto_to_named_selection(proto: models.NamedSelection) -> NamedSelection:
    """Convert a protobuf named selection to the object model.

    Examples
    --------
    >>> proto = models.NamedSelection(
    ...     id="ns-1",
    ...     type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
    ... )
    >>> proto_to_named_selection(proto).id
    'ns-1'

    """
    property_ids = None
    if proto.HasField("property_ids"):
        property_ids = _proto_to_property_scoping(proto.property_ids)

    return NamedSelection(
        id=proto.id,
        type=NamedSelectionType[
            models.NamedSelectionType.Name(proto.type).removeprefix("NAMED_SELECTION_TYPE_")
        ],
        name=proto.name if proto.HasField("name") else None,
        description=proto.description if proto.HasField("description") else None,
        solver_named_selections=list(proto.solver_named_selections),
        bodies=[dict(body.string_map) for body in proto.bodies],
        node_ids=[_proto_to_ids_scoping(value) for value in proto.node_ids],
        element_ids=[_proto_to_ids_scoping(value) for value in proto.element_ids],
        property_ids=property_ids,
        creation_time=proto.creation_time if proto.HasField("creation_time") else None,
        location=proto.location if proto.HasField("location") else None,
        size=proto.size if proto.HasField("size") else None,
        readonly=proto.readonly if proto.HasField("readonly") else None,
    )
