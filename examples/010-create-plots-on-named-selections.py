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
.. _create_plots_example:

Create Plots on Named selections
=============================================

This example demonstrates how to create named selections and use them to
create plots in Result Explorer:

- **Named selections** based on element IDs to filter and organize data.
- **Plot definitions** for displacement and velocity using named selections.
- **Multiple result sets** handling across different timesteps.
- **Viewport assignment** to display plots side-by-side for comparison.

This example uses a transient structural analysis result with multiple
timesteps for visualization.
"""

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import launch_result_explorer, models
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# %%
# Locate Example Data
# --------------------
# Get the path to the example result file.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

# %%
# Create a Workspace and Solution
# --------------------------------
# Create a workspace and load a solution from the result file.
workspace = rx.create_workspace(name="PyRX NS Plot Workspace")

sol_name = "Coupled Field Transient Analysis"
sol = rx.create_solution(
    name=sol_name,
    file_path=rst_path,
)
print(f"Created solution: {sol.name}")

# %%
# Identify Available Result Sets
# --------------------------------
# Verify the solution has multiple timesteps and extract the set IDs.
if sol.n_sets < 2:
    raise RuntimeError("This example requires at least two result sets/timesteps.")

set_ids = sorted({tf.set_id for tf in sol.time_frequencies})
if len(set_ids) < 2:
    raise RuntimeError("Could not find two distinct set IDs in time frequencies.")

set_id_1, set_id_2 = set_ids[0], set_ids[1]
print(f"Using timesteps (set IDs): {set_id_1}, {set_id_2}")

# %%
# Create Named Selections
# ------------------------
# Create named selections based on element IDs for filtering results.
ns_1 = sol.create_named_selection(
    models.NamedSelectionCreate(
        name="Elements NS 1",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
        element_ids=[models.IdsScoping(range=models.Range(min=23, max=28))],
    )
)

ns_2 = sol.create_named_selection(
    models.NamedSelectionCreate(
        name="Elements NS 2",
        type=models.NamedSelectionType.NAMED_SELECTION_TYPE_ELEMENT,
        element_ids=[models.IdsScoping(values=[3, 4, 7, 8, 9, 11, 13, 15, 17, 19])],
    )
)

print(f"Created named selections: {ns_1.name}, {ns_2.name}")

# %%
# Create Plot Definitions
# -------------------------
# Create displacement and velocity plots using the named selections.
existing_view_ids = {v.id for v in sol.views}
plot_1 = sol.create_plot(
    models.PlotDefinitionCreate(
        name=f"Displacement - {ns_1.name} - set {set_id_1}",
        result_type=models.ResultType.RESULT_TYPE_DISPLACEMENT,
        location="Nodal",
        fields=[models.Field(name="displacement", components=["X", "Y", "Z"])],
        named_selection_id=ns_1.id,
        set_ids=[set_id_1],
        all_sets=False,
        last_set=False,
    )
)

existing_view_ids = {v.id for v in sol.views}
plot_2 = sol.create_plot(
    models.PlotDefinitionCreate(
        name=f"Velocity - {ns_2.name} - set {set_id_2}",
        result_type=models.ResultType.RESULT_TYPE_VELOCITY,
        location="Nodal",
        fields=[models.Field(name="velocity", components=["X", "Y", "Z"])],
        named_selection_id=ns_2.id,
        set_ids=[set_id_2],
        all_sets=False,
        last_set=False,
    )
)

# %%
# Assign Plots to Viewports
# ---------------------------
# Display the plots in side-by-side viewports for comparison.
left_viewport = workspace.assign_view(view=plot_1, wait=True)
right_viewport = workspace.create_viewport(
    viewport=left_viewport,
    direction=models.ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)
right_viewport.set_view(plot_2, wait=True)

print("Opened plots in two side-by-side viewports.")
print(f" - Left viewport:  {plot_1.name}")
print(f" - Right viewport: {plot_2.name}")

# take screenshot of the two viewports

left_viewport.display_options.show_mesh_edges = True
left_viewport.save_snapshot(
    "left_viewport.png",
    settings=get_example_snapshot_settings(),
)

right_viewport.display_options.show_mesh_edges = True
right_viewport.save_snapshot(
    "right_viewport.png",
    settings=get_example_snapshot_settings(),
)

rx.stop()
