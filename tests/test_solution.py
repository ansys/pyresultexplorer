import logging
from pathlib import Path

import pytest

from ansys.result_explorer.core import models
from ansys.result_explorer.core.entities import Solution

log = logging.getLogger(__name__)


def test_solution(rx, rst_multiple_connections):
    """CRUD operations for solutions."""

    # create a new solution
    sol = rx.create_solution(
        name="Test Solution",
        result_provider_name="Local",
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
        result_provider_name="Local",
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
        (p for p in sol.plots if p.result_type == models.ResultType.RESULT_TYPE_STRESS),
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
        result_provider="Local",
    )
    assert "ANSYS RELEASE" in err_content
    assert "*** WARNING ***" in err_content

    gst_content = sol._client._get_file_content(
        path=str(cp_trans_path / "file.gst"),
        result_provider="Local",
    )
    assert "<SOLUTION>" in gst_content
    assert "<LOADSTEPDATA>" in gst_content
