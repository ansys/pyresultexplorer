import pytest

from ansys.result_explorer.core import models


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


def test_solution_properties(rst_solution):
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
    assert "MKS" in sol.unit_system

    assert len(sol.views) > 1

    assert (
        len(sol.bodies) == 4
    )  # temporarily because splitMeshBy is defaulted to false in the web api
    assert sol.unsupported_element_types[0] == "SURF154"


@pytest.mark.xfail(reason="View types not properly returned")
def test_view_types(rst_solution):
    sol = rst_solution

    view_types = {v.type for v in sol.views}

    assert models.ViewType.VIEW_TYPE_SURFACE_MESH in view_types
    assert models.ViewType.VIEW_TYPE_SURFACE_MESH_WITH_INTERFACES in view_types
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
