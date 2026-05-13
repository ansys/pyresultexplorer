import json
import logging
from pathlib import Path

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
        result_provider="Local",
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
