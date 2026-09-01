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

import json
import logging
import uuid
from pathlib import Path

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

    # do the same with more granular APIs
    workspace.sync_camera = True
    workspace.sync_time_freq = True
    workspace.sync_legend = True
    workspace.sync_probe_entity = False
    workspace.sync_probe_location = False
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


def test_export_workspace_template(rx, tmp_path):
    """Test export_as_template path handling: makedirs, extension appending, valid JSON output."""

    workspace = rx.create_workspace("Template Export Test")

    # Export to a nested path to verify makedirs
    template_path = tmp_path / "nested" / "dir" / "ws.rxwt"
    workspace.export_as_template(template_path)

    assert template_path.exists()

    content = template_path.read_text()
    data = json.loads(content)
    assert isinstance(data, dict)

    # Verify top-level structure
    assert "version" in data
    assert "app_state" in data
    app_state = data["app_state"]
    assert "workspaces" in app_state
    assert "viewportLayoutNodes" in app_state
    assert "viewportPortals" in app_state
    assert len(app_state["workspaces"]) == 1
    ws_state = next(iter(app_state["workspaces"].values()))
    assert ws_state["name"] == workspace.name

    # Test with a Path without extension - should auto-append .rxwt
    template_path_no_ext = tmp_path / "ws_no_ext"
    workspace.export_as_template(template_path_no_ext)
    expected_path = Path(str(template_path_no_ext) + ".rxwt")
    assert expected_path.exists()

    data2 = json.loads(expected_path.read_text())
    assert isinstance(data2, dict)

    # Test with a string path
    template_path_str = str(tmp_path / "from_string.rxwt")
    workspace.export_as_template(template_path_str)
    assert Path(template_path_str).exists()

    rx.delete_workspace(workspace)


def test_export_workspace_template_with_views(rx, multiple_connections_solution, tmp_path):
    """Test that a workspace template with assigned views is exported correctly."""

    sol = multiple_connections_solution

    # Create a 2x1 workspace and assign views to both viewports
    workspace = rx.create_workspace("Template With Views", rows=2, cols=1)

    views = sol.views
    displacement_view = next((v for v in views if "Displacement" in v.name), None)
    stress_view = next((v for v in views if "Stress" in v.name), None)
    assert displacement_view is not None

    workspace.assign_view(view=displacement_view, wait=True)
    if stress_view is not None:
        workspace.assign_view(view=stress_view, wait=True)

    template_path = tmp_path / "ws_with_views.rxwt"
    workspace.export_as_template(template_path)

    assert template_path.exists()

    data = json.loads(template_path.read_text())
    assert isinstance(data, dict)

    # Verify top-level structure
    assert "version" in data
    assert "app_state" in data
    app_state = data["app_state"]
    assert len(app_state["workspaces"]) == 1
    ws_state = next(iter(app_state["workspaces"].values()))
    assert ws_state["name"] == workspace.name
    assert len(ws_state["viewportLayoutNodeIds"]) == 3  # 2x1 = 3 nodes (root + 2 leaves)

    # Verify at least one portal has a view assigned
    portals = app_state["viewportPortals"]
    assigned_portals = [p for p in portals.values() if p.get("viewId")]
    assert len(assigned_portals) >= 1
    assigned = assigned_portals[0]
    assert assigned["solutionId"] == sol.id

    # Verify the assigned view is recorded in the views dict with the right name
    views_state = app_state["views"]
    assert assigned["viewId"] in views_state
    expected_view_names = {v.name for v in views}
    assert views_state[assigned["viewId"]]["name"] in expected_view_names

    rx.delete_workspace(workspace)


@pytest.mark.parametrize("with_options", [False, True])
def test_import_workspace_from_template_round_trip(
    rx, multiple_connections_solution, tmp_path, with_options
):
    """Export a workspace template then import it and verify the result."""

    from ansys.result_explorer.core import models

    sol = multiple_connections_solution

    # Build a 1x2 workspace with one view assigned
    original_ws = rx.create_workspace("Template Round Trip", rows=1, cols=2)
    views = sol.views
    displacement_view = next((v for v in views if "Displacement" in v.name), None)
    assert displacement_view is not None
    original_ws.assign_view(view=displacement_view, wait=True)

    saved_view_name = displacement_view.name

    # Export template
    template_path = tmp_path / "round_trip.rxwt"
    original_ws.export_as_template(template_path)
    assert template_path.exists()

    # Import template — rebind the same solution slot the template references
    use_camera_position = None if not with_options else True
    use_time_freq = None if not with_options else True
    use_body_visibility = None if not with_options else True
    imported_ws = rx.import_workspace_from_template(
        template_path,
        workspace_name="Imported Round Trip",
        solutions=[
            models.WorkspaceImportRequest.SolutionInfo(
                name=sol.name + " (imported)",
                result_provider_name="Local",
                file_path=multiple_connections_solution.files[0].path,
            )
        ],
        use_camera_position=use_camera_position,
        use_time_freq=use_time_freq,
        use_body_visibility=use_body_visibility,
    )

    assert imported_ws.id != original_ws.id
    assert imported_ws.name == "Imported Round Trip"
    assert len(imported_ws.viewport_ids) == 2  # 1x2 layout preserved

    # Verify the assigned view name is preserved
    assigned_vp = next((v for v in imported_ws.viewports if v.view_id), None)
    assert assigned_vp is not None
    imported_sol = rx.get_solution(assigned_vp.solution_id)
    assert imported_sol.name == sol.name + " (imported)"
    restored_view = next((v for v in imported_sol.views if v.id == assigned_vp.view_id), None)
    assert restored_view is not None
    assert restored_view.name == saved_view_name

    # Cleanup
    rx.delete_workspace(original_ws)
    rx.delete_workspace(imported_ws)
