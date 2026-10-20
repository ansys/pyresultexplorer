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

from dataclasses import asdict

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.message_factory import GetMessageClass
from hypothesis import given
from hypothesis import strategies as st

from ansys.result_explorer.core import models
from ansys.result_explorer.core.objects.named_selection import (
    NamedSelection,
    NamedSelectionCreate,
    Range,
    named_selection_create_to_proto,
    named_selection_to_proto,
    proto_to_named_selection,
    proto_to_named_selection_create,
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
            return st.dictionaries(protobuf_fields(key), protobuf_fields(value), max_size=5)
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
