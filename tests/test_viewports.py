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

import logging

import pytest

from ansys.result_explorer.core import (
    CameraPosition,
    ChartViewportSettings,
    ContactTrackersViewportSettings,
    ConvergenceTrackersViewportSettings,
    LogsViewportSettings,
    MeshViewportSettings,
    PlotViewportMetadata,
    ThreeDViewportSettings,
    ViewportSettings,
    models,
)
from ansys.result_explorer.core.models import ViewportDirection, ViewType
from ansys.result_explorer.core.objects.viewport import (
    PlotViewportSettings,
    Viewport,
    _dict_to_settings,
    _settings_to_dict,
)

log = logging.getLogger(__name__)


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
    assert viewport.view_id == view.id
    assert viewport.solution_id == sol.id

    # list viewports
    viewports = workspace.viewports
    assert len(viewports) >= 1

    # modify settings
    opts = viewport.settings
    opts.show_mesh_edges = not opts.show_mesh_edges
    opts.show_min_max_labels = not opts.show_min_max_labels

    assert viewport.settings.show_mesh_edges == opts.show_mesh_edges
    assert _settings_to_dict(viewport._pb.settings)["showMesh"] == opts.show_mesh_edges

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


def test_viewport_settings_round_trip():
    settings = {
        "leftClickMode": "Probe Node",
        "timeFrequencySetId": 1,
        "showMesh": False,
        "shownBodies": ["1", "4"],
        "cameraPosition": {"matrix": [1.0] * 16},
        "transparentBodies": None,
    }

    round_tripped = _settings_to_dict(_dict_to_settings(settings))

    assert round_tripped == {**settings, "transparentBodies": []}


def test_viewport_setting_options():
    settings = ThreeDViewportSettings._from_pb(_dict_to_settings({}), client=None)
    settings._setting_options = _settings_to_dict(
        _dict_to_settings(
            {
                "leftClickMode": [
                    "Select Bodies",
                    "Probe Node",
                    "Probe Element",
                    "Toggle Transparent",
                ],
            }
        )
    )

    assert settings.left_click_modes == [
        "Select Bodies",
        "Probe Node",
        "Probe Element",
        "Toggle Transparent",
    ]


def test_plot_viewport_setting_options():
    settings = PlotViewportSettings._from_pb(
        _dict_to_settings({"componentName": "X", "timeFrequencySetId": 1}), client=None
    )
    settings._setting_options = _settings_to_dict(
        _dict_to_settings(
            {
                "componentName": ["Magnitude", "X", "Y", "Z"],
                "timeFrequencySetId": ["1", "2"],
                "legendColorMap": ["Rainbow", "Turbo"],
            }
        )
    )

    assert settings.component_name.options == ["Magnitude", "X", "Y", "Z"]
    assert settings.set_id.options == ["1", "2"]
    assert settings.color_maps == ["Rainbow", "Turbo"]


