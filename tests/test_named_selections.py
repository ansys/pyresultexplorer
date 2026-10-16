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

import logging

import pytest

from ansys.result_explorer.core import models
from ansys.result_explorer.core.exceptions import ResultExplorerError
from ansys.result_explorer.core.objects import Solution
from ansys.result_explorer.core.objects.named_selection import (
    IdsScoping,
    NamedSelection,
    NamedSelectionCreate,
    NamedSelectionType,
    PropertyScoping,
    Range,
    named_selection_create_to_proto,
    named_selection_to_proto,
    proto_to_named_selection,
    proto_to_named_selection_create,
)

log = logging.getLogger(__name__)


def test_named_selection_proto_conversion():
    named_selection = NamedSelection(
        id="selection-1",
        type=NamedSelectionType.MESH_PROPERTY,
        name="Materials",
        description="Selected materials",
        solver_named_selections=["_ELMISC"],
        bodies=[{"name": "Body 1", "id": "body-1"}],
        node_ids=[IdsScoping(values=[1, 2])],
        element_ids=[IdsScoping(values=[], range=Range(min=3, max=5))],
        property_ids=PropertyScoping(
            name="mat",
            ids=[IdsScoping(values=[7], range=Range(min=7))],
        ),
        creation_time="2026-10-16T00:00:00Z",
        location="Elemental",
        size=0,
        readonly=False,
    )

    converted = proto_to_named_selection(named_selection_to_proto(named_selection))

    assert converted.id == named_selection.id
    assert converted.type == named_selection.type
    assert converted.name == named_selection.name
    assert converted.description == named_selection.description
    assert converted.solver_named_selections == named_selection.solver_named_selections
    assert converted.bodies == named_selection.bodies
    assert converted.node_ids[0].values == [1, 2]
    assert converted.element_ids[0].range.min == 3
    assert converted.element_ids[0].range.max == 5
    assert converted.property_ids.name == "mat"
    assert converted.property_ids.ids[0].range.min == 7
    assert converted.creation_time == named_selection.creation_time
    assert converted.location == named_selection.location
    assert converted.size == 0
    assert converted.readonly is False


def test_proto_to_named_selection_preserves_absent_optional_fields():
    proto = models.NamedSelection(
        id="selection-1",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
    )

    named_selection = proto_to_named_selection(proto)

    assert named_selection.name is None
    assert named_selection.description is None
    assert named_selection.property_ids is None
    assert named_selection.creation_time is None
    assert named_selection.location is None
    assert named_selection.size is None
    assert named_selection.readonly is None


def test_named_selection_create_proto_conversion():
    named_selection = NamedSelectionCreate(
        type=NamedSelectionType.MESH_PROPERTY,
        solver_named_selections=["_ELMISC"],
        bodies=[{"name": "Body 1", "id": "body-1"}],
        node_ids=[IdsScoping(values=[1, 2])],
        element_ids=[IdsScoping(values=[], range=Range(min=3, max=5))],
        name="Materials",
        description="Selected materials",
        property_ids=PropertyScoping(
            name="mat",
            ids=[IdsScoping(values=[7], range=Range(min=7))],
        ),
        id="selection-1",
        readonly=False,
    )

    converted = proto_to_named_selection_create(named_selection_create_to_proto(named_selection))

    assert converted.type == named_selection.type
    assert converted.solver_named_selections == named_selection.solver_named_selections
    assert converted.bodies == named_selection.bodies
    assert converted.node_ids[0].values == [1, 2]
    assert converted.element_ids[0].range.min == 3
    assert converted.element_ids[0].range.max == 5
    assert converted.name == named_selection.name
    assert converted.description == named_selection.description
    assert converted.property_ids.name == "mat"
    assert converted.property_ids.ids[0].range.min == 7
    assert converted.id == named_selection.id
    assert converted.readonly is False


def test_proto_to_named_selection_create_preserves_absent_optional_fields():
    proto = models.NamedSelectionCreate(
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
    )

    named_selection = proto_to_named_selection_create(proto)

    assert named_selection.name is None
    assert named_selection.description is None
    assert named_selection.property_ids is None
    assert named_selection.id is None
    assert named_selection.readonly is None


