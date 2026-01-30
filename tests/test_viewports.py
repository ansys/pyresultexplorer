import pytest

from ansys.result_explorer.core.models import ViewportDirection


@pytest.fixture
def multiple_connections_solution(rx, rst_multiple_connections):
    sol = rx.create_solution(
        name="Test Solution",
        result_provider_name="Local",
        file_path=rst_multiple_connections,
    )
    yield sol
    rx.delete_solution(sol)


def test_viewports(rx, multiple_connections_solution):
    sol = multiple_connections_solution

    # find displacement view
    views = sol.views

    view = next((v for v in views if "Displacement" in v.name), None)
    assert view is not None

    # assign view to viewport
    workspace = rx.create_workspace("Test Workspace")
    viewport = workspace.assign_view(view=view, wait=True)

    assert viewport.id in workspace.viewport_ids
    assert view.id == view.id

    # list viewports
    viewports = workspace.viewports
    assert len(viewports) >= 1

    # modify metadata
    meta = viewport.metadata
    meta.show_mesh_edges = not meta.show_mesh_edges
    meta.show_min_max_labels = not meta.show_min_max_labels

    viewport.modify_view_metadata(meta)

    # get workspace to refresh viewport
    assert viewport.metadata.show_mesh_edges == meta.show_mesh_edges

    # take snapshot
    snapshot_data = viewport.take_snapshot()
    assert len(snapshot_data) > 0

    # split viewport to create a 2x1 layout
    bottom_viewport = workspace.create_viewport(
        viewport, ViewportDirection.VIEWPORT_DIRECTION_BOTTOM
    )

    # get workspace and verify new viewport
    workspace = rx.get_workspace(workspace.id)
    assert len(workspace.viewport_ids) == 2
    assert bottom_viewport.id in workspace.viewport_ids

    # set viewport to fullscreen
    workspace.set_fullscreen_viewport(bottom_viewport)
    assert workspace.fullscreen_viewport_id == bottom_viewport.id
    workspace = rx.get_workspace(workspace.id)
    assert workspace.fullscreen_viewport_id == bottom_viewport.id

    # exit fullscreen
    workspace.exit_fullscreen()
    assert workspace.fullscreen_viewport_id == ""
    workspace = rx.get_workspace(workspace.id)
    assert workspace.fullscreen_viewport_id == ""

    # delete viewport
    workspace.delete_viewport(bottom_viewport)
    assert len(workspace.viewport_ids) == 1

    # get workspace and verify deletion
    workspace = rx.get_workspace(workspace.id)
    assert len(workspace.viewport_ids) == 1
