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

from __future__ import annotations

from dataclasses import asdict

import pytest
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.message_factory import GetMessageClass
from hypothesis import given
from hypothesis import strategies as st

from ansys.result_explorer.core import models
from ansys.result_explorer.core.exceptions import ResultExplorerError
from ansys.result_explorer.core.objects.named_selection import (
    NamedSelection,
    NamedSelectionCreate,
    Range,
    named_selection_create_to_proto,
    named_selection_to_proto,
    proto_to_named_selection,
    proto_to_named_selection_create,
)
from ansys.result_explorer.core.objects.plot_definition import (
    Component,
    Location,
    PlotDefinition,
    ResultFieldName,
    ResultType,
    ShellPosition,
)

INT32 = st.integers(min_value=-(2**31), max_value=2**31 - 1)
# Match protobuf's float32 precision; NaN cannot be compared by equality.
FLOAT32 = st.floats(width=32, allow_nan=False)


st.register_type_strategy(
    Range,
    st.builds(Range, min=st.none() | FLOAT32, max=st.none() | FLOAT32),
)


def protobufs[T: Message](message_type: type[T]) -> st.SearchStrategy[T]:
    fields = {}
    for field in message_type.DESCRIPTOR.fields:
        assert isinstance(field, FieldDescriptor)
        fields[field.name] = protobuf_fields(field)
    return st.builds(message_type, **fields)


def protobuf_fields(field: FieldDescriptor) -> st.SearchStrategy[object]:
    strategy: st.SearchStrategy[object]
    if field.message_type is not None:
        if field.message_type.GetOptions().map_entry:
            key, value = field.message_type.fields
            values = (
                protobufs(GetMessageClass(value.message_type))
                if value.message_type is not None
                else protobuf_fields(value)
            )
            return st.dictionaries(protobuf_fields(key), values, max_size=5)
        strategy = protobufs(GetMessageClass(field.message_type))
    elif field.enum_type is not None:
        strategy = st.sampled_from([value.number for value in field.enum_type.values])
    else:
        strategy = {
            FieldDescriptor.TYPE_STRING: st.text(),
            FieldDescriptor.TYPE_INT32: INT32,
            FieldDescriptor.TYPE_FLOAT: FLOAT32,
            FieldDescriptor.TYPE_BOOL: st.booleans(),
        }[field.type]

    if field.is_repeated:
        return st.lists(strategy, max_size=5)
    if field.has_presence:
        return st.none() | strategy
    return strategy


@given(selection=st.from_type(NamedSelection))
def test_named_selection_object_round_trip(selection: NamedSelection) -> None:
    converted = proto_to_named_selection(named_selection_to_proto(selection))

    # These dataclasses deliberately disable generated equality.
    assert asdict(converted) == asdict(selection)


@given(selection=st.from_type(NamedSelectionCreate))
def test_named_selection_create_object_round_trip(selection: NamedSelectionCreate) -> None:
    converted = proto_to_named_selection_create(named_selection_create_to_proto(selection))

    assert asdict(converted) == asdict(selection)


@given(proto=protobufs(models.NamedSelection))
def test_named_selection_proto_round_trip(proto: models.NamedSelection) -> None:
    converted = named_selection_to_proto(proto_to_named_selection(proto))

    assert converted == proto


@given(proto=protobufs(models.NamedSelectionCreate))
def test_named_selection_create_proto_round_trip(proto: models.NamedSelectionCreate) -> None:
    converted = named_selection_create_to_proto(proto_to_named_selection_create(proto))

    assert converted == proto


@pytest.mark.parametrize("proto_type", [models.PlotDefinition, models.PlotDefinitionCreate])
@given(
    result_type=st.from_type(ResultType),
    location=st.from_type(Location),
    shell_position=st.from_type(ShellPosition),
)
def test_plot_definition_enum_conversion[T: (models.PlotDefinition, models.PlotDefinitionCreate)](
    proto_type: type[T],
    result_type: ResultType,
    location: Location,
    shell_position: ShellPosition,
) -> None:
    plot = PlotDefinition(result_type, location, shell_position=shell_position)
    proto = plot.to_proto(proto_type)
    assert models.ResultType.Name(proto.result_type) == f"RESULT_TYPE_{result_type.name.upper()}"
    assert proto.location == location.value
    assert (
        models.ShellPosition.Name(proto.shell_position)
        == f"SHELL_POSITION_{shell_position.name.upper()}"
    )
    converted = PlotDefinition.from_proto(proto)
    assert converted.result_type is result_type
    assert converted.location == location
    assert converted.shell_position is shell_position


@pytest.mark.parametrize("proto_type", [models.PlotDefinition, models.PlotDefinitionCreate])
@pytest.mark.parametrize("result_type", models.ResultType.values(), ids=models.ResultType.Name)
def test_proto_to_plot_result_type[T: (models.PlotDefinition, models.PlotDefinitionCreate)](
    proto_type: type[T], result_type: models.ResultType.ValueType
) -> None:
    converted = PlotDefinition.from_proto(proto_type(result_type=result_type))

    assert isinstance(converted.result_type, ResultType)
    assert (
        converted.result_type.value
        == models.ResultType.Name(result_type).removeprefix("RESULT_TYPE_").lower()
    )


@pytest.mark.parametrize("proto_type", [models.PlotDefinition, models.PlotDefinitionCreate])
@pytest.mark.parametrize(
    "shell_position", models.ShellPosition.values(), ids=models.ShellPosition.Name
)
def test_proto_to_plot_shell_position[T: (models.PlotDefinition, models.PlotDefinitionCreate)](
    proto_type: type[T], shell_position: models.ShellPosition.ValueType
) -> None:
    converted = PlotDefinition.from_proto(proto_type(shell_position=shell_position))

    assert isinstance(converted.shell_position, ShellPosition)
    assert (
        converted.shell_position.value
        == models.ShellPosition.Name(shell_position).removeprefix("SHELL_POSITION_").lower()
    )


@pytest.mark.parametrize("proto_type", [models.PlotDefinition, models.PlotDefinitionCreate])
@given(
    name=st.from_type(ResultFieldName),
    components=st.lists(st.from_type(Component), max_size=5),
)
def test_plot_field_enum_conversion[T: (models.PlotDefinition, models.PlotDefinitionCreate)](
    proto_type: type[T], name: ResultFieldName, components: list[Component]
) -> None:
    proto = proto_type(
        fields=[models.Field(name=name.value, components=[item.value for item in components])]
    )
    converted = PlotDefinition.from_proto(proto)
    assert converted.fields is not None
    field = converted.fields[0]
    assert field.name is name
    assert field.components == (components or None)
    assert all(isinstance(item, Component) for item in field.components or [])
    if name.name.startswith("total_"):
        with pytest.raises(ResultExplorerError, match="total result fields"):
            converted.to_proto(proto_type)
    else:
        assert converted.to_proto(proto_type).fields == proto.fields
