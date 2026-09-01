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

from ansys.result_explorer.core import Client, models
from ansys.result_explorer.core.exceptions import ResultExplorerError
from ansys.result_explorer.core.objects import Solution
from ansys.result_explorer.core.objects.plot_definition import (
    Component,
    Field,
    Location,
    PlotDefinition,
    ResultFieldName,
    ResultType,
    ShellPosition,
    plot_definition_to_proto,
    proto_to_plot_definition,
)

log = logging.getLogger(__name__)


def test_plot(multiple_connections_solution: Solution):
    """CRUD operations for plot."""

    sol = multiple_connections_solution

    # create a new plot
    plot_def = PlotDefinition(
        result_type=ResultType.stress,
        location="Nodal",
        name="My stress plot",
        last_set=False,
        all_sets=True,
        on_skin=True,
        shell_position=ShellPosition.middle,
        fields=[
            Field(ResultFieldName.equivalent_von_mises_stress),
            Field(ResultFieldName.stress_tensor, [Component.XX, Component.ZZ]),
        ],
    )

    plot_view = sol.create_plot(plot_def)
    plot_def = plot_view.definition

    assert plot_def.id is not None
    assert plot_def.name == "My stress plot"
    assert plot_def.result_type == ResultType.stress
    assert plot_def.on_skin is True
    assert plot_def.supports_monitoring is True
    assert plot_def.shell_position == ShellPosition.middle
    assert plot_def.all_sets is True
    assert plot_def.last_set is False

    # verify the plot is in the solution's plots
    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is not None
    assert plot_def_in_sol.fields[0].name == "equivalent_von_mises_stress"
    assert plot_def_in_sol.fields[1].name == "stress_tensor"
    assert plot_def_in_sol.fields[1].components == ["XX", "ZZ"]

    # update the plot
    plot_def.name = "Updated stress plot"
    plot_def.all_sets = False
    plot_def.last_set = True
    plot_def = sol.update_plot(plot_def)

    assert plot_def.name == "Updated stress plot"

    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is not None
    assert plot_def_in_sol.name == "Updated stress plot"
    assert plot_def_in_sol.all_sets is False
    assert plot_def_in_sol.last_set is True

    # delete the plot
    sol.delete_plot(plot_def.id)
    plot_def_in_sol = next((p for p in sol.plots if p.id == plot_def.id), None)
    assert plot_def_in_sol is None

    plot_def_in_views = next(
        (v for v in sol.views if v.type == models.ViewType.VIEW_TYPE_PLOT and v.id == plot_def.id),
        None,
    )
    assert plot_def_in_views is None


def test_plot_view_no_definition(multiple_connections_solution: Solution):

    sol = multiple_connections_solution

    # create a new plot
    plot_def = PlotDefinition(
        result_type=ResultType.stress,
        location=Location.nodal,
        name="My stress plot",
        shell_position=ShellPosition.middle,
        fields=[
            Field(ResultFieldName.equivalent_von_mises_stress),
        ],
    )

    plot_view = sol.create_plot(plot_def)
    plot_def = plot_view.definition

    # delete the plot view
    sol.delete_plot(plot_def.id)

    with pytest.raises(RuntimeError, match="not found"):
        _ = plot_view.definition


def test_plot_with_default_result_type(multiple_connections_solution: Solution):
    """Make sure that a plot using the default result type (displacement)
    can be created without error.

    This is a regression test for a bug where the server would return an error
    if the result type was not explicitly set, which is the case when setting
    the result type to displacement since it's the default and protobuf does not
    serialize default values.
    """

    sol = multiple_connections_solution

    plot_def = PlotDefinition(
        result_type=ResultType.displacement,
        location="Nodal",
        name="test plot",
        last_set=True,
        all_sets=False,
        on_skin=True,
        shell_position=ShellPosition.middle,
        fields=[Field(ResultFieldName.displacement)],
    )

    plot_def = sol.create_plot(plot_def).definition

    assert plot_def.id is not None
    assert plot_def.result_type == ResultType.displacement


