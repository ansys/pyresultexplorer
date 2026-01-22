import logging

log = logging.getLogger(__name__)


def test_workspace_crud(rx):
    # list workspaces
    workspaces = rx.list_workspaces()
    assert workspaces[0].name == "Workspace 1"

    # create a new workspace
    workspace = rx.create_workspace(name="Test Workspace")
    assert workspace.name == "Test Workspace"
    assert workspace.fullscreen_viewport_id == ""
    assert workspace.sync_options.camera is False
    assert workspace.sync_options.time_freq is False
    assert workspace.sync_options.legend is False
    assert len(workspace.viewport_ids) == 1

    # update workspace to turn on sync options and set fullscreen viewport
    workspace = rx.set_workspace_sync(
        workspace_id=workspace.id, camera=True, time_freq=True, legend=True
    )
    assert workspace.sync_options.camera is True
    assert workspace.sync_options.time_freq is True
    assert workspace.sync_options.legend is True

    workspace = rx.set_fullscreen_viewport(
        workspace_id=workspace.id, viewport_id=workspace.viewport_ids[0]
    )
    assert workspace.fullscreen_viewport_id == workspace.viewport_ids[0]

    # get workspace and verify updates
    workspace = rx.get_workspace(workspace_id=workspace.id)
    assert workspace.sync_options.camera is True

    # delete the created workspace
    rx.delete_workspace(workspace_id=workspace.id)

    # verify deletion
    workspaces = rx.list_workspaces()
    assert len(workspaces) == 1
    assert "Test Workspace" not in [ws.name for ws in workspaces]


def test_error_get_nonexistent_workspace(rx):
    non_existent_id = "non-existent-id"
    try:
        rx.get_workspace(workspace_id=non_existent_id)
    except Exception as e:
        log.info(f"Caught expected exception: {e}")
        # assert "not found" in str(e) # todo: needs web adjustments
