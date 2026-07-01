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

import logging

import pytest

from ansys.result_explorer.core import (
    CameraPosition,
    ChartViewportMetadata,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersViewportMetadata,
    LogsViewportMetadata,
    MeshViewportMetadata,
    PlotViewportMetadata,
)
from ansys.result_explorer.core.models import ViewportDirection, ViewType
from ansys.result_explorer.core.objects.viewport import PlotDisplayOptions, ResultDisplayOptions

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

    # modify display options
    opts = viewport.display_options
    opts.show_mesh_edges = not opts.show_mesh_edges
    opts.show_min_max_labels = not opts.show_min_max_labels

    assert viewport.display_options.show_mesh_edges == opts.show_mesh_edges
    assert viewport._pb.metadata["showMeshEdges"] == opts.show_mesh_edges

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

    # Test show_mesh_edges via display options
    opts = viewport.display_options
    original_mesh_edges = opts.show_mesh_edges
    opts.show_mesh_edges = not original_mesh_edges
    assert viewport.display_options.show_mesh_edges == (not original_mesh_edges)

    # Test show_min_max_labels via display options
    opts = viewport.display_options
    original_min_max = opts.show_min_max_labels
    opts.show_min_max_labels = not original_min_max
    assert viewport.display_options.show_min_max_labels == (not original_min_max)

    # Test deformation_scale via result_options
    assert viewport.display_options.result_options.deformation_scale == 1.0
    opts = viewport.display_options
    opts.result_options.deformation_scale = 2.5
    assert viewport.display_options.result_options.deformation_scale == 2.5

    # Cleanup
    rx.delete_workspace(workspace)


def test_logs_viewport_metadata(rx, cp_transient_solution):
    """Test LogsViewportMetadata."""

    # Create workspace
    workspace = rx.create_workspace("Test Logs Metadata")

    # find a logs view from the solution
    views = cp_transient_solution.views
    logs_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_LOGS), None)
    assert logs_view is not None

    viewport = workspace.assign_view(view=logs_view, wait=True)
    meta = viewport.metadata
    log.info("logs metadata: %s", meta)

    assert meta is not None
    assert isinstance(meta, LogsViewportMetadata)

    assert "cp_trans" in viewport.display_options.log_path
    assert viewport.display_options.log_path.endswith("solve.out")

    opts = viewport.display_options
    opts.log_path = opts.log_path.replace("solve.out", "file.err")
    assert viewport.display_options.log_path.endswith("file.err")


def test_mesh_viewport_metadata(rx, multiple_connections_solution):
    """Test MeshViewportMetadata properties."""
    sol = multiple_connections_solution

    # Find a mesh view from the solution
    views = sol.views
    mesh_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_MESH), None)
    assert mesh_view is not None

    # Create workspace and assign mesh view
    workspace = rx.create_workspace("Test Mesh Metadata")
    viewport = workspace.assign_view(view=mesh_view, wait=True)

    log.info("mesh metadata: %s", viewport.metadata)

    # Test explode property
    opts = viewport.display_options
    original_explode = opts.explode
    opts.explode = not original_explode
    assert viewport.display_options.explode == (not original_explode)

    # Test explode_scale_factor property
    with viewport.update_display_options() as opts:
        opts.explode_scale_factor = 1.5
    assert viewport.display_options.explode_scale_factor == 1.5

    # Test explode_direction property
    opts = viewport.display_options
    opts.explode_direction = "Radial"
    assert viewport.display_options.explode_direction == "Radial"

    with viewport.update_display_options() as opts:
        opts.explode_direction = "X"
    assert viewport.display_options.explode_direction == "X"

    # Test expanded_groups property
    opts = viewport.display_options
    opts.expanded_groups = ["group1", "group2"]
    assert viewport.display_options.expanded_groups == ["group1", "group2"]

    # Cleanup
    rx.delete_workspace(workspace)


