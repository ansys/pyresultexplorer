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
.. _plot_display_options_example:

Customize Plot Display Options and Animate Results
===================================================

This example demonstrates how to configure plot display options and animate
results across time steps in Result Explorer:

- **Plot view management** to find and configure displacement views.
- **Display options customization** for deformation, component selection,
  and mesh visualization.
- **Result range control** using global min/max settings.
- **Animation through time steps** by updating plot properties dynamically.

This example uses a transient contact analysis result to showcase animation
and visualization options across multiple timesteps.
"""

# %%
# Import the standard library and third-party dependencies.

import imageio

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import (
    PlotView,
    launch_result_explorer,
)
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)
from ansys.result_explorer.core.models import ViewType

# %%
# Launch Result Explorer
# ----------------------
# Start a Result Explorer instance for this example.
rx = launch_result_explorer()

# %%
# Load Example Data
# ------------------
# Create a solution from the transient contact analysis data.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

sol = rx.create_solution(
    name="Contact Transient Analysis",
    file_path=rst_path,
)
print(f"Created solution:\n{sol}")

# %%
# Find and Configure a Plot View
# --------------------------------
# Locate the displacement view and configure it to show all time steps.
views = sol.views
disp_view: PlotView = next(
    (v for v in views if v.type == ViewType.VIEW_TYPE_PLOT and "Displacement" in v.name), None
)

assert disp_view is not None, "Displacement view not found in solution"

disp_view.definition.all_sets = True
disp_view.definition.last_set = False
sol.update_plot(disp_view.definition)

print(f"Found displacement view: {disp_view.name}")

# %%
# Create Workspace and Assign View
# ----------------------------------
# Create a workspace and assign the displacement view to a viewport.
workspace = rx.create_workspace(name="Plot Viewports")
print(f"Created workspace with {len(workspace.viewport_ids)} viewports (2x1 grid)")

disp_viewport = workspace.viewports[0]
disp_viewport = disp_viewport.set_view(disp_view, wait=True)

# %%
# Customize Display Options
# ----------------------------
# Configure plot display options including deformation scale and mesh edges.
with disp_viewport.update_display_options() as disp_opts:
    disp_opts.result_options.use_global_min_max = True
    disp_opts.result_options.component_index = 0
    disp_opts.result_options.deformation_scale = 2
    disp_opts.result_options.legend_range = None  # auto-range based on current component values
    disp_opts.show_mesh_edges = True

# Save thumbnail image
disp_viewport.save_snapshot(
    file_path="011-plot-display-options-set-1.png", settings=get_example_snapshot_settings()
)

# %%
# Animate Through Time Steps
# ----------------------------
# Animate the displacement plot across all available time steps and save as a GIF.
time_frequencies = sol.time_frequencies
print(f"Animating over {len(time_frequencies)} time steps...")

with imageio.get_writer("011-plot-display-options.gif", mode="I") as writer:
    for i, tf in enumerate(time_frequencies):
        print(f"  Step {i}: set_id={tf.set_id}, value={tf.value}")
        with disp_viewport.update_display_options() as opts:
            # Update the set_id to change the displayed time step
            opts.result_options.set_id = tf.set_id

        meta = disp_viewport.metadata
        for extreme in [meta.active_result.min, meta.active_result.max]:
            print(f"    entity={extreme.entity_id}, value={extreme.value}, pos={extreme.position}")

        snapshot_data = disp_viewport.take_snapshot(settings=get_example_snapshot_settings())
        image = imageio.imread(snapshot_data)
        writer.append_data(image)

rx.stop()
