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

"""
.. _workspace_layout_example:

Create workspace grid layouts
==========================================

This example demonstrates how to create and manage workspace layouts with
various grid configurations in PyResultExplorer:

- **Workspace creation** with custom grid dimensions using rows and columns.
- **Grid layout configurations** from 1x1 to 3x3 grid arrangements.
- **Layout descriptions** showing where each viewport is positioned.
- **Viewport positions** with row and column grid coordinates.

This example showcases the flexibility of Result Explorer's workspace layout
system for organizing and visualizing multiple result sets simultaneously.
"""

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import (
    Component,
    Field,
    Location,
    PlotDefinition,
    ResultFieldName,
    ResultType,
    ViewportPlacement,
    launch_result_explorer,
)
from ansys.result_explorer.core.examples import ExampleKeys, get_example_file
from ansys.result_explorer.core.models import ViewportDirection

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# Create a solution
rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)
sol = rx.create_solution(
    name="Example Solution",
    file_path=rst_path,
)

# %%
# Create workspace grid layouts
# ------------------------------
# Create workspaces with various grid configurations from 1x1 to 3x3 and
# inspect the viewports in each layout.

for r in range(1, 4):
    for c in range(1, 4):
        workspace = rx.create_workspace(name=f"{c}x{r} Grid Workspace", rows=r, cols=c)
        print(f"Created workspace: {workspace.name} (id: {workspace.id})")
        viewports = workspace.viewports
        print(f"Viewport count: {len(viewports)}")
        print(workspace.layout)
        print("-" * 40)

# %%
# Describe where the viewports are
# --------------------------------
# ``workspace.layout`` describes the arrangement as a grid of rows and
# columns. Printing it shows a diagram of the current positions.

workspace = rx.create_workspace(name="Comparison Workspace", rows=2, cols=3)
print(workspace.layout)


# %%
# Assign plots by grid position
# -----------------------------
# Create a plot named after each grid position, then use ``viewport_at()``
# to assign it to the matching viewport. Rows are ordered from top to bottom
# and columns from left to right.


def create_named_plot(name: str):
    """Create a displacement plot with the given name."""
    return sol.create_plot(
        PlotDefinition(
            name=name,
            result_type=ResultType.displacement,
            location=Location.nodal,
            fields=[
                Field(
                    name=ResultFieldName.displacement,
                    components=[Component.X, Component.Y, Component.Z],
                )
            ],
        )
    )


rows, cols = workspace.layout.grid_shape
for row_index in range(rows):
    for column_index in range(cols):
        plot_view = create_named_plot(f"Row {row_index}, Column {column_index}")
        viewport = workspace.viewport_at(row=row_index, column=column_index)
        viewport.set_view(plot_view, wait=True)
        print(f"Assigned {plot_view.name} to viewport {viewport.id}")

# %%
# Describe a layout that is not a grid
# ------------------------------------
# Viewports can also be split freely. A viewport that is not part of a
# regular grid spans several rows or columns, which the layout reports
# through ``row_span`` and ``column_span``.

split_workspace = rx.create_workspace(name="Split Workspace")
left = split_workspace.viewports[0]
right_top = split_workspace.create_viewport(left, ViewportDirection.VIEWPORT_DIRECTION_RIGHT)
split_workspace.create_viewport(right_top, ViewportDirection.VIEWPORT_DIRECTION_BOTTOM)

layout = split_workspace.layout
print(layout)
print(f"Grid shape: {layout.grid_shape}, regular grid: {layout.is_grid}")

left_placement = layout.placement_of(left)
print(f"The left viewport spans {left_placement.row_span} rows.")

# %%
# Assign a view named after the cells that each viewport occupies, so that
# the reported positions can be checked against the application window.


def span_text(label: str, start: int, span: int) -> str:
    """Describe the cells occupied along one direction."""
    if span == 1:
        return f"{label} {start}"
    return f"{label}s {start}-{start + span - 1}"


def position_name(placement: ViewportPlacement) -> str:
    """Describe the position of a placement."""
    return (
        f"{span_text('Row', placement.row, placement.row_span)}, "
        f"{span_text('Column', placement.column, placement.column_span)}"
    )


for placement in layout.placements:
    plot_view = create_named_plot(position_name(placement))
    placement.viewport.set_view(plot_view, wait=True)
    print(f"Assigned {plot_view.name} to viewport {placement.viewport.id}")

rx.stop()
