import hashlib
import logging
from pathlib import Path

import pytest

from ansys.result_explorer.core import (
    CameraPosition,
    ChartViewportMetadata,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersViewportMetadata,
)
from ansys.result_explorer.core.models import SnapshotSettings, ViewportDirection, ViewType

log = logging.getLogger(__name__)


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
    assert viewport.view_id == view.id
    assert viewport.solution_id == sol.id

    # list viewports
    viewports = workspace.viewports
    assert len(viewports) >= 1

    # modify metadata
    meta = viewport.metadata
    meta.show_mesh_edges = not meta.show_mesh_edges
    meta.show_min_max_labels = not meta.show_min_max_labels

    viewport.set_metadata(meta)

    assert viewport.metadata.show_mesh_edges == meta.show_mesh_edges
    assert viewport._pb.metadata["showMeshEdges"] == meta.show_mesh_edges

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

    # Get plot metadata
    meta = viewport.metadata

    # Test show_mesh_edges property
    original_mesh_edges = meta.show_mesh_edges
    meta.show_mesh_edges = not original_mesh_edges
    viewport.set_metadata(meta)
    assert viewport.metadata.show_mesh_edges == (not original_mesh_edges)

    # Test show_min_max_labels property
    original_min_max = meta.show_min_max_labels
    meta.show_min_max_labels = not original_min_max
    viewport.set_metadata(meta)
    assert viewport.metadata.show_min_max_labels == (not original_min_max)

    # Test deformation_scale property
    assert viewport.metadata.deformation_scale == 1.0
    meta.deformation_scale = 2.5
    viewport.set_metadata(meta)
    assert viewport.metadata.deformation_scale == 2.5

    # Cleanup
    rx.delete_workspace(workspace)


def test_mesh_viewport_metadata(rx, multiple_connections_solution):
    """Test MeshViewportMetadata properties."""
    sol = multiple_connections_solution

    # Find a mesh view from the solution
    views = sol.views
    mesh_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_MESH), None)

    if mesh_view is None:
        pytest.skip("No mesh view available in test solution")

    # Create workspace and assign mesh view
    workspace = rx.create_workspace("Test Mesh Metadata")
    viewport = workspace.assign_view(view=mesh_view, wait=True)

    # Get mesh metadata
    meta = viewport.metadata
    log.info("mesh metadata: %s", viewport.metadata)

    # Test explode property
    original_explode = meta.explode
    meta.explode = not original_explode
    viewport.set_metadata(meta)
    assert viewport.metadata.explode == (not original_explode)

    # Test explode_scale_factor property
    meta.explode_scale_factor = 1.5
    viewport.set_metadata(meta)
    assert viewport.metadata.explode_scale_factor == 1.5

    # Test explode_direction property with Literal validation
    meta.explode_direction = "Radial"
    viewport.set_metadata(meta)
    assert viewport.metadata.explode_direction == "Radial"

    meta.explode_direction = "X"
    viewport.set_metadata(meta)
    assert viewport.metadata.explode_direction == "X"

    # Test expanded_groups property
    meta.expanded_groups = ["group1", "group2"]
    viewport.set_metadata(meta)
    assert viewport.metadata.expanded_groups == ["group1", "group2"]

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

    log.info("chart metadata: %s", meta)

    assert meta is not None
    assert isinstance(meta, ChartViewportMetadata)

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

    assert meta.selected_tracker_name == "Force Convergence"


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


@pytest.mark.images
def test_camera_position_snapshots(rx, multiple_connections_solution, snapshot):
    sol = multiple_connections_solution

    # Find a displacement view
    views = sol.views
    view = next((v for v in views if "Displacement" in v.name), None)
    assert view is not None

    # Create workspace and assign view
    workspace = rx.create_workspace("Test Camera Snapshot")
    viewport = workspace.assign_view(view=view, wait=True)

    # Get initial camera zoom/translation to preserve them
    initial_cam = viewport.metadata.camera_position
    initial_zoom = initial_cam.zoom if initial_cam is not None else 1.0
    initial_translation = initial_cam.translation if initial_cam is not None else (0.0, 0.0, 0.0)

    # Create snapshots directory for PNGs
    snapshots_dir = Path(__file__).parent / "__snapshots__" / "camera_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Saving camera snapshots to: {snapshots_dir.absolute()}")

    # Test a few camera presets
    camera_tests = {
        "top": CameraPosition.top(),
        "bottom": CameraPosition.bottom(),
        "front": CameraPosition.front(),
        "isometric": CameraPosition.isometric(),
        "isometric+30x-10z": CameraPosition.isometric().rotate_x(30).rotate_z(-10),
    }

    snapshots_dict = {}
    for name, cam in camera_tests.items():
        # Apply camera with preserved zoom/translation
        meta = viewport.metadata
        meta.camera_position = cam.with_zoom(initial_zoom).with_translation(*initial_translation)
        viewport.set_metadata(meta)

        # Take snapshot with clean settings (no timestamp, logo, etc.)
        settings = SnapshotSettings(
            show_time_stamp=False,
            show_logo=False,
            show_legend=False,
            show_solution_name=False,
            show_result_picker=False,
            transparent_background=False,
            background_color="#FFFFFF",
            height=300,
            width=300,
        )
        snapshot_data = viewport.take_snapshot(settings=settings)
        assert len(snapshot_data) > 0

        # Save as PNG file
        png_file = snapshots_dir / f"camera_{name}.png"
        with open(png_file, "wb") as f:
            f.write(snapshot_data)
        log.info(f"Saved snapshot: {png_file.absolute()}")

        # Store hash in syrupy snapshot for change detection
        file_hash = hashlib.md5(snapshot_data).hexdigest()
        snapshots_dict[name] = {
            "file": str(png_file.relative_to(Path(__file__).parent)),
            "hash": file_hash,
        }

    # Compare hashes using syrupy
    assert snapshots_dict == snapshot

    # Cleanup
    rx.delete_workspace(workspace)