def test_viewport_settings_and_options_types():
    three_d_settings = ThreeDViewportSettings._from_pb(
        _dict_to_settings({"showMesh": True}), client=None
    )
    three_d_settings._setting_options = _settings_to_dict(
        _dict_to_settings({"leftClickMode": ["Select Bodies"]})
    )
    mesh_settings = MeshViewportSettings._from_pb(
        _dict_to_settings({"shownNamedSelectionId": "selection-1"}), client=None
    )
    chart_settings = ChartViewportSettings._from_pb(
        _dict_to_settings({"showChart": True, "showLegend": True, "xAxisSeries": "Time"}),
        client=None,
    )
    chart_settings._setting_options = _settings_to_dict(
        _dict_to_settings({"activeSeries": ["Time"]})
    )
    contact_settings = ContactTrackersViewportSettings._from_pb(
        _dict_to_settings({"chartSelectionMode": "chartBodies"}), client=None
    )
    contact_settings._setting_options = _settings_to_dict(
        _dict_to_settings({"chartSelectionMode": ["chartBodies"]})
    )
    convergence_settings = ConvergenceTrackersViewportSettings._from_pb(
        _dict_to_settings({"tracker": "Force Convergence"}), client=None
    )
    convergence_settings._setting_options = _settings_to_dict(
        _dict_to_settings({"tracker": ["Force"]})
    )
    logs_settings = LogsViewportSettings._from_pb(
        _dict_to_settings({"logFile": "solve.out"}), client=None
    )
    logs_settings._setting_options = _settings_to_dict(
        _dict_to_settings({"logFile": ["solve.out"]})
    )

    assert three_d_settings.show_mesh_edges.value is True
    assert three_d_settings.left_click_modes == ["Select Bodies"]
    assert mesh_settings.visible_named_selection == "selection-1"
    assert mesh_settings.visible_named_selection.options is None
    assert chart_settings.show_chart.value is True
    assert chart_settings.selected_x_axis == "Time"
    assert chart_settings.selected_x_axis.options == ["Time"]
    assert contact_settings.selection_mode == "chartBodies"
    assert contact_settings.selection_mode.options == ["chartBodies"]
    assert convergence_settings.selected_tracker_name == "Force Convergence"
    assert convergence_settings.selected_tracker_name.options == ["Force"]
    assert logs_settings.log_path == "solve.out"
    assert logs_settings.log_path.options == ["solve.out"]


def test_unassigned_viewport_uses_generic_settings():
    viewport = Viewport(models.Viewport(id="viewport-1"), client=None)

    assert isinstance(viewport.settings, ViewportSettings)
    assert isinstance(viewport.metadata, object)


def test_plot_viewport_settings_from_raw_settings_with_empty_values():
    settings = _dict_to_settings(
        {
            "shownBodies": [],
            "expandedGroups": [],
            "deformationScale": None,
            "timeFrequencySetId": 1,
            "componentName": "Magnitude",
            "legendMin": 0,
            "legendMax": 0.00011873363109771162,
            "legendUseGlobalMinMax": True,
            "result": "displacement",
        }
    )
    settings.append(
        models.SettingOption(key="transparencyLevel", value=models.SettingValue(string_value=""))
    )

    opts = PlotViewportSettings._from_pb(settings, client=None)

    assert opts.visible_bodies == []
    assert opts.expanded_groups == []
    assert opts.deformation_scale.value is None
    assert opts.set_id == 1
    assert opts.component_name == "Magnitude"
    assert opts.legend_range == (0.0, 0.00011873363109771162)


def test_plot_viewport_settings_from_raw_settings():
    settings = PlotViewportSettings._from_pb(
        _dict_to_settings(
            {
                "showMesh": True,
                "showMinMaxLabels": False,
                "result": "displacement",
                "componentName": "X",
            }
        ),
        client=None,
    )

    assert settings.show_mesh_edges.value is True
    assert settings.show_min_max_labels.value is False
    assert settings.result == "displacement"
    assert settings.component_name == "X"


def test_viewport_size(rx):
    """Test grid workspace creation and viewport size manipulation."""

    # Test grid workspace creation with different row/column counts
    workspace_2x2 = rx.create_workspace("Test 2x2 Grid", rows=2, cols=2)
    assert len(workspace_2x2.viewport_ids) == 4

    workspace_3x2 = rx.create_workspace("Test 3x2 Grid", rows=3, cols=2)
    assert len(workspace_3x2.viewport_ids) == 6

    workspace_1x3 = rx.create_workspace("Test 1x3 Grid", rows=1, cols=3)
    assert len(workspace_1x3.viewport_ids) == 3

    # Test viewport.size property
    viewports_2x2 = workspace_2x2.viewports
    sizes_2x2 = [vp.size for vp in viewports_2x2]

    # All viewports should have a size property that's a number
    assert all(isinstance(size, int | float) for size in sizes_2x2)

    # In a 2x2 grid, viewports should have non-zero sizes
    assert all(size > 0 for size in sizes_2x2)

    # Test updating viewport size using viewport.set_size
    first_viewport = viewports_2x2[0]

    new_size = 75.0
    first_viewport.set_size(new_size)
    assert first_viewport.size == new_size
    assert workspace_2x2.viewports[1].size == 100 - new_size

    # Refresh the viewport from the server
    updated_viewports = workspace_2x2.viewports
    first_vp_updated = next((vp for vp in updated_viewports if vp.id == first_viewport.id), None)

    assert first_vp_updated is not None
    assert first_vp_updated.size == new_size

    # Cleanup
    rx.delete_workspace(workspace_2x2)
    rx.delete_workspace(workspace_3x2)
    rx.delete_workspace(workspace_1x3)


