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
from pathlib import Path

import pytest

from ansys.result_explorer.core import models
from ansys.result_explorer.core.objects import ChartDefinition, ResultType, Solution, View

log = logging.getLogger(__name__)


def test_solution(rx, rst_multiple_connections):
    """CRUD operations for solutions."""

    # create a new solution
    sol = rx.create_solution(
        name="Test Solution",
        file_path=rst_multiple_connections,
    )

    assert sol.name == "Test Solution"
    assert sol.id is not None
    assert sol.n_elements == 246
    assert sol.n_nodes == 844

    # list solutions
    solutions = rx.list_solutions()
    assert any(s.id == sol.id for s in solutions)

    # get solution
    fetched_sol = rx.get_solution(sol.id)
    assert fetched_sol.id == sol.id
    assert fetched_sol.name == sol.name
    assert fetched_sol.n_elements == sol.n_elements
    assert len(fetched_sol.views) > 0

    # delete solution
    rx.delete_solution(sol)

    # verify deletion
    solutions = rx.list_solutions()
    assert all(s.id != sol.id for s in solutions)


@pytest.fixture
def rst_solution(rx, rst_multiple_connections):
    sol = rx.create_solution(
        name="Test Solution",
        file_path=rst_multiple_connections,
    )
    yield sol
    rx.delete_solution(sol)


def test_solution_properties(rst_solution: Solution):
    sol = rst_solution

    assert sol.name == "Test Solution"
    assert sol.id is not None

    assert sol.n_elements == 246
    assert sol.n_nodes == 844
    assert sol.n_sets == 1
    assert sol.analysis_type == "static"
    assert sol.physics_type == "mechanical"
    assert sol.solver_version == "24.1"
    assert len(sol.files) == 1
    assert sol.files[0].key == "rst"

    assert len(sol.available_mesh_properties) > 0
    assert "mat" in [prop.id for prop in sol.available_mesh_properties]

    assert len(sol.views) > 1

    assert len(sol.bodies) == 18
    body10 = next((b for b in sol.bodies if b.id == "10"), None)
    assert body10 is not None
    assert body10.labels["mat"] == "9"
    assert body10.labels["apdl_element_type"] == "175"
    assert body10.labels["apdl_element_type"] == "175"
    assert body10.element_types == ["CONTA175"]

    assert sol.unsupported_element_types[0] == "SURF154"

    assert len(sol.solver_named_selections) > 0

    assert len(sol.time_frequencies) == 1
    assert sol.time_frequencies[0].value == 1.0
    assert sol.time_frequencies[0].set_id == 1
    assert sol.time_frequencies[0].step == 1
    assert sol.time_frequencies[0].substep == 1

    assert len(sol.element_groups) == 5
    assert models.ElementGroup.ELEMENT_GROUP_SOLID in sol.element_groups
    assert models.ElementGroup.ELEMENT_GROUP_MPC in sol.element_groups

    assert "MKS" in sol.unit_system
    assert sol.distance_unit == "m"
    assert sol.solver_version == "24.1"

    # find configurable stress plot
    stress_plot = next(  # noqa
        (
            v
            for v in sol.configurable_plots
            if v.result_type == models.ResultType.RESULT_TYPE_STRESS
        ),
        None,
    )
    assert stress_plot is not None

    # find stress plot
    stress_plot_def = next(
        (p for p in sol.plots if p.result_type == ResultType.stress),
        None,
    )
    assert stress_plot_def is not None
    assert stress_plot_def.last_set is True
    assert stress_plot_def.fields[0].name is not None

    # find configurable displacement chart
    disp_chart = next(
        (
            v
            for v in sol.configurable_charts
            if v.results[0].result_type == models.ResultType.RESULT_TYPE_DISPLACEMENT
        ),
        None,
    )
    assert disp_chart is not None
    assert models.Filter.FILTER_MIN in disp_chart.results[0].filters
    assert models.Filter.FILTER_MAX in disp_chart.results[0].filters

    # test named selections
    assert len(sol.named_selections) == len(sol.solver_named_selections)
    ns = next((ns for ns in sol.named_selections if ns.name == "_FIXEDSU"), None)
    assert ns is not None
    assert ns.type == models.NamedSelectionType.NAMED_SELECTION_TYPE_SOLVER_NAMED_SELECTION
    assert ns.size == 80
    assert ns.location == "Nodal"

    # Test uncovered properties
    assert isinstance(sol.description, str)
    assert isinstance(sol.cache_plot_data, bool)
    assert isinstance(sol.creation_time, str)
    assert isinstance(sol.ready, bool)
    assert isinstance(sol.errors, list)
    assert isinstance(sol.live, bool)
    assert isinstance(sol.outdated, bool)

    # Test collections
    assert len(sol.available_results) > 0
    assert isinstance(sol.available_results[0], models.AvailableResult)

    assert isinstance(sol.available_trackers, list)

    # Test available_custom_selections
    assert isinstance(sol.available_custom_selections, list)

    # Test charts property
    assert len(sol.charts) > 0
    assert isinstance(sol.charts[0], ChartDefinition)

    # Test result_provider property
    result_provider = sol.result_provider
    assert result_provider is not None
    assert sol.id in result_provider.solution_ids


