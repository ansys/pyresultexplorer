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

import json
import logging
import time
from pathlib import Path

import pytest

from ansys.result_explorer.core import models

log = logging.getLogger(__name__)


def test_app(rx):
    # build info
    app_info = rx.app_info()
    assert app_info.version != ""
    assert app_info.commit_hash != ""

    # get settings
    app_settings = rx.app_settings()
    log.info(f"App settings: {app_settings}")

    # update settings
    app_settings.appearance.theme = models.AppTheme.APP_THEME_DARK
    app_settings.three_d.interaction_mode = (
        models.ThreeDInteractionMode.THREE_DINTERACTION_MODE_PRESET_3
    )
    app_settings.data_processing.chunking_strategy = models.ChunkingStrategy.CHUNKING_STRATEGY_SMALL
    app_settings.three_d.color_map = models.ThreeDColorMap.THREE_DCOLOR_MAP_VIRIDIS

    original_show_mesh_edges = app_settings.three_d.show_mesh_edges_by_default
    app_settings.three_d.show_mesh_edges_by_default = not original_show_mesh_edges
    new_settings = rx.update_app_settings(app_settings)

    assert new_settings.appearance.theme == models.AppTheme.APP_THEME_DARK
    assert (
        new_settings.three_d.interaction_mode
        == models.ThreeDInteractionMode.THREE_DINTERACTION_MODE_PRESET_3
    )
    assert (
        new_settings.data_processing.chunking_strategy
        == models.ChunkingStrategy.CHUNKING_STRATEGY_SMALL
    )
    assert new_settings.three_d.color_map == models.ThreeDColorMap.THREE_DCOLOR_MAP_VIRIDIS
    assert new_settings.three_d.show_mesh_edges_by_default == (not original_show_mesh_edges)


def test_save_session(rx, tmp_path):
    """Test save_session path handling: makedirs, extension appending, valid JSON output."""

    # Save session to a nested path to verify makedirs
    session_path = tmp_path / "nested" / "dir" / "session.rxs"
    rx.save_session(session_path)

    assert session_path.exists()

    # Verify the file contains valid JSON
    content = session_path.read_text()
    data = json.loads(content)
    assert isinstance(data, dict)

    # Test with a Path without extension - should auto-append .rxs
    session_path_no_ext = tmp_path / "session_no_ext"
    rx.save_session(session_path_no_ext)
    expected_path = Path(str(session_path_no_ext) + ".rxs")
    assert expected_path.exists()

    content2 = expected_path.read_text()
    data2 = json.loads(content2)
    assert isinstance(data2, dict)

    # Test with a string path
    session_path_str = str(tmp_path / "from_string.rxs")
    rx.save_session(session_path_str)
    assert Path(session_path_str).exists()


def test_save_session_with_views(rx, rst_multiple_connections, tmp_path):
    """Test that a session with solutions, workspaces, and views is saved correctly."""

    # Create a solution
    sol = rx.create_solution(
        name="Session Test Solution",
        file_path=rst_multiple_connections,
    )

    # Create workspaces with different layouts
    ws1 = rx.create_workspace("Session WS 1", rows=2, cols=1)
    ws2 = rx.create_workspace("Session WS 2", rows=1, cols=2)

    # Assign views to viewports
    views = sol.views
    displacement_view = next((v for v in views if "Displacement" in v.name), None)
    assert displacement_view is not None

    ws1.assign_view(view=displacement_view, wait=True)

    stress_view = next((v for v in views if "Stress" in v.name), None)
    if stress_view is not None:
        ws2.assign_view(view=stress_view, wait=True)

    # Save session
    session_path = tmp_path / "full_session.rxs"
    rx.save_session(session_path)

    assert session_path.exists()

    content = session_path.read_text()
    data = json.loads(content)
    assert isinstance(data, dict)

    # Verify session structure
    assert "app_state" in data
    assert "result_providers" in data
    app_state = data["app_state"]
    assert "solutions" in app_state
    assert "workspaces" in app_state
    assert len(app_state["solutions"]) >= 1
    assert len(app_state["workspaces"]) >= 2

    rx.delete_workspace(ws1)
    rx.delete_workspace(ws2)
    rx.delete_solution(sol)


def test_open_session_round_trip(rx, rst_multiple_connections, tmp_path):
    """Save a session with a workspace and solution, then restore it and verify the state."""

    # --- build initial state ---
    sol = rx.create_solution(
        name="Round Trip Solution",
        file_path=rst_multiple_connections,
    )
    workspace = rx.create_workspace("Round Trip WS", rows=1, cols=2)
    views = sol.views
    displacement_view = next((v for v in views if "Displacement" in v.name), None)
    assert displacement_view is not None
    _ = workspace.assign_view(view=displacement_view, wait=True)

    # record what we expect to find after the round trip (IDs change on open_session)
    saved_ws_id = workspace.id
    saved_sol_name = sol.name
    saved_ws_name = workspace.name
    saved_view_name = displacement_view.name

    # --- save session ---
    session_path = tmp_path / "round_trip.rxs"
    rx.save_session(session_path)
    assert session_path.exists()

    # --- clear state ---
    rx.delete_workspace(workspace)
    rx.delete_solution(sol)
    assert all(w.id != saved_ws_id for w in rx.list_workspaces())

    # --- restore session ---
    with pytest.raises(ValueError, match="extension"):
        rx.open_session(str(session_path).replace(".rxs", ".txt"))

    # --- restore session ---
    rx.open_session(session_path)
    time.sleep(1)  # wait for session to load

    # --- verify workspaces ---
    workspaces = rx.list_workspaces()
    restored_ws = next((w for w in workspaces if w.name == saved_ws_name), None)
    assert restored_ws is not None, f"Workspace '{saved_ws_name}' not found after open_session"
    assert len(restored_ws.viewport_ids) == 2

    # --- verify solution ---
    solutions = rx.list_solutions()
    restored_sol = next((s for s in solutions if s.name == saved_sol_name), None)
    assert restored_sol is not None, f"Solution '{saved_sol_name}' not found after open_session"

    # --- verify the viewport has the view assigned ---
    # IDs are re-generated on open_session, so match by view name instead
    restored_vps = restored_ws.viewports
    assigned_vp = next((v for v in restored_vps if v.view_id), None)
    assert assigned_vp is not None, "No viewport with an assigned view found after open_session"
    restored_view = next(
        (v for v in rx.get_solution(restored_sol.id).views if v.id == assigned_vp.view_id), None
    )
    assert restored_view is not None, "Could not resolve the assigned view"
    assert restored_view.name == saved_view_name
    assert assigned_vp.solution_id == restored_sol.id

    # --- cleanup ---
    rx.delete_workspace(restored_ws)
    rx.delete_solution(restored_sol)
