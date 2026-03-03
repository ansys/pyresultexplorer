import logging
import uuid

import pytest

from ansys.result_explorer.core import ResultExplorerError

log = logging.getLogger(__name__)


def test_workspace(rx):
    """CRUD operations for workspaces."""

    # list workspaces
    workspaces = rx.list_workspaces()
    for ws in workspaces:
        assert ws.id is not None
        assert ws.name is not None

    # create a new workspace
    name = f"Test Workspace {str(uuid.uuid4())}"
    workspace = rx.create_workspace(name=name)
    assert workspace.name == name
    assert workspace.fullscreen_viewport_id == ""
    assert workspace.sync_camera is False
    assert workspace.sync_time_freq is False
    assert workspace.sync_legend is False
    assert workspace.sync_probe_entity is False
    assert workspace.sync_probe_location is False
    assert len(workspace.viewport_ids) == 1

    # update workspace to turn on sync options and set fullscreen viewport
    workspace.set_sync(camera=True, time_freq=True, legend=True)
    workspace = rx.get_workspace(workspace.id)
    assert workspace.sync_camera is True
    assert workspace.sync_time_freq is True
    assert workspace.sync_legend is True
    assert workspace.sync_probe_entity is False
    assert workspace.sync_probe_location is False

    workspace.set_fullscreen_viewport(workspace.viewports[0])
    workspace = rx.get_workspace(workspace.id)
    assert workspace.fullscreen_viewport_id == workspace.viewport_ids[0]

    # get workspace and verify updates
    workspace = rx.get_workspace(workspace.id)
    assert workspace.sync_camera is True

    # delete the created workspace
    rx.delete_workspace(workspace)

    # verify deletion
    workspaces = rx.list_workspaces()
    assert all(ws.name != workspace.name for ws in workspaces)


def test_error_get_nonexistent_workspace(rx):
    non_existent_id = "non-existent-id"
    with pytest.raises(ResultExplorerError) as exc_info:
        rx.get_workspace(workspace_id=non_existent_id)

    log.info(f"Caught expected exception: {exc_info.value}")

    assert "not found" in str(exc_info.value)
    assert non_existent_id in str(exc_info.value)