@pytest.mark.flaky(reruns=3, reruns_delay=1)
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

    assert isinstance(viewport.metadata, MeshViewportMetadata)
    log.info("mesh metadata: %s", viewport.metadata)

    # Test named selection visibility by id
    ns_contact = next((ns for ns in sol.named_selections if "CONTACT" in ns.name), None)
    with viewport.update_display_options() as opts:
        opts.visible_named_selection = ns_contact.id
        opts.show_mesh_edges = True
    assert viewport.display_options.visible_named_selection == ns_contact.id

    _ = viewport.take_snapshot(settings=snapshot_settings)
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="CONTACT")

    # Test named selection visibility by object
    ns_eppl = next((ns for ns in sol.named_selections if "ND001_EPPL_ELEMENTS" in ns.name), None)
    opts = viewport.display_options
    opts.visible_named_selection = ns_eppl
    assert viewport.display_options.visible_named_selection == ns_eppl.id

    assert viewport.ready is True
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="ND001_EPPL_ELEMENTS")

    # Test named selection visibility by name
    with viewport.update_display_options() as opts:
        opts.visible_named_selection = "LEFT1"
    ns_left = next((ns for ns in sol.named_selections if "LEFT1" in ns.name), None)
    assert viewport.display_options.visible_named_selection == ns_left.id

    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="LEFT1")

    opts = viewport.display_options
    # test exception for invalid named selection
    with pytest.raises(ValueError, match="INVALID_NS"):
        opts.visible_named_selection = "INVALID_NS"

    # Cleanup
    rx.delete_workspace(workspace)


def test_chart_viewport_metadata(rx, cp_transient_solution):
    """Test ChartViewportMetadata."""
    # Create workspace
    workspace = rx.create_workspace("Test Chart Metadata")

    # Get any viewport for chart metadata testing
    viewports = workspace.viewports
    assert len(viewports) > 0

    # find a chart view from the solution
    views = cp_transient_solution.views
    chart_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CHART), None)
    assert chart_view is not None

    viewport = workspace.assign_view(view=chart_view, wait=True)

    meta = viewport.metadata
    opts = viewport.display_options

    log.info("chart metadata: %s", meta)

    assert meta is not None
    assert isinstance(meta, ChartViewportMetadata)

    # Test chart_names property (read-only, from metadata)
    chart_names = meta.chart_names
    assert isinstance(chart_names, list)
    assert len(chart_names) >= 1
    assert "Min/Max Displacement Over Time" in chart_names
    log.info("Available charts: %s", chart_names)

    # Test active_charts property (from display options)
    active_charts = opts.active_charts
    assert isinstance(active_charts, list)
    assert len(active_charts) > 0
    assert all(c in chart_names for c in active_charts)
    assert "Min/Max Displacement Over Time" in active_charts
    log.info("Active charts: %s", active_charts)

    # Test series_names property (read-only, from metadata)
    series_names = meta.series_names
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
    active_series = opts.active_series
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
    assert isinstance(opts.selected_x_axis, str)
    assert opts.selected_x_axis == "Time/Frequency"
    log.info("Selected X-axis: %s", opts.selected_x_axis)

    # Test show_legend property (from display options)
    assert isinstance(opts.show_legend, bool)
    assert opts.show_legend is True
    log.info("Show legend: %s", opts.show_legend)

    # Test show_table property (from display options)
    assert isinstance(opts.show_table, bool)
    assert opts.show_table is False
    log.info("Show table: %s", opts.show_table)

    # Test split_direction property (from display options)
    assert opts.split_direction == "vertical"
    log.info("Split direction: %s", opts.split_direction)

    # Test modifying active_series
    if len(series_names) >= 2:
        new_series = [series_names[0], series_names[1]]
        with viewport.update_display_options() as opts:
            opts.active_series = new_series
        assert viewport.display_options.active_series == new_series

    # Test modifying active_charts
    if len(chart_names) >= 1:
        with viewport.update_display_options() as opts:
            opts.active_charts = [chart_names[0]]
        assert viewport.display_options.active_charts == [chart_names[0]]

    # Test toggling legend visibility
    opts = viewport.display_options
    opts.show_legend = False
    assert viewport.display_options.show_legend is False

    opts = viewport.display_options
    opts.show_legend = True
    assert viewport.display_options.show_legend is True

    # Test toggling table visibility
    opts = viewport.display_options
    opts.show_table = True
    assert viewport.display_options.show_table is True

    opts = viewport.display_options
    opts.show_table = False
    assert viewport.display_options.show_table is False

    # Test split_direction
    opts = viewport.display_options
    opts.split_direction = "horizontal"
    assert viewport.display_options.split_direction == "horizontal"

    opts = viewport.display_options
    opts.split_direction = "vertical"
    assert viewport.display_options.split_direction == "vertical"

    # Cleanup
    rx.delete_workspace(workspace)


