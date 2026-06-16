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

"""
.. _workspace_and_views_example:

Workspaces, Solutions, and View Management
===========================================

This example demonstrates advanced PyResultExplorer functionality including:

- **Workspace management** for organizing and accessing visualization sessions.
- **Solution management** to load and work with result data.
- **View assignment** to display specific analysis results in viewports.
- **Viewport layouts** by creating multiple viewports in grid configurations.
- **Display options** to customize visualization properties like mesh edges and labels.
- **Snapshots** to capture and save viewport visualizations as images.
- **Synchronization** of camera, time steps, and color ranges across viewports.

This example uses a transient structural analysis result with multiple load cases.
"""

# %%
# Import the standard library and third-party dependencies.

from slugify import slugify

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import launch_result_explorer
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)
from ansys.result_explorer.core.models import ViewportDirection

# %%
# Launch Result Explorer
# -----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# %%
# Locate Example Data
# --------------------
# Get the path to the example result file. This file contains transient results
# with multiple load cases for demonstration.
rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)

# %%
# Manage Workspaces
# ------------------
# List existing workspaces and create a new one for this example.
workspaces = rx.list_workspaces()
print("Existing workspaces:")
for ws in workspaces:
    print(f" - {ws}")

# %%
# Create a new workspace to organize our visualization session.
workspace = rx.create_workspace(name="PyRX Workspace")

workspaces = rx.list_workspaces()
print("Existing workspaces after creation:")
for ws in workspaces:
    print(f" - {ws}")

# %%
# List viewports in the newly created workspace.
viewports = workspace.viewports
print("Viewports in workspace:")
for vp in viewports:
    print(f" - {vp}")

# %%
# Create and Manage Solutions
# ----------------------------
# Create a solution from the result file and list available views.
sol_name = "PyRX Solution"
sol = rx.create_solution(
    name=sol_name,
    file_path=rst_path,
)
print(f"Created solution:\n{sol}")

# %%
# List all existing solutions in the Result Explorer instance.
solutions = rx.list_solutions()
print("Existing solutions:")
for sol_item in solutions:
    print(f" - {sol_item.name}")

# %%
# List available views in the solution. Views represent specific analysis results
# like displacement, stress, strain, etc.
views = sol.views
print("Views in solution:")
for v in views:
    print(f" - {v}")

# %%
# Assign a View to a Viewport
# ----------------------------
# Find a displacement view and assign it to a viewport in the workspace.
view = next((v for v in views if "Displacement" in v.name), None)
assert view is not None, "No displacement view found in solution"

print(f"Opening view: {view.name} in the workspace.")
viewport = workspace.assign_view(view=view, wait=True)
print(f"Assigned viewport: {viewport}")

# %%
# Capture and Save Snapshots
# ---------------------------
# Take a snapshot of the viewport and save it as a PNG file.
viewport.save_snapshot(
    file_path=slugify(sol_name + " - " + view.name) + ".png",
    settings=get_example_snapshot_settings(),
)

# %%
# Create a Viewport Grid Layout
# -------------------------------
# Create a 2x2 grid by adding viewports in different directions.
print("Creating 2 x 2 grid layout...")
top_left_viewport = viewport
bottom_left_viewport = workspace.create_viewport(
    viewport=top_left_viewport,
    direction=ViewportDirection.VIEWPORT_DIRECTION_BOTTOM,
)

top_right_viewport = workspace.create_viewport(
    viewport=top_left_viewport,
    direction=ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)

bottom_right_viewport = workspace.create_viewport(
    viewport=bottom_left_viewport,
    direction=ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)

# %%
# Configure Viewport Synchronization
# ------------------------------------
# Set synchronization options so that camera, time steps, and color ranges
# are shared across all viewports in the workspace.
print("Setting workspace sync options...")
workspace.set_sync(camera=True, time_freq=True, legend=True)

# %%
# Fullscreen Display
# -------------------
# Set a viewport to fullscreen mode for focused viewing.
print("Setting viewport to fullscreen...")
workspace.set_fullscreen_viewport(viewport=top_left_viewport)

# %%
# Exit fullscreen mode.
print("Exiting fullscreen...")
workspace.exit_fullscreen()

# %%
# Modify Display Options
# -----------------------
# Customize viewport visualization properties using the context manager.
# Toggle mesh edges and enable minimum/maximum labels.
print("Modifying view display options...")
with viewport.update_display_options() as opts:
    opts.show_mesh_edges = not opts.show_mesh_edges
    opts.show_min_max_labels = True

# %%
# Capture a Modified Snapshot
# ----------------------------
# Take a new snapshot after modifying display options and save it as a separate file.
top_left_viewport.save_snapshot(
    file_path=slugify(sol_name + " - " + view.name) + "-modified.png",
    settings=get_example_snapshot_settings(),
)

# %%
# Clean up
# --------------------
# Delete the bottom right viewport to demonstrate viewport deletion.
print("Deleting bottom right viewport...")
workspace.delete_viewport(viewport=bottom_right_viewport)

rx.stop()