def test_grid_layout(rx):
    """Test layout description of a regular grid of viewports."""
    workspace = rx.create_workspace("Test Grid Layout", rows=2, cols=3)

    layout = workspace.layout
    assert layout.grid_shape == (2, 3)
    assert layout.is_grid is True

    grid = workspace.viewport_grid()
    assert [len(row) for row in grid] == [3, 3]

    # every cell holds a different viewport
    grid_ids = [viewport.id for row in grid for viewport in row]
    assert sorted(grid_ids) == sorted(workspace.viewport_ids)

    assert workspace.viewport_at(row=1, column=2).id == grid[1][2].id

    # each viewport covers the fraction of the workspace matching its cell
    for row_index, row in enumerate(grid):
        for column_index, viewport in enumerate(row):
            placement = layout.placement_of(viewport)
            assert (placement.row, placement.column) == (row_index, column_index)
            assert (placement.row_span, placement.column_span) == (1, 1)
            assert placement.x == pytest.approx(column_index / 3)
            assert placement.width == pytest.approx(1 / 3)
            assert placement.y == pytest.approx(row_index / 2)
            assert placement.height == pytest.approx(1 / 2)

    with pytest.raises(IndexError, match="No viewport at row"):
        workspace.viewport_at(row=2, column=0)

    rx.delete_workspace(workspace)


def test_non_grid_layout(rx):
    """Test layout description of a viewport arrangement that is not a grid."""
    workspace = rx.create_workspace("Test Split Layout")
    left = workspace.viewports[0]
    right_top = workspace.create_viewport(left, ViewportDirection.VIEWPORT_DIRECTION_RIGHT)
    right_bottom = workspace.create_viewport(right_top, ViewportDirection.VIEWPORT_DIRECTION_BOTTOM)

    layout = workspace.layout
    assert layout.grid_shape == (2, 2)
    assert layout.is_grid is False

    # the left viewport spans both rows of the first column
    left_placement = layout.placement_of(left)
    assert (left_placement.row, left_placement.column) == (0, 0)
    assert (left_placement.row_span, left_placement.column_span) == (2, 1)

    assert layout.viewport_at(0, 0).id == left.id
    assert layout.viewport_at(1, 0).id == left.id
    assert layout.viewport_at(0, 1).id == right_top.id
    assert layout.viewport_at(1, 1).id == right_bottom.id

    assert left.id in layout.describe()

    rx.delete_workspace(workspace)


def test_viewport_hidden(rx):
    """Test viewport hidden, hide, and show."""
    workspace = rx.create_workspace("Test Viewport Hidden", rows=1, cols=2)
    viewports = workspace.viewports
    assert len(viewports) == 2

    vp = viewports[0]

    # newly created viewport should be visible
    assert vp.hidden is False

    # hide the viewport
    vp.hide()
    assert vp.hidden is True

    # verify server state
    refreshed = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == vp.id)
    assert refreshed.hidden is True

    # show the viewport again
    vp.show()
    assert vp.hidden is False

    # verify server state
    refreshed = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == vp.id)
    assert refreshed.hidden is False

    # Cleanup
    rx.delete_workspace(workspace)