def test_new_plot_added_to_views(multiple_connections_solution: Solution):
    """Ensure that a new plot is added to the solution's views."""

    sol = multiple_connections_solution

    plot_def = PlotDefinition(
        result_type=ResultType.displacement,
        location=Location.nodal,
        name="New plot",
        last_set=True,
        all_sets=False,
        on_skin=True,
        fields=[Field(ResultFieldName.displacement, [Component.X, Component.Y, Component.Z])],
    )
    existing_view_ids = {v.id for v in sol.views}
    plot_def = sol.create_plot(plot_def).definition

    new_plot_views = [v for v in sol.plot_views if v.id not in existing_view_ids]
    view = next((v for v in new_plot_views if v.name == plot_def.name), None)
    assert view is not None

    # modify the plot definition and make sure the view name is updated
    plot_def.name = "Renamed plot"
    plot_def = sol.update_plot(plot_def).definition

    view = next((v for v in sol.views if v.id == view.id), None)
    assert view is not None
    assert view.name == "Renamed plot"


def test_new_plot_no_components(rx: Client, cp_transient_solution: Solution):
    """Cover known issue with "total" fields that have no components."""

    sol = cp_transient_solution

    plot_def = PlotDefinition(
        result_type=ResultType.displacement,
        location=Location.nodal,
        name="New plot",
        last_set=True,
        all_sets=False,
        on_skin=True,
        fields=[Field(ResultFieldName.total_displacement, components=None)],
    )

    with pytest.raises(ResultExplorerError, match="known issue"):
        _ = sol.create_plot(plot_def)

    # once the issue will be fixed, we can uncomment the following lines
    # # assign view to a workspace and make sure it renders without error
    # workspace = rx.create_workspace("New plot workspace")
    # viewport = workspace.assign_view(view=view, wait=True)

    # meta = viewport.metadata
    # assert isinstance(meta, PlotViewportMetadata)
    # assert meta.active_result.max == pytest.approx(1.187e-4, rel=1e-3)
    # assert meta.active_result.min == 0.0

    # rx.delete_workspace(workspace)


def test_plot_using_python_plot_definition(multiple_connections_solution: Solution):
    """Create, update and delete a plot using the native Python PlotDefinition."""
    sol = multiple_connections_solution

    py_def = PlotDefinition(
        result_type=ResultType.stress,
        location=Location.nodal,
        name="Python stress plot",
        fields=[Field(ResultFieldName.equivalent_von_mises_stress)],
        shell_position=ShellPosition.middle,
        all_sets=True,
        last_set=False,
    )

    plot_view = sol.create_plot(py_def)
    plot_def = plot_view.definition

    assert plot_def.id is not None
    assert plot_def.name == "Python stress plot"
    assert plot_def.result_type == ResultType.stress
    assert plot_def.shell_position == ShellPosition.middle

    # update via Python PlotDefinition
    py_def.id = plot_def.id
    py_def.name = "Python stress plot (updated)"
    updated_view = sol.update_plot(py_def)
    assert updated_view.definition.name == "Python stress plot (updated)"

    # delete via Python PlotDefinition
    sol.delete_plot(py_def)
    assert next((p for p in sol.plots if p.id == plot_def.id), None) is None