def test_solution_string_representation(cp_transient_solution: Solution):
    sol = cp_transient_solution

    str_repr = str(sol)

    log.info("String representation of solution:\n%s", str_repr)

    # Check that the string contains key information
    assert "Solution:" in str_repr
    assert sol.name in str_repr
    assert sol.id in str_repr
    assert "Analysis Information:" in str_repr
    assert "Mesh Information:" in str_repr
    assert "Results Information:" in str_repr
    assert "Status:" in str_repr
    assert "Ready" in str_repr
    assert "Available Plot Results" in str_repr
    assert "Solver Text Outputs" in str_repr
    assert "solve.out" in str_repr


def test_view_types(rst_solution: Solution):
    sol = rst_solution

    view_types = {v.type for v in sol.views}

    assert models.ViewType.VIEW_TYPE_MESH in view_types
    assert models.ViewType.VIEW_TYPE_PLOT in view_types
    assert models.ViewType.VIEW_TYPE_CHART in view_types

    # find displacement view
    disp_view = next(
        (
            v
            for v in sol.views
            if "displacement" in v.name.lower() and v.type == models.ViewType.VIEW_TYPE_PLOT
        ),
        None,
    )
    assert disp_view is not None


def test_solution_out_files(data_directory, cp_transient_solution: Solution):
    sol = cp_transient_solution

    cp_trans_path = Path(data_directory) / "cp_trans"

    # list cp_trans folder content through filesystem API
    content = sol._client.ls(path=str(cp_trans_path), result_provider="Local", depth=0)
    file_names = {item.name for item in content if item.is_file}

    expected_files = {
        "ds.dat",
        "file.cnd",
        "file.err",
        "file.gst",
        "file.nr001",
        "file.nr002",
        "file.nr003",
        "file.rst",
        "solve.out",
    }
    assert expected_files.issubset(file_names)

    # validate solver text outputs discovered on the solution
    solver_out_files = sol.solver_text_outputs
    assert len(solver_out_files) > 0

    solver_out_names = {f.name for f in solver_out_files}
    assert "solve.out" in solver_out_names

    # get out file content through solution API
    solve_out = next((f for f in solver_out_files if f.name == "solve.out"), None)
    assert solve_out is not None

    content_from_obj = sol.get_solver_out_content(solve_out)
    assert isinstance(content_from_obj, str)
    assert len(content_from_obj) > 0
    assert "MAPDL 2024 R2" in content_from_obj

    content_from_name = sol.get_solver_out_content("solve.out")
    assert content_from_name == content_from_obj

    # validate content of additional cp_trans files through filesystem API
    err_content = sol._client._get_file_content(
        path=str(cp_trans_path / "file.err"),
    )
    assert "ANSYS RELEASE" in err_content
    assert "*** WARNING ***" in err_content

    gst_content = sol._client._get_file_content(
        path=str(cp_trans_path / "file.gst"),
    )
    assert "<SOLUTION>" in gst_content
    assert "<LOADSTEPDATA>" in gst_content


def test_mesh_options_with_processing_mode(rx, rst_multiple_connections):
    original_settings = rx.app_settings()
    original_mode = original_settings.data_processing.processing_mode
    if original_mode == models.ProcessingMode.PROCESSING_MODE_FULL:
        new_mode = models.ProcessingMode.PROCESSING_MODE_SKIN
        expected_on_skin = True
    else:
        new_mode = models.ProcessingMode.PROCESSING_MODE_FULL
        expected_on_skin = False

    try:
        settings = models.AppSettings()
        settings.CopyFrom(original_settings)
        settings.data_processing.processing_mode = new_mode
        rx.update_app_settings(settings)

        updated_settings = rx.app_settings()
        assert updated_settings.data_processing.processing_mode == new_mode

        sol = rx.create_solution(
            name="Test Solution - Data Processing",
            file_path=rst_multiple_connections,
        )

        assert sol.mesh_options.on_skin == expected_on_skin
        assert sol.mesh_options.as_linear is True

        mesh_view = next((v for v in sol.views if v.type == models.ViewType.VIEW_TYPE_MESH), None)
        assert mesh_view is not None
        assert mesh_view.options.on_skin == expected_on_skin

        # Cleanup
        rx.delete_solution(sol)

    finally:
        restored_settings = models.AppSettings()
        restored_settings.CopyFrom(original_settings)
        restored_settings.data_processing.processing_mode = original_mode
        rx.update_app_settings(restored_settings)

        final_settings = rx.app_settings()
        assert final_settings.data_processing.processing_mode == original_mode


def test_solver_text_output_invalid_file(rst_solution: Solution):
    """Test get_solver_out_content with invalid file."""
    sol = rst_solution

    with pytest.raises(ValueError, match="not found"):
        sol.get_solver_out_content("nonexistent_file.out")


def test_solution_views(cp_transient_solution: Solution):

    sol = cp_transient_solution

    assert sol.logs_view is not None
    assert sol.mesh_view is not None
    assert len(sol.plot_views) == len(
        [v for v in sol.views if v.type == models.ViewType.VIEW_TYPE_PLOT]
    )
    assert len(sol.chart_views) == len(
        [v for v in sol.views if v.type == models.ViewType.VIEW_TYPE_CHART]
    )
    assert isinstance(sol.contact_trackers_view, View)
    assert isinstance(sol.contact_trackers_view, View)
    assert isinstance(sol.logs_view, View)
    assert sol.mesh_view.options is not None


def test_solution_warnings(cp_transient_solution: Solution):

    sol = cp_transient_solution

    assert len(sol.errors) == 0
    assert len(sol.warnings) > 0