def test_plot_viewport_metadata(rx, multiple_connections_solution):
    """Test PlotViewportMetadata properties."""
    sol = multiple_connections_solution

    # Find a displacement view (typically a plot view)
    views = sol.views
    view = next((v for v in views if "Displacement" in v.name), None)
    assert view is not None

    # Create workspace and assign view
    workspace = rx.create_workspace("Test Plot Metadata")
    viewport = workspace.assign_view(view=view, wait=True)

    meta = viewport.metadata
    log.info("plot metadata: %s", meta)

    # Test show_mesh via settings
    opts = viewport.settings
    original_show_mesh = opts.show_mesh_edges
    opts.show_mesh_edges = not original_show_mesh
    assert viewport.settings.show_mesh_edges == (not original_show_mesh)

    # Test show_min_max_labels via settings
    opts = viewport.settings
    original_min_max = opts.show_min_max_labels
    opts.show_min_max_labels = not original_min_max
    assert viewport.settings.show_min_max_labels == (not original_min_max)

    # Test deformation_scale via result_settings
    assert viewport.settings.deformation_scale == 1.0
    opts = viewport.settings
    opts.deformation_scale = 2.5
    assert viewport.settings.deformation_scale == 2.5

    # Cleanup
    rx.delete_workspace(workspace)


def test_logs_viewport_settings(rx, cp_transient_solution):
    """Test LogsViewportSettings."""

    # Create workspace
    workspace = rx.create_workspace("Test Logs Metadata")

    # find a logs view from the solution
    views = cp_transient_solution.views
    logs_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_LOGS), None)
    assert logs_view is not None

    viewport = workspace.assign_view(view=logs_view, wait=True)
    settings = viewport.settings
    log.info("logs settings: %s", settings)

    assert settings is not None
    assert isinstance(settings, LogsViewportSettings)

    assert "cp_trans" in viewport.settings.log_path
    assert viewport.settings.log_path.endswith("solve.out")

    opts = viewport.settings
    opts.log_path = opts.log_path.replace("solve.out", "file.err")
    assert viewport.settings.log_path.endswith("file.err")


def test_mesh_viewport_settings(rx, multiple_connections_solution):
    """Test MeshViewportSettings properties."""
    sol = multiple_connections_solution

    # Find a mesh view from the solution
    views = sol.views
    mesh_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_MESH), None)
    assert mesh_view is not None

    # Create workspace and assign mesh view
    workspace = rx.create_workspace("Test Mesh Metadata")
    viewport = workspace.assign_view(view=mesh_view, wait=True)

    log.info("mesh settings: %s", viewport.settings)

    # Test explode property
    opts = viewport.settings
    original_explode = opts.explode
    opts.explode = not original_explode
    assert viewport.settings.explode == (not original_explode)

    # Test explode_scale_factor property
    with viewport.update_settings() as opts:
        opts.explode_scale_factor = 1.5
    assert viewport.settings.explode_scale_factor == 1.5

    # Test explode_direction property
    opts = viewport.settings
    opts.explode_direction = "Radial"
    assert viewport.settings.explode_direction == "Radial"

    with viewport.update_settings() as opts:
        opts.explode_direction = "X"
    assert viewport.settings.explode_direction == "X"

    # Test expanded_groups property
    opts = viewport.settings
    opts.expanded_groups = ["group1", "group2"]
    assert viewport.settings.expanded_groups == ["group1", "group2"]

    # Cleanup
    rx.delete_workspace(workspace)