class TestPlotDefinitionConversion:
    """Check converting between PlotDefinition and its protobuf representation."""

    def test_to_proto_create(self):
        py_def = PlotDefinition(
            result_type=ResultType.stress,
            location=Location.nodal,
            name="My stress plot",
            fields=[
                Field(ResultFieldName.equivalent_von_mises_stress),
                Field(ResultFieldName.stress_tensor, [Component.XX, Component.ZZ]),
            ],
            shell_position=ShellPosition.middle,
            all_sets=True,
            last_set=False,
            named_selection_id="ns-123",
            set_ids=[1, 2, 3],
            id="plot-456",
        )

        proto = plot_definition_to_proto(py_def, models.PlotDefinitionCreate)

        assert proto.result_type == models.ResultType.RESULT_TYPE_STRESS
        assert proto.location == "Nodal"
        assert proto.name == "My stress plot"
        assert proto.shell_position == models.ShellPosition.SHELL_POSITION_MIDDLE
        assert proto.all_sets is True
        assert proto.last_set is False
        assert proto.named_selection_id == "ns-123"
        assert list(proto.set_ids) == [1, 2, 3]
        assert proto.id == "plot-456"
        assert len(proto.fields) == 2
        assert proto.fields[0].name == "equivalent_von_mises_stress"
        assert proto.fields[1].name == "stress_tensor"
        assert list(proto.fields[1].components) == ["XX", "ZZ"]

    def test_to_proto_custom_options(self):
        py_def = PlotDefinition(
            result_type=ResultType.user_defined,
            location="Nodal",
            custom_options={"threshold": 1.5, "label": "peak", "count": 3, "active": True},
        )

        proto = plot_definition_to_proto(py_def, models.PlotDefinitionCreate)

        assert proto.custom_options["threshold"].float == pytest.approx(1.5)
        assert proto.custom_options["label"].string == "peak"
        assert proto.custom_options["count"].int32 == 3
        assert proto.custom_options["active"].bool is True

    def test_from_proto_custom_options(self):
        proto = models.PlotDefinitionCreate(
            result_type=models.ResultType.RESULT_TYPE_USER_DEFINED,
            location="Nodal",
        )
        proto.custom_options["threshold"].float = 1.5
        proto.custom_options["label"].string = "peak"
        proto.custom_options["count"].int32 = 3
        proto.custom_options["active"].bool = True

        py_def = proto_to_plot_definition(proto)

        assert py_def.custom_options["threshold"] == pytest.approx(1.5)
        assert py_def.custom_options["label"] == "peak"
        assert py_def.custom_options["count"] == 3
        assert py_def.custom_options["active"] is True

    def test_round_trip_custom_options(self):
        original = PlotDefinition(
            result_type=ResultType.user_defined,
            location="Nodal",
            custom_options={"threshold": 2.5, "label": "top", "count": 7, "active": False},
        )

        proto = plot_definition_to_proto(original, models.PlotDefinitionCreate)
        restored = proto_to_plot_definition(proto)

        assert restored.custom_options["threshold"] == pytest.approx(2.5)
        assert restored.custom_options["label"] == "top"
        assert restored.custom_options["count"] == 7
        assert restored.custom_options["active"] is False

    def test_from_proto_create(self):
        proto = models.PlotDefinitionCreate(
            result_type=models.ResultType.RESULT_TYPE_VELOCITY,
            location="Nodal",
            name="velocity plot",
            shell_position=models.ShellPosition.SHELL_POSITION_TOP,
            all_sets=False,
            last_set=True,
            named_selection_id="ns-abc",
            set_ids=[5],
            fields=[models.Field(name="velocity", components=["X", "Y", "Z"])],
        )

        py_def = proto_to_plot_definition(proto)

        assert py_def.result_type == ResultType.velocity
        assert py_def.location == "Nodal"
        assert py_def.name == "velocity plot"
        assert py_def.shell_position == ShellPosition.top  # TOP=0 is proto default, maps to top
        assert py_def.all_sets is False
        assert py_def.last_set is True
        assert py_def.named_selection_id == "ns-abc"
        assert py_def.set_ids == [5]
        assert py_def.supports_monitoring is None
        assert len(py_def.fields) == 1
        assert py_def.fields[0].name == ResultFieldName.velocity
        assert py_def.fields[0].components == [Component.X, Component.Y, Component.Z]

    def test_from_proto_definition(self):
        proto = models.PlotDefinition(
            id="plot-789",
            result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
            location="Nodal",
            name="displacement plot",
            supports_monitoring=True,
            creation_time="2026-01-01T00:00:00Z",
            fields=[models.Field(name="total_displacement")],
        )

        py_def = proto_to_plot_definition(proto)

        assert py_def.id == "plot-789"
        assert py_def.result_type == ResultType.displacement
        assert py_def.name == "displacement plot"
        assert py_def.supports_monitoring is True
        assert py_def.creation_time == "2026-01-01T00:00:00Z"
        assert len(py_def.fields) == 1
        assert py_def.fields[0].name == ResultFieldName.total_displacement
        assert py_def.fields[0].components is None

    def test_round_trip(self):
        original = PlotDefinition(
            result_type=ResultType.stress,
            location="Nodal",
            name="round-trip plot",
            fields=[
                Field(ResultFieldName.stress_tensor, [Component.XX, Component.YY, Component.ZZ]),
            ],
            shell_position=ShellPosition.bottom,
            all_sets=False,
            last_set=True,
            named_selection_id="ns-rt",
            set_ids=[2, 4],
            on_skin=False,
            include_displacement=True,
            id="plot-rt",
        )

        proto = plot_definition_to_proto(original, models.PlotDefinitionCreate)
        restored = proto_to_plot_definition(proto)

        assert restored.result_type == original.result_type
        assert restored.location == original.location
        assert restored.name == original.name
        assert restored.shell_position == original.shell_position
        assert restored.all_sets == original.all_sets
        assert restored.last_set == original.last_set
        assert restored.named_selection_id == original.named_selection_id
        assert restored.set_ids == original.set_ids
        assert restored.on_skin == original.on_skin
        assert restored.include_displacement == original.include_displacement
        assert restored.id == original.id
        assert len(restored.fields) == 1
        assert restored.fields[0].name == ResultFieldName.stress_tensor
        assert restored.fields[0].components == [Component.XX, Component.YY, Component.ZZ]

    def test_to_proto_method(self):
        py_def = PlotDefinition(
            result_type=ResultType.velocity,
            location="Nodal",
            shell_position=ShellPosition.middle,
        )

        proto = py_def.to_proto(models.PlotDefinitionCreate)

        assert proto.result_type == models.ResultType.RESULT_TYPE_VELOCITY
        assert proto.shell_position == models.ShellPosition.SHELL_POSITION_MIDDLE

    def test_from_proto_classmethod(self):
        proto = models.PlotDefinition(
            id="plot-cm",
            result_type=models.ResultType.RESULT_TYPE_STRESS,
            location="Elemental",
            name="stress plot",
            supports_monitoring=False,
        )

        py_def = PlotDefinition.from_proto(proto)

        assert py_def.id == "plot-cm"
        assert py_def.result_type == ResultType.stress
        assert py_def.location == "Elemental"
        assert py_def.supports_monitoring is False

    def test_result_type_enum_matches_proto(self):
        """Verify that ResultType enum items match 100% with models.ResultType."""
        # Check each Python ResultType has a corresponding proto constant
        for py_result in ResultType:
            proto_name = f"RESULT_TYPE_{py_result.name.upper()}"
            assert proto_name in models.ResultType.DESCRIPTOR.values_by_name, (
                f"Missing proto constant: {proto_name} for Python ResultType.{py_result.name}"
            )

        # Check each proto RESULT_TYPE_* constant has a Python equivalent
        proto_values = models.ResultType.DESCRIPTOR.values_by_name.keys()
        for proto_name in proto_values:
            py_name = proto_name.removeprefix("RESULT_TYPE_").lower()
            assert hasattr(ResultType, py_name), (
                f"Missing Python ResultType.{py_name} for proto constant: {proto_name}"
            )
            py_result = getattr(ResultType, py_name)
            # Verify the Python enum value is valid
            assert isinstance(py_result, ResultType)