def test_convergence_trackers_viewport_metadata(rx, cp_transient_solution):
    """Test ConvergenceTrackersViewportMetadata."""

    # Create workspace
    workspace = rx.create_workspace("Test Convergence Trackers Metadata")

    # find a convergence trackers view from the solution
    views = cp_transient_solution.views
    conv_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS), None)
    assert conv_view is not None

    viewport = workspace.assign_view(view=conv_view, wait=True)
    meta = viewport.metadata
    log.info("convergence trackers metadata: %s", meta)

    assert meta is not None
    assert isinstance(meta, ConvergenceTrackersViewportMetadata)

    assert viewport.display_options.selected_tracker_name == "Force Convergence"

    with viewport.update_display_options() as opts:
        opts.selected_tracker_name = "Displacement Convergence"
    assert viewport.display_options.selected_tracker_name == "Displacement Convergence"


def test_contact_trackers_viewport_metadata(rx, cp_transient_solution):
    """Test ContactTrackersViewportMetadata."""

    # Create workspace
    workspace = rx.create_workspace("Test Contact Trackers Metadata")

    # find a contact trackers view from the solution
    views = cp_transient_solution.views
    contact_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CONTACT_TRACKERS), None)
    assert contact_view is not None

    viewport = workspace.assign_view(view=contact_view, wait=True)

    meta = viewport.metadata
    log.info("contact trackers metadata: %s", meta)

    assert meta is not None
    assert isinstance(meta, ContactTrackersViewportMetadata)

    opts = viewport.display_options

    # Test inherited chart display options
    assert isinstance(opts.show_legend, bool)
    assert isinstance(opts.show_table, bool)
    assert opts.split_direction in ["horizontal", "vertical"]

    # Test series_names property (read-only, from metadata)
    assert isinstance(meta.series_names, list)
    assert len(meta.series_names) > 0

    # Check specific expected series names from contact tracking
    expected_series = [
        "Number of Contact Elements in Contact",
        "Max. Contact Pressure",
        "Max. Friction Stress",
    ]
    for expected in expected_series:
        assert expected in meta.series_names, f"Expected series '{expected}' not found"

    log.info("Available series: %s", meta.series_names[:5])  # Log first 5

    # Test active_series property (from display options)
    active_series = opts.active_series
    assert isinstance(active_series, list)
    assert len(active_series) > 0
    assert all(s in meta.series_names for s in active_series)
    log.info("Active series: %s", active_series)

    # Test toggling active series
    if len(meta.series_names) >= 2:
        new_series = [meta.series_names[0], meta.series_names[1]]
        opts = viewport.display_options
        opts.active_series = new_series
        assert viewport.display_options.active_series == new_series

    # Test contact tracker names (read-only, from metadata)
    contact_trackers = meta.contact_tracker_names
    assert isinstance(contact_trackers, list)
    assert len(contact_trackers) >= 2, "Expected at least 2 contact tracker pairs"

    # Verify expected contact tracker pattern
    for tracker in contact_trackers:
        assert "Solid" in tracker
        assert "ID:" in tracker

    log.info("Contact trackers: %s", contact_trackers)

    # Test toggling legend visibility
    original_legend = opts.show_legend
    opts = viewport.display_options
    opts.show_legend = not original_legend
    assert viewport.display_options.show_legend == (not original_legend)

    # Test toggling table visibility
    original_table = viewport.display_options.show_table
    opts = viewport.display_options
    opts.show_table = not original_table
    assert viewport.display_options.show_table == (not original_table)

    # Test split direction
    opts = viewport.display_options
    opts.split_direction = "horizontal"
    assert viewport.display_options.split_direction == "horizontal"

    # Cleanup
    rx.delete_workspace(workspace)