@pytest.mark.flaky(reruns=1, reruns_delay=1)
def test_mesh_viewport_named_selection_visibility(
    rx, cp_transient_solution, snapshot, snapshot_settings
):
    """Test named selection visibility in MeshViewportMetadata."""
    sol = cp_transient_solution

    # Find a mesh view from the solution
    views = sol.views
    mesh_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_MESH), None)
    assert mesh_view is not None

    # Create workspace and assign mesh view
    workspace = rx.create_workspace("Test Mesh Metadata Visibility")
    viewport = workspace.assign_view(view=mesh_view, wait=True)

    assert isinstance(viewport.settings, MeshViewportSettings)
    log.info("mesh settings: %s", viewport.settings)

    # Test named selection visibility by id
    ns_contact = next((ns for ns in sol.named_selections if "CONTACT" in ns.name), None)
    with viewport.update_settings() as opts:
        opts.visible_named_selection = ns_contact.id
        opts.show_mesh_edges = True
    assert viewport.settings.visible_named_selection == ns_contact.id

    _ = viewport.take_snapshot(settings=snapshot_settings)
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="CONTACT")

    # Test named selection visibility by object
    ns_eppl = next((ns for ns in sol.named_selections if "ND001_EPPL_ELEMENTS" in ns.name), None)
    opts = viewport.settings
    opts.visible_named_selection = ns_eppl
    assert viewport.settings.visible_named_selection == ns_eppl.id

    assert viewport.ready is True
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="ND001_EPPL_ELEMENTS")

    # Test named selection visibility by name
    with viewport.update_settings() as opts:
        opts.visible_named_selection = "LEFT1"
    ns_left = next((ns for ns in sol.named_selections if "LEFT1" in ns.name), None)
    assert viewport.settings.visible_named_selection == ns_left.id

    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="LEFT1")

    opts = viewport.settings
    # test exception for invalid named selection
    with pytest.raises(ValueError, match="INVALID_NS"):
        opts.visible_named_selection = "INVALID_NS"

    # Cleanup
    rx.delete_workspace(workspace)


def test_chart_viewport_settings(rx, cp_transient_solution):
    """Test ChartViewportSettings."""
    # Create workspace
    workspace = rx.create_workspace("Test Chart Settings")

    # Get any viewport for chart metadata testing
    viewports = workspace.viewports
    assert len(viewports) > 0

    # find a chart view from the solution
    views = cp_transient_solution.views
    chart_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CHART), None)
    assert chart_view is not None

    viewport = workspace.assign_view(view=chart_view, wait=True)

    settings = viewport.settings

    assert settings is not None
    assert isinstance(settings, ChartViewportSettings)

    log.info("Viewport settings: %s", viewport._pb.settings)
    log.info("Viewport setting options: %s", viewport._pb.setting_options)

    # Test settings doesn't have an active_charts property
    assert not hasattr(settings, "active_charts")

    # Test series_names property (read-only, from metadata)
    series_names = settings.active_series.options
    assert isinstance(series_names, list)
    assert len(series_names) >= 4
    expected_series = [
        "Time/Frequency",
        "Displacement: Min Total Displacement",
        "Displacement: Max Total Displacement",
        "Displacement: Avg Total Displacement",
    ]
    for expected in expected_series:
        assert expected in series_names, f"Expected series '{expected}' not found"
    log.info("Available series: %s", series_names)

    # Test active_series property (from display options)
    active_series = settings.active_series
    assert isinstance(active_series, list)
    assert len(active_series) == 3  # Should have 3 active series
    expected_active = [
        "Displacement: Min Total Displacement",
        "Displacement: Max Total Displacement",
        "Displacement: Avg Total Displacement",
    ]
    assert active_series == expected_active
    log.info("Active series: %s", active_series)

    # Test selected_x_axis property (from display options)
    assert isinstance(settings.selected_x_axis, str)
    assert settings.selected_x_axis == "Time/Frequency"
    log.info("Selected X-axis: %s", settings.selected_x_axis)

    # Test show_legend property (from display options)
    assert isinstance(settings.show_legend.value, bool)
    assert settings.show_legend.value is True
    log.info("Show legend: %s", settings.show_legend)

    # Test show_table property (from display options)
    assert isinstance(settings.show_table.value, bool)
    assert settings.show_table.value is False
    log.info("Show table: %s", settings.show_table)

    # Test split_direction property (from display options)
    assert settings.split_direction == "vertical"
    log.info("Split direction: %s", settings.split_direction)

    # Test modifying active_series
    if len(series_names) >= 2:
        new_series = [series_names[0], series_names[1]]
        with viewport.update_settings() as opts:
            opts.active_series = new_series
        assert viewport.settings.active_series == new_series

    # Test toggling legend visibility
    opts = viewport.settings
    opts.show_legend = False
    assert viewport.settings.show_legend.value is False

    opts = viewport.settings
    opts.show_legend = True
    assert viewport.settings.show_legend.value is True

    # Test toggling table visibility
    opts = viewport.settings
    opts.show_table = True
    assert viewport.settings.show_table.value is True

    opts = viewport.settings
    opts.show_table = False
    assert viewport.settings.show_table.value is False

    # Test split_direction
    opts = viewport.settings
    opts.split_direction = "horizontal"
    assert viewport.settings.split_direction == "horizontal"

    opts = viewport.settings
    opts.split_direction = "vertical"
    assert viewport.settings.split_direction == "vertical"

    # Cleanup
    rx.delete_workspace(workspace)