def test_named_selections(multiple_connections_solution: Solution):
    """CRUD operations for named selections."""

    sol = multiple_connections_solution

    # create a new named selection
    named_selection = NamedSelectionCreate(
        name="My NS",
        type=NamedSelectionType.ELEMENT,
        solver_named_selections=[],
        bodies=[],
        node_ids=[],
        element_ids=[
            IdsScoping(values=[1, 2, 3, 4, 5]),
        ],
    )

    log.info("Creating named selection with data: %s", named_selection)

    named_selection = sol.create_named_selection(named_selection)

    assert named_selection.id is not None
    assert named_selection.name == "My NS"
    assert named_selection.type == NamedSelectionType.ELEMENT
    assert named_selection.element_ids[0].values == [1, 2, 3, 4, 5]
    assert named_selection.size == 5

    # verify the named selection is in the solution
    ns_in_sol = next((ns for ns in sol.named_selections if ns.id == named_selection.id), None)
    assert ns_in_sol is not None
    assert ns_in_sol.name == "My NS"
    assert ns_in_sol.readonly is False
    assert ns_in_sol.location == "Elemental"

    # update the named selection
    named_selection.name = "Updated NS"
    named_selection.element_ids.clear()
    named_selection.element_ids.append(IdsScoping(range=Range(min=6, max=10)))
    named_selection = sol.update_named_selection(named_selection)

    assert named_selection.name == "Updated NS"
    assert named_selection.element_ids[0].range.min == 6
    assert named_selection.element_ids[0].range.max == 10
    assert named_selection.size == 5

    ns_in_sol = next((ns for ns in sol.named_selections if ns.id == named_selection.id), None)
    assert ns_in_sol is not None
    assert ns_in_sol.name == "Updated NS"
    assert ns_in_sol.element_ids[0].range.min == 6
    assert ns_in_sol.element_ids[0].range.max == 10
    assert ns_in_sol.size == 5

    # delete the named selection
    sol.delete_named_selection(named_selection.id)
    ns_in_sol = next((ns for ns in sol.named_selections if ns.id == named_selection.id), None)
    assert ns_in_sol is None


def test_named_selection_types(multiple_connections_solution: Solution):

    sol = multiple_connections_solution

    # -- create body named selection --
    bodies = sol.bodies

    # find bodies with elm type SOLID186 and wrap their labels in StringMap
    solid186_bodies = []
    for body in bodies:
        if "SOLID186" in body.element_types:
            solid186_bodies.append(body.labels)

    # create a new named selection
    named_selection = NamedSelectionCreate(
        name="Selection-SOLID186",
        type=NamedSelectionType.BODY,
        solver_named_selections=[],
        node_ids=[],
        element_ids=[],
        bodies=solid186_bodies,
    )

    # let's check it errors out since body-based named selections are not supported for creation
    with pytest.raises(ValueError, match="currently not supported"):
        _ = sol.create_named_selection(named_selection)

    # -- create node named selection --
    named_selection = NamedSelectionCreate(
        name="Selection-Nodes",
        type=NamedSelectionType.NODE,
        solver_named_selections=[],
        bodies=[],
        element_ids=[],
        node_ids=[
            IdsScoping(values=[59, 60, 61, 62]),
        ],
    )

    named_selection = sol.create_named_selection(named_selection)
    assert named_selection.id is not None
    assert named_selection.name == "Selection-Nodes"
    assert named_selection.type == NamedSelectionType.NODE
    assert named_selection.size == 4
    assert named_selection.location == "Nodal"

    # -- create a mesh property named selection --
    named_selection = NamedSelectionCreate(
        name="Selection-MeshProperty",
        type=NamedSelectionType.MESH_PROPERTY,
        solver_named_selections=[],
        bodies=[],
        node_ids=[],
        element_ids=[],
        property_ids=PropertyScoping(
            name="mat",
            ids=[IdsScoping(values=[2, 4])],
        ),
    )

    named_selection = sol.create_named_selection(named_selection)
    assert named_selection.id is not None
    assert named_selection.name == "Selection-MeshProperty"
    assert named_selection.type == NamedSelectionType.MESH_PROPERTY
    assert named_selection.size == 27 + 27
    assert named_selection.location == "Elemental"

    ## -- create a solver ns based named selection --
    elmisc_ns = next((ns for ns in sol.solver_named_selections if ns.name == "_ELMISC"), None)
    fixedsu_ns = next((ns for ns in sol.solver_named_selections if ns.name == "_FIXEDSU"), None)
    assert elmisc_ns is not None
    assert elmisc_ns.location == "Elemental"
    assert elmisc_ns.size == 2
    assert fixedsu_ns is not None
    assert fixedsu_ns.location == "Nodal"
    assert fixedsu_ns.size == 80

    named_selection = NamedSelectionCreate(
        name="Selection-SolverNS",
        type=NamedSelectionType.SOLVER_NAMED_SELECTION,
        bodies=[],
        node_ids=[],
        element_ids=[],
        solver_named_selections=[
            "_ELMISC",
            "_FIXEDSU",
        ],
    )

    with pytest.raises(ResultExplorerError, match="must have the same location"):
        _ = sol.create_named_selection(named_selection)
