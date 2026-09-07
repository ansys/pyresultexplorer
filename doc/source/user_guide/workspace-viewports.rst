Workspaces and viewports
########################

Result Explorer allows you to create multiple workspaces, each with its own layout of viewports.
A workspace is a collection of viewports that can display different views of the solution data.
You can switch between workspaces to organize your analysis and visualization tasks.


Managing workspaces
===================

Using the :class:`Client <ansys.result_explorer.core.Client>` object, you can list, create, rename, and delete workspaces.

.. code-block:: python

   # List all workspaces
   workspaces = rx.list_workspaces()

   # Create a new workspace
   workspace = rx.create_workspace(name="Example Workspace")

   # Create a workspace with a grid layout of 2 rows and 3 columns
   workspace = rx.create_workspace(name="Grid Workspace", rows=2, cols=3)

   # Delete a workspace
   rx.delete_workspace(workspace)

The :class:`Workspace <ansys.result_explorer.core.Workspace>` object allows you to:

- Manage the viewports within that workspace, including creating new viewports and assigning views to them.
- Enter full screen mode for a specific viewport to focus on a particular view.
- Set synchronization options to link viewports together.

Managing viewports
==================

A workspace can contain multiple viewports, which you access through the :attr:`Workspace.viewports <ansys.result_explorer.core.Workspace.viewports>` attribute.
Each viewport can display a view of the solution data, and you can customize the display options for each viewport independently.

Accessing and assigning views
-----------------------------

You can list all viewports in a workspace and assign views to them:

.. code-block:: python

    # Get all viewports in a workspace
    viewports = workspace.viewports

    # Assign a view to a viewport
    first_viewport = viewports[0]
    first_viewport.set_view(displacement_view, wait=True)

    # Or use the convenient shortcut to assign a view to the first viewport
    viewport = workspace.assign_view(view=displacement_view, wait=True)

Describing the viewport layout
------------------------------

The :attr:`Workspace.layout <ansys.result_explorer.core.Workspace.layout>` attribute
describes where each viewport is positioned. Every layout is described as a grid of
rows and columns, and printing it shows a diagram of the current arrangement followed
by a legend of viewport IDs:

.. code-block:: python

   print(workspace.layout)

.. code-block:: text

   +---------------------+---------------------+
   | [0] r0c0            | [1] r0c1            |
   |                     |                     |
   |                     |                     |
   |                     +---------------------+
   |                     | [2] r1c1            |
   |                     |                     |
   |                     |                     |
   +---------------------+---------------------+
   [0] ad661e90-4bf1-4df2-9f03-4f12e28b381e (row 0, column 0, 2x1 cells)
   [1] fb469094-bdc8-4037-89fe-b193be36666e (row 0, column 1, 1x1 cells)
   [2] 2be6dda3-1889-44d2-bbfb-4c59f28fa548 (row 1, column 1, 1x1 cells)

Viewports that are not part of a regular grid span several rows or columns.
In the layout above, the first viewport spans both rows of the first column:

.. code-block:: python

   layout = workspace.layout

   layout.grid_shape  # (2, 2)
   layout.is_grid  # False

   placement = layout.placement_of(viewport)
   placement.row, placement.column  # (0, 0)
   placement.row_span, placement.column_span  # (2, 1)

Each :class:`ViewportPlacement <ansys.result_explorer.core.ViewportPlacement>` also
reports the fraction of the workspace that the viewport covers through its ``x``,
``y``, ``width``, and ``height`` attributes.

Accessing viewports by grid position
------------------------------------

Use :meth:`Workspace.viewport_at <ansys.result_explorer.core.Workspace.viewport_at>`
to access a viewport by its position. Rows are ordered from top to bottom and
columns are ordered from left to right, and both indexes start at zero.
A viewport that spans several cells is returned for each cell that it occupies.

.. code-block:: python

    workspace = rx.create_workspace(name="Grid Workspace", rows=2, cols=3)

    # Assign a view to the lower-right viewport.
    lower_right = workspace.viewport_at(row=1, column=2)
    lower_right.set_view(displacement_view, wait=True)

    # Get every viewport as rows of the grid.
    grid = workspace.viewport_grid()

Creating and deleting viewports
-------------------------------

You can create new viewports by splitting existing ones in different directions:

.. code-block:: python

    from ansys.result_explorer.core.models import ViewportDirection

    # Create a new viewport to the right of the first viewport
    right_viewport = workspace.create_viewport(
        viewport=viewports[0],
        direction=ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
    )

    # Create a new viewport below the first viewport
    bottom_viewport = workspace.create_viewport(
        viewport=viewports[0],
        direction=ViewportDirection.VIEWPORT_DIRECTION_BOTTOM,
    )

    # Delete a viewport
    workspace.delete_viewport(right_viewport)

Customizing viewport display options
------------------------------------

Each viewport has display options that you can customize independently:

.. code-block:: python

    # Access display options for a viewport
    opts = viewport.display_options

    # For plot viewports, customize visualization settings
    opts.show_mesh_edges = True
    opts.show_min_max_labels = True

    # Set deformation scale and component
    opts.result_options.deformation_scale = 2.0
    opts.result_options.component_index = 0

    # Batch multiple changes efficiently
    with viewport.update_display_options() as opts:
        opts.show_mesh_edges = True
        opts.explode = True
        opts.result_options.deformation_scale = 3.0

Display options are specific to the type of view being displayed in the viewport.
For example, plot viewports have options for showing mesh edges and min/max labels,
while chart viewports have options for hiding/showing the legend and data table.


Direct commit vs. batch update of display options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


When you assign a display option directly
(for example, ``opts.show_mesh_edges = True``), it immediately commits the change
to the app. For multiple changes, use the :meth:`viewport.update_display_options() <ansys.result_explorer.core.Viewport.update_display_options>`
context manager to batch all updates into a single API call, which is more
efficient:

.. code-block:: python

    # Inefficient: 3 API calls
    opts = viewport.display_options
    opts.show_mesh_edges = True        # API call 1
    opts.explode = True                # API call 2
    opts.result_options.set_id = 3     # API call 3

    # Efficient: 1 API call
    with viewport.update_display_options() as opts:
        opts.show_mesh_edges = True
        opts.explode = True
        opts.result_options.set_id = 3


Saving viewport snapshots
-------------------------

You can save viewport visualizations as PNG images:

.. code-block:: python

    from ansys.result_explorer.core.models import SnapshotSettings

    # Save a snapshot with default settings
    viewport.save_snapshot("displacement_view.png")

    # Save with custom snapshot settings
    settings = SnapshotSettings(
        height=600,
        width=800,
        show_time_stamp=False,
        show_logo=True,
        show_legend=True,
        show_solution_name=False,
        show_result_picker=True,
        transparent_background=False,
        background_color="#FFFFFF",
    )
    viewport.save_snapshot("displacement_view_custom.png", settings=settings)