def test_convergence_trackers_viewport_settings(rx, cp_transient_solution):
    """Test ConvergenceTrackersViewportSettings."""

    # Create workspace
    workspace = rx.create_workspace("Test Convergence Trackers Settings")

    # find a convergence trackers view from the solution
    views = cp_transient_solution.views
    conv_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS), None)
    assert conv_view is not None

    viewport = workspace.assign_view(view=conv_view, wait=True)
    settings = viewport.settings
    log.info("convergence trackers settings: %s", settings)

    assert settings is not None
    assert isinstance(settings, ConvergenceTrackersViewportSettings)

    assert settings.selected_tracker_name == "Force Convergence"

    with viewport.update_settings() as opts:
        opts.selected_tracker_name = "Displacement Convergence"
    assert viewport.settings.selected_tracker_name == "Displacement Convergence"


def test_contact_trackers_viewport_settings(rx, cp_transient_solution):
    """Test ContactTrackersViewportSettings."""

    # Create workspace
    workspace = rx.create_workspace("Test Contact Trackers Settings")

    # find a contact trackers view from the solution
    views = cp_transient_solution.views
    contact_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CONTACT_TRACKERS), None)
    assert contact_view is not None

    viewport = workspace.assign_view(view=contact_view, wait=True)

    settings = viewport.settings
    log.info("contact trackers settings: %s", settings)

    assert settings is not None
    assert isinstance(settings, ContactTrackersViewportSettings)

    # Test inherited chart settings
    assert isinstance(settings.show_legend.value, bool)
    assert isinstance(settings.show_table.value, bool)
    assert settings.split_direction in ["horizontal", "vertical"]

    # Test series_names property (read-only, from metadata)
    assert isinstance(settings.active_series.options, list)
    assert len(settings.active_series.options) > 0

    # Check specific expected series names from contact tracking
    expected_series = [
        "Number of Contact Elements in Contact",
        "Max. Contact Pressure",
        "Max. Friction Stress",
    ]
    for expected in expected_series:
        assert expected in settings.active_series.options, f"Expected series '{expected}' not found"

    log.info("Available series: %s", settings.active_series.options[:5])  # Log first 5

    # Test active_series property (from display options)
    active_series = settings.active_series
    assert isinstance(active_series, list)
    assert len(active_series) > 0
    assert all(s in settings.active_series.options for s in active_series)
    log.info("Active series: %s", active_series)

    # Test toggling active series
    if len(settings.active_series.options) >= 2:
        new_series = [settings.active_series.options[0], settings.active_series.options[1]]
        settings = viewport.settings
        settings.active_series = new_series
        assert viewport.settings.active_series == new_series

    # Test contact tracker names (read-only, from metadata)
    contact_trackers = settings.active_contact_trackers.options
    assert isinstance(contact_trackers, list)
    assert len(contact_trackers) >= 2, "Expected at least 2 contact tracker pairs"

    # Verify expected contact tracker pattern
    for tracker in contact_trackers:
        assert "Solid" in tracker
        assert "ID:" in tracker

    log.info("Contact trackers: %s", contact_trackers)

    # Test toggling legend visibility
    original_legend = settings.show_legend
    settings = viewport.settings
    settings.show_legend = not original_legend
    assert viewport.settings.show_legend == (not original_legend)

    # Test toggling table visibility
    original_table = viewport.settings.show_table
    opts = viewport.settings
    opts.show_table = not original_table
    assert viewport.settings.show_table == (not original_table)

    # Test split direction
    opts = viewport.settings
    opts.split_direction = "horizontal"
    assert viewport.settings.split_direction == "horizontal"

    # Cleanup
    rx.delete_workspace(workspace)