@pytest.mark.images
@pytest.mark.flaky(reruns=3, reruns_delay=1)
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
    initial_cam = viewport.display_options.camera_position
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
        opts = viewport.display_options
        opts.camera_position = cam.with_zoom(initial_zoom).with_translation(*initial_translation)

        # Take snapshot with clean settings
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
        assert len(snapshot_data) > 0

        # image comparison
        assert snapshot_data == snapshot(name=name)

    # Cleanup
    rx.delete_workspace(workspace)


@pytest.mark.images
@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_result_display_options_snapshots(
    rx, cp_transient_solution, snapshot, snapshot_settings_with_legend
):
    """Test snapshot comparisons for result display option changes."""
    sol = cp_transient_solution

    view = next((v for v in sol.views if "Displacement" in v.name), None)
    assert view is not None

    # Enable all time steps so set_id can be changed freely
    time_frequencies = sol.time_frequencies
    assert len(time_frequencies) >= 2
    first_tf = time_frequencies[0]
    last_tf = time_frequencies[-1]

    view.definition.all_sets = True
    view.definition.last_set = False
    sol.update_plot(view.definition)

    workspace = rx.create_workspace("Test Result Display Options")
    viewport = workspace.assign_view(view=view, wait=True)

    opts = viewport.display_options
    assert isinstance(opts, PlotDisplayOptions)

    opts.result_options = ResultDisplayOptions(set_id=last_tf.set_id)

    _ = viewport.take_snapshot(settings=snapshot_settings_with_legend)

    # Different component indices produce visually distinct color distributions
    for name, component_index in [("component_x", 0), ("component_y", 1), ("component_z", 2)]:
        with viewport.update_display_options() as opts:
            opts.result_options.component_index = component_index
            opts.result_options.legend_range = None  # reset legend range to auto for new component
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings_with_legend)
        assert snapshot_data == snapshot(name=name)

    # reset some options for further tests

    opts = viewport.display_options
    assert isinstance(opts, PlotDisplayOptions)
    opts.result_options = ResultDisplayOptions(component_index=-1)
    assert viewport.display_options.result_options.component_index == -1

    # Deformation scale changes the shape of the deformed mesh
    for name, scale in [("deformation_1x", 1.0), ("deformation_5x", 5.0)]:
        with viewport.update_display_options() as opts:
            opts.result_options.deformation_scale = scale
        snapshot_data = viewport.take_snapshot(settings=snapshot_settings_with_legend)
        assert snapshot_data == snapshot(name=name)

    # reset some options for further tests
    opts = viewport.display_options
    opts.result_options.deformation_scale = 1

    # use_global_min_max affects how the legend range is computed
    opts.result_options = ResultDisplayOptions(
        set_id=first_tf.set_id,
        deformation_scale=1.0,
        use_global_min_max=False,
    )

    assert snapshot(name="use_local_min_max") == viewport.take_snapshot(
        settings=snapshot_settings_with_legend
    )

    # legend_range pins the color scale to a fixed interval
    opts = viewport.display_options
    opts.result_options = ResultDisplayOptions(
        set_id=last_tf.set_id,
        deformation_scale=1.0,
        use_global_min_max=False,
        legend_range=(0.0, 5e-5),
    )

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

    import time

    time.sleep(5)

    bodies = sol.bodies
    solid186_body_ids = []
    for body in bodies:
        if "SOLID186" in body.element_types:
            solid186_body_ids.append(body.id)

    # Test visible_bodies property
    opts = viewport.display_options
    opts.visible_bodies = solid186_body_ids
    assert viewport.display_options.visible_bodies == solid186_body_ids

    # image comparison
    snapshot_data = viewport.take_snapshot(settings=snapshot_settings)
    assert snapshot_data == snapshot(name="SOLID186_bodies")

    # Cleanup
    rx.delete_workspace(workspace)
