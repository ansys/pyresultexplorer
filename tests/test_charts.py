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

from ansys.result_explorer.core import models
from ansys.result_explorer.core.objects import Solution
from ansys.result_explorer.core.objects.chart_definition import (
    ChartDefinition,
    ChartResult,
    Filter,
    chart_definition_to_proto,
    proto_to_chart_definition,
)
from ansys.result_explorer.core.objects.plot_definition import (
    Component,
    Field,
    ResultFieldName,
    ResultType,
    ShellPosition,
)

log = logging.getLogger(__name__)


def test_chart(multiple_connections_solution: Solution):
    """CRUD operations for chart."""

    sol = multiple_connections_solution

    # create a new chart
    chart_def = ChartDefinition(
        name="My chart",
        user_defined=False,
        all_sets=True,
        results=[
            ChartResult(
                result_type=ResultType.stress,
                name="Stress",
                location="Nodal",
                fields=[
                    Field(ResultFieldName.equivalent_von_mises_stress),
                    Field(ResultFieldName.stress_tensor, [Component.XX, Component.ZZ]),
                ],
                filters=[Filter.max],
            )
        ],
    )

    chart_def = sol.create_chart(chart_def).definition

    assert chart_def.id is not None
    assert chart_def.name == "My chart"
    assert chart_def.user_defined is False
    assert chart_def.all_sets is True
    assert len(chart_def.results) == 1
    assert chart_def.results[0].filters[0] == Filter.max

    # verify the chart is in the solution's charts
    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is not None
    assert chart_def_in_sol.results[0].name == "Stress"
    assert chart_def_in_sol.results[0].fields[0].name == "equivalent_von_mises_stress"
    assert chart_def_in_sol.results[0].fields[1].name == "stress_tensor"
    assert chart_def_in_sol.results[0].fields[1].components == ["XX", "ZZ"]

    # update the chart
    chart_def.name = "Updated chart"
    chart_def.results[0].name = "Updated Stress"
    chart_def = sol.update_chart(chart_def).definition

    assert chart_def.name == "Updated chart"

    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is not None
    assert chart_def_in_sol.name == "Updated chart"
    assert chart_def_in_sol.results[0].name == "Updated Stress"

    # delete the chart
    sol.delete_chart(chart_def)
    chart_def_in_sol = next((c for c in sol.charts if c.id == chart_def.id), None)
    assert chart_def_in_sol is None

    chart_def_in_views = next(
        (
            v
            for v in sol.views
            if v.type == models.ViewType.VIEW_TYPE_CHART and v.id == chart_def.id
        ),
        None,
    )
    assert chart_def_in_views is None


def test_chart_view_no_definition(multiple_connections_solution: Solution):

    sol = multiple_connections_solution

    chart_def = ChartDefinition(
        name="My chart",
        user_defined=False,
        all_sets=True,
        results=[
            ChartResult(
                result_type=ResultType.stress,
                name="Stress",
                location="Nodal",
                fields=[
                    Field(ResultFieldName.equivalent_von_mises_stress),
                    Field(ResultFieldName.stress_tensor, [Component.XX, Component.ZZ]),
                ],
                filters=[Filter.max],
            )
        ],
    )

    chart_view = sol.create_chart(chart_def)
    chart_def = chart_view.definition

    # delete the chart view
    sol.delete_chart(chart_def.id)

    with pytest.raises(RuntimeError, match="not found"):
        _ = chart_view.definition


def test_new_chart_added_to_views(multiple_connections_solution: Solution):
    """Ensure that a new chart is added to the solution's views."""

    sol = multiple_connections_solution

    chart_def = ChartDefinition(
        name="My chart",
        user_defined=False,
        all_sets=True,
        results=[
            ChartResult(
                result_type=ResultType.stress,
                name="Stress",
                location="Nodal",
                fields=[
                    Field(ResultFieldName.equivalent_von_mises_stress),
                ],
                filters=[Filter.max],
            )
        ],
    )
    existing_view_ids = {v.id for v in sol.views}
    chart_def = sol.create_chart(chart_def).definition

    new_chart_views = [v for v in sol.chart_views if v.id not in existing_view_ids]
    view = next((v for v in new_chart_views if v.name == chart_def.name), None)
    assert view is not None

    # modify the chart definition and make sure the view name is updated
    chart_def.name = "Renamed chart"
    chart_def = sol.update_chart(chart_def).definition

    view = next((v for v in sol.views if v.id == view.id), None)
    assert view is not None
    assert view.name == "Renamed chart"