@pytest.mark.images
@pytest.mark.flaky(reruns=1, reruns_delay=1)
def test_camera_position_snapshots(rx, multiple_connections_solution, snapshot, snapshot_settings):
    sol = multiple_connections_solution

    # Find a displacement view
    views = sol.views
    view = next((v for v in views if "Displacement" in v.name), None)
    assert view is not None

    # Create workspace and assign view
    workspace = rx.create_workspace("Test Camera Snapshot")
    viewport = workspace.assign_view(view=view, wait=True)

    # Get initial camera zoom/translation to preserve them
    initial_cam = viewport.settings.camera_position
    initial_zoom = initial_cam.zoom if initial_cam is not None else 1.0
    initial_translation = initial_cam.translation if initial_cam is not None else (0.0, 0.0, 0.0)

    # Test a few camera presets
    camera_tests = {
        "top": CameraPosition.top(),
        "bottom": CameraPosition.bottom(),
        "front": CameraPosition.front(),
        "isometric": CameraPosition.isometric(),
        "isometric+30x-10z": CameraPosition.isometric().rotate_x(30).rotate_z(-10),
    }

    _ = viewport.take_snapshot(settings=snapshot_settings)
    for name, cam in camera_tests.items():
        # Apply camera with preserved zoom/translation
        opts = viewport.settings
        opts.camera_position = cam.with_zoom(initial_zoom).with_translation(*initial_translation)

        # Take snapshot with clean settings
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
        assert len(snapshot_data) > 0

        # image comparison
        assert snapshot_data == snapshot(name=name)

    # Cleanup
    rx.delete_workspace(workspace)


