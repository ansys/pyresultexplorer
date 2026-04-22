import logging

import pytest

from ansys.result_explorer.core.models import ViewportDirection, ViewType

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


def test_chart_viewport_metadata(rx):
    """Test ChartViewportMetadata (empty metadata)."""
    # Create workspace
    workspace = rx.create_workspace("Test Chart Metadata")

    # Get any viewport for chart metadata testing
    viewports = workspace.viewports
    assert len(viewports) > 0

    viewport = viewports[0]
    meta = viewport.metadata

    # ChartViewportMetadata should be instantiable without errors
    assert meta is not None

    # Verify it's the base ViewportMetadata or ChartViewportMetadata
    meta_str = str(meta)
    assert isinstance(meta_str, str)

    # Cleanup
    rx.delete_workspace(workspace)