class TestChartDefinitionConversion:
    """Check converting between ChartDefinition and its protobuf representation."""

    def test_to_proto_create(self):
        py_def = ChartDefinition(
            name="My chart",
            results=[
                ChartResult(
                    result_type=ResultType.stress,
                    name="Stress",
                    location="Nodal",
                    fields=[
                        Field(ResultFieldName.equivalent_von_mises_stress),
                        Field(ResultFieldName.stress_tensor, [Component.XX, Component.ZZ]),
                    ],
                    filters=[Filter.max],
                    shell_position=ShellPosition.middle,
                )
            ],
            all_sets=True,
            set_ids=None,
            id="chart-123",
        )

        proto = chart_definition_to_proto(py_def, models.ChartDefinitionCreate)

        assert proto.name == "My chart"
        assert proto.id == "chart-123"
        assert proto.all_sets is True
        assert len(proto.results) == 1
        r = proto.results[0]
        assert r.result_type == models.ResultType.RESULT_TYPE_STRESS
        assert r.name == "Stress"
        assert r.location == "Nodal"
        assert r.shell_position == models.ShellPosition.SHELL_POSITION_MIDDLE
        assert list(r.filters) == [models.Filter.FILTER_MAX]
        assert len(r.fields) == 2
        assert r.fields[0].name == "equivalent_von_mises_stress"
        assert r.fields[1].name == "stress_tensor"
        assert list(r.fields[1].components) == ["XX", "ZZ"]

    def test_to_proto_custom_options(self):
        py_def = ChartDefinition(
            name="Custom chart",
            custom_options={"threshold": 1.5, "label": "peak", "count": 3, "active": True},
        )

        proto = chart_definition_to_proto(py_def, models.ChartDefinitionCreate)

        assert proto.custom_options["threshold"].float == pytest.approx(1.5)
        assert proto.custom_options["label"].string == "peak"
        assert proto.custom_options["count"].int32 == 3
        assert proto.custom_options["active"].bool is True

    def test_from_proto_create(self):
        proto = models.ChartDefinitionCreate(
            name="velocity chart",
            all_sets=False,
            set_ids=[5],
            user_defined=False,
            results=[
                models.ChartResult(
                    result_type=models.ResultType.RESULT_TYPE_VELOCITY,
                    name="Velocity",
                    location="Nodal",
                    shell_position=models.ShellPosition.SHELL_POSITION_TOP,
                    fields=[models.Field(name="velocity", components=["X", "Y", "Z"])],
                    filters=[models.Filter.FILTER_MIN],
                )
            ],
        )

        py_def = proto_to_chart_definition(proto)

        assert py_def.name == "velocity chart"
        assert py_def.all_sets is False
        assert py_def.set_ids == [5]
        assert py_def.user_defined is False
        assert py_def.supports_monitoring is None
        assert len(py_def.results) == 1
        r = py_def.results[0]
        assert r.result_type == ResultType.velocity
        assert r.name == "Velocity"
        assert r.location == "Nodal"
        assert r.shell_position == ShellPosition.top
        assert r.filters == [Filter.min]
        assert len(r.fields) == 1
        assert r.fields[0].name == ResultFieldName.velocity
        assert r.fields[0].components == [Component.X, Component.Y, Component.Z]

    def test_from_proto_definition(self):
        proto = models.ChartDefinition(
            id="chart-789",
            name="displacement chart",
            supports_monitoring=True,
            creation_time="2026-01-01T00:00:00Z",
            all_sets=True,
            results=[
                models.ChartResult(
                    result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
                    name="Displacement",
                    fields=[models.Field(name="total_displacement")],
                )
            ],
        )

        py_def = proto_to_chart_definition(proto)

        assert py_def.id == "chart-789"
        assert py_def.name == "displacement chart"
        assert py_def.supports_monitoring is True
        assert py_def.creation_time == "2026-01-01T00:00:00Z"
        assert py_def.all_sets is True
        assert len(py_def.results) == 1
        assert py_def.results[0].result_type == ResultType.displacement
        assert py_def.results[0].name == "Displacement"
        assert py_def.results[0].fields[0].name == ResultFieldName.total_displacement

    def test_from_proto_custom_options(self):
        proto = models.ChartDefinitionCreate(name="chart")
        proto.custom_options["threshold"].float = 1.5
        proto.custom_options["label"].string = "peak"
        proto.custom_options["count"].int32 = 3
        proto.custom_options["active"].bool = True

        py_def = proto_to_chart_definition(proto)

        assert py_def.custom_options["threshold"] == pytest.approx(1.5)
        assert py_def.custom_options["label"] == "peak"
        assert py_def.custom_options["count"] == 3
        assert py_def.custom_options["active"] is True

    def test_round_trip(self):
        original = ChartDefinition(
            name="round-trip chart",
            results=[
                ChartResult(
                    result_type=ResultType.stress,
                    name="Stress",
                    location="Nodal",
                    fields=[
                        Field(ResultFieldName.stress_tensor, [Component.XX, Component.YY]),
                    ],
                    filters=[Filter.max, Filter.min],
                    shell_position=ShellPosition.bottom,
                    on_skin=False,
                )
            ],
            all_sets=False,
            set_ids=[2, 4],
            user_defined=False,
            named_selection_id="ns-rt",
            id="chart-rt",
        )

        proto = chart_definition_to_proto(original, models.ChartDefinitionCreate)
        restored = proto_to_chart_definition(proto)

        assert restored.name == original.name
        assert restored.all_sets == original.all_sets
        assert restored.set_ids == original.set_ids
        assert restored.named_selection_id == original.named_selection_id
        assert restored.id == original.id
        assert len(restored.results) == 1
        r = restored.results[0]
        assert r.result_type == ResultType.stress
        assert r.name == "Stress"
        assert r.location == "Nodal"
        assert r.shell_position == ShellPosition.bottom
        assert r.filters == [Filter.max, Filter.min]
        assert r.on_skin is False
        assert r.fields[0].name == ResultFieldName.stress_tensor
        assert r.fields[0].components == [Component.XX, Component.YY]

    def test_round_trip_custom_options(self):
        original = ChartDefinition(
            name="custom opts chart",
            custom_options={"threshold": 2.5, "label": "top", "count": 7, "active": False},
        )

        proto = chart_definition_to_proto(original, models.ChartDefinitionCreate)
        restored = proto_to_chart_definition(proto)

        assert restored.custom_options["threshold"] == pytest.approx(2.5)
        assert restored.custom_options["label"] == "top"
        assert restored.custom_options["count"] == 7
        assert restored.custom_options["active"] is False

    def test_to_proto_method(self):
        py_def = ChartDefinition(
            name="method chart",
            results=[
                ChartResult(
                    result_type=ResultType.velocity,
                    shell_position=ShellPosition.middle,
                )
            ],
        )

        proto = py_def.to_proto(models.ChartDefinitionCreate)

        assert proto.name == "method chart"
        assert proto.results[0].result_type == models.ResultType.RESULT_TYPE_VELOCITY
        assert proto.results[0].shell_position == models.ShellPosition.SHELL_POSITION_MIDDLE

    def test_from_proto_classmethod(self):
        proto = models.ChartDefinition(
            id="chart-cm",
            name="classmethod chart",
            supports_monitoring=False,
            all_sets=True,
        )

        py_def = ChartDefinition.from_proto(proto)

        assert py_def.id == "chart-cm"
        assert py_def.name == "classmethod chart"
        assert py_def.supports_monitoring is False
        assert py_def.all_sets is True