# @pytest.mark.images
# @pytest.mark.flaky(reruns=1, reruns_delay=1)
def test_result_display_options_snapshots(
    rx, cp_transient_solution, snapshot, snapshot_settings_with_legend
):
    """Test snapshot comparisons for result display option changes."""
    sol = cp_transient_solution

    view = next((v for v in sol.plot_views if "Displacement" in v.name), None)
    assert view is not None

    # Enable all time steps so set_id can be changed freely
    time_frequencies = sol.time_frequencies
    assert len(time_frequencies) >= 2
    first_tf = time_frequencies[0]
    last_tf = time_frequencies[-1]

    plot_def = view.definition
    plot_def.all_sets = True
    plot_def.last_set = False
    view = sol.update_plot(plot_def)
    assert view.definition.all_sets is True
    assert view.definition.last_set is False

    workspace = rx.create_workspace("Test Result Display Options")
    viewport = workspace.assign_view(view=view, wait=True)

    opts = viewport.settings
    assert isinstance(opts, PlotViewportSettings)

    opts.set_id = last_tf.set_id

    _ = viewport.take_snapshot(settings=snapshot_settings_with_legend)

    # Different component indices produce visually distinct color distributions
    for name, component_name in [("component_x", "X"), ("component_y", "Y"), ("component_z", "Z")]:
        with viewport.update_settings() as opts:
            opts.component_name = component_name
            opts.legend_range = None  # reset legend range to auto for new component
        assert opts.component_name == component_name
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings_with_legend)
        assert snapshot_data == snapshot(name=name)

    # reset some options for further tests

    opts = viewport.settings
    assert isinstance(opts, PlotViewportSettings)
    opts.component_name = "Magnitude"
    assert viewport.settings.component_name == "Magnitude"

    # Deformation scale changes the shape of the deformed mesh
    for name, scale in [("deformation_1x", 1.0), ("deformation_5x", 5.0)]:
        with viewport.update_settings() as opts:
            opts.deformation_scale = scale
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings_with_legend)
        assert snapshot_data == snapshot(name=name)

    # reset some options for further tests
    opts = viewport.settings
    opts.deformation_scale = 1

    # use_global_min_max affects how the legend range is computed
    with viewport.update_settings() as opts:
        opts.set_id = first_tf.set_id
        opts.deformation_scale = 1.0
        opts.use_global_min_max = False

    assert snapshot(name="use_local_min_max") == viewport.take_snapshot(
        settings=snapshot_settings_with_legend
    )

    # legend_range pins the color scale to a fixed interval
    opts = viewport.settings
    with viewport.update_settings() as opts:
        opts.set_id = last_tf.set_id
        opts.deformation_scale = 1.0
        opts.use_global_min_max = False
        opts.legend_range = (0.0, 5e-5)

    assert viewport.settings.legend_range[0] == 0.0
    assert viewport.settings.legend_range[1] == 5e-5

    assert snapshot(name="legend_range_fixed") == viewport.take_snapshot(
        settings=snapshot_settings_with_legend
    )

    # verify extremes
    meta: PlotViewportMetadata = viewport.metadata
    assert meta.active_result.min.value == 0.0
    assert meta.active_result.min.entity_id == 150
    assert meta.active_result.max.value == pytest.approx(1.187e-4, rel=1e-3)
    assert meta.active_result.max.entity_id == 7

    rx.delete_workspace(workspace)


def test_camera_position_invalid_matrix_length():
    """Test CameraPosition rejects invalid matrix length."""
    with pytest.raises(ValueError, match="Expected 16 matrix values"):
        CameraPosition([1, 2, 3])  # Too few


def test_camera_position_rotations():
    """Test all rotation methods."""
    cam = CameraPosition.top()
    rotated_x = cam.rotate_x(90)
    rotated_y = cam.rotate_y(45)
    rotated_z = cam.rotate_z(180)
    assert len(rotated_x.matrix) == 16
    assert len(rotated_y.matrix) == 16
    assert len(rotated_z.matrix) == 16


def test_camera_position_with_zoom():
    """Test CameraPosition with non-unit zoom."""
    m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2.5]
    cam = CameraPosition(m)
    assert cam.zoom == 2.5
    assert cam.with_translation(10, 20, 30).translation == (10, 20, 30)


def test_visible_bodies_option(rx, multiple_connections_solution, snapshot, snapshot_settings):
    """Test visible bodies display option."""

    if rx.app_info.version == "2026.7.0":
        pytest.skip("Skipping test due to known issue in version 2026.7.0")

    sol = multiple_connections_solution

    # Find a mesh view from the solution
    views = sol.views
    mesh_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_MESH), None)
    assert mesh_view is not None

    # Create workspace and assign mesh view
    workspace = rx.create_workspace("Test Body Visibility")
    viewport = workspace.assign_view(view=mesh_view, wait=True)

    _ = viewport.take_snapshot(settings=snapshot_settings)

    # image comparison
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="initial")

    bodies = sol.bodies
    solid186_body_ids = []
    for body in bodies:
        if "SOLID186" in body.element_types:
            solid186_body_ids.append(body.id)

    # Test visible_bodies property
    opts = viewport.settings
    opts.visible_bodies = solid186_body_ids
    assert viewport.settings.visible_bodies == solid186_body_ids

    # image comparison
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="SOLID186_bodies")

    # Cleanup
    rx.delete_workspace(workspace)
