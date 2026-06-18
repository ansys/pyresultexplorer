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

import logging

import pytest
from google.protobuf.json_format import MessageToDict

from ansys.result_explorer.core import models
from ansys.result_explorer.core.exceptions import ResultExplorerError
from ansys.result_explorer.core.objects import Solution

log = logging.getLogger(__name__)


def test_named_selections(multiple_connections_solution: Solution):
    """CRUD operations for named selections."""

    sol = multiple_connections_solution

    # create a new named selection
    named_selection = models.NamedSelectionCreate(
        name="My NS",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
        element_ids=[
            models.IdsScoping(
                values=[1, 2, 3, 4, 5],
            ),
        ],
    )

    # to dict and print
    named_selection_dict = MessageToDict(named_selection, always_print_fields_with_no_presence=True)
    log.info(f"Creating named selection with data: {named_selection_dict}")

    named_selection = sol.create_named_selection(named_selection)

    assert named_selection.id is not None
    assert named_selection.name == "My NS"
    assert named_selection.type == models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT
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
    named_selection.element_ids.append(models.IdsScoping(range=models.Range(min=6, max=10)))
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
            string_map = models.StringMap(string_map=body.labels)
            solid186_bodies.append(string_map)

    # create a new named selection
    named_selection = models.NamedSelectionCreate(
        name="Selection-SOLID186",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_BODY,
        bodies=solid186_bodies,
    )

    # let's check it errors out since body-based named selections are not supported for creation
    with pytest.raises(ValueError, match="currently not supported"):
        _ = sol.create_named_selection(named_selection)

    # -- create node named selection --
    named_selection = models.NamedSelectionCreate(
        name="Selection-Nodes",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_NODE,
        node_ids=[
            models.IdsScoping(
                values=[59, 60, 61, 62],
            ),
        ],
    )

    named_selection = sol.create_named_selection(named_selection)
    assert named_selection.id is not None
    assert named_selection.name == "Selection-Nodes"
    assert named_selection.type == models.NamedSelectionType.NAMED_SELECTION_TYPE_NODE
    assert named_selection.size == 4
    assert named_selection.location == "Nodal"

    # -- create a mesh property named selection --
    named_selection = models.NamedSelectionCreate(
        name="Selection-MeshProperty",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_MESH_PROPERTY,
        property_ids=models.PropertyScoping(
            name="mat",
            ids=[
                models.IdsScoping(
                    values=[2, 4],
                )
            ],
        ),
    )

    named_selection = sol.create_named_selection(named_selection)
    assert named_selection.id is not None
    assert named_selection.name == "Selection-MeshProperty"
    assert named_selection.type == models.NamedSelectionType.NAMED_SELECTION_TYPE_MESH_PROPERTY
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

    named_selection = models.NamedSelectionCreate(
        name="Selection-SolverNS",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_SOLVER_NAMED_SELECTION,
        solver_named_selections=[
            "_ELMISC",
            "_FIXEDSU",
        ],
    )

    with pytest.raises(ResultExplorerError, match="must have the same location"):
        _ = sol.create_named_selection(named_selection)
