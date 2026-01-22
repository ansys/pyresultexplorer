from ansys.result_explorer.core.models import ViewportDirection


def test_viewports(rx, rst_multiple_connections):
    # create a new solution
    sol = rx.create_solution(
        name="Test Solution",
        result_provider_name="Local",
        file_path=rst_multiple_connections,
    )

    # find displacement view
    views = sol.views

    view = next((v for v in views if "Displacement" in v.name), None)
    assert view is not None

    # assign view to viewport
    workspace = rx.list_workspaces()[0]
    viewport = rx.assign_view(
        viewport_id=workspace.viewport_ids[0], solution_id=sol.id, view_id=view.id, wait=True
    )

    assert viewport.solution_id == sol.id
    assert viewport.view_id == view.id
    assert viewport.ready is True

    # list viewports
    viewports = rx.list_viewports(workspace_id=workspace.id)
    assert len(viewports) == 1
    assert viewports[0].id == viewport.id

    # take snapshot
    snapshot_data = rx.take_snapshot(viewport_id=viewport.id)
    assert len(snapshot_data) > 0

    # split viewport to create a 2x1 layout
    bottom_viewport = rx.create_viewport(
        workspace_id=workspace.id,
        viewport_id=viewport.id,
        direction=ViewportDirection.VIEWPORT_DIRECTION_BOTTOM,
    )

    # get workspace and verify new viewport
    workspace = rx.get_workspace(workspace_id=workspace.id)
    assert len(workspace.viewport_ids) == 2
    assert bottom_viewport.id in workspace.viewport_ids

    # set viewport to fullscreen
    workspace = rx.set_fullscreen_viewport(
        workspace_id=workspace.id, viewport_id=bottom_viewport.id
    )
    assert workspace.fullscreen_viewport_id == bottom_viewport.id

    # exit fullscreen
    workspace = rx.exit_fullscreen(workspace_id=workspace.id)
    assert workspace.fullscreen_viewport_id == ""

    # delete viewport
    rx.delete_viewport(viewport_id=bottom_viewport.id)

    # get workspace and verify deletion
    workspace = rx.get_workspace(workspace_id=workspace.id)
    assert len(workspace.viewport_ids) == 1
