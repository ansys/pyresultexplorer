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
.. _trackers_viewport_options_example:

Work with contact and convergence trackers
===========================================

This example demonstrates how to work with tracker viewports in Result Explorer:

- **Convergence trackers** to monitor solver convergence across iterations.
- **Contact trackers** to visualize and analyze contact behavior in transient simulations.
- **Tracker viewport metadata** to read and display properties of tracker visualizations.
- **Active series configuration** for contact trackers to select specific analysis types.
- **Display options** to customize tracker visualization (legend, table, split direction).

This example uses a transient contact analysis result with convergence and
contact tracking data.
"""

# %%
# Import the Result Explorer dependencies.
from ansys.result_explorer.core import (
    ContactTrackersViewportMetadata,
    launch_result_explorer,
)
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
# Load example data
# ------------------
# Create a solution from the transient contact analysis.
rst_path = get_example_file(ExampleKeys.RST_CP_TRANSIENT)

sol = rx.create_solution(
    name="Contact Transient Analysis",
    file_path=rst_path,
)
print(f"Created solution: {sol.name}")
print(f"  Elements: {sol.n_elements}, Nodes: {sol.n_nodes}")

# %%
# Find tracker views
# -------------------
# Locate convergence and contact trackers views in the solution.
convergence_view = sol.convergence_trackers_view
contact_view = sol.contact_trackers_view

assert convergence_view is not None, "Convergence trackers view not found in solution"
assert contact_view is not None, "Contact trackers view not found in solution"

print(f"Found convergence trackers view: {convergence_view.name}")
print(f"Found contact trackers view: {contact_view.name}")

# %%
# Create workspace with grid layout
# -----------------------------------
# Create a workspace with a 2x1 grid for tracker viewports.
workspace = rx.create_workspace(name="Tracker Viewports", rows=2, cols=1)
print(f"Created workspace with {len(workspace.viewport_ids)} viewports (2x1 grid)")

# %%
# Configure convergence trackers viewport
# ----------------------------------------
# Assign and configure the convergence trackers view.
conv_viewport = workspace.viewports[0]
conv_viewport.set_view(convergence_view, wait=True)

conv_opts = conv_viewport.display_options
print("\nConfiguring convergence trackers viewport:")
print(f"  Selected tracker: {conv_opts.selected_tracker_name}")

conv_viewport.save_snapshot(
    file_path="020-convergence-trackers.png", settings=get_example_snapshot_settings()
)

# %%
# Configure contact trackers viewport
# ------------------------------------
# Assign and configure the contact trackers view with available options.
contact_viewport = workspace.viewports[1]
contact_viewport.set_view(contact_view, wait=True)

contact_meta: ContactTrackersViewportMetadata = contact_viewport.metadata
print("\nConfiguring contact trackers viewport:")

# Show available trackers
trackers = contact_meta.contact_tracker_names
print(f"  Available contact trackers: {len(trackers)}")
for tracker in trackers:
    print(f"    - {tracker}")

# Configure active trackers
contact_opts = contact_viewport.display_options
contact_opts.active_contact_trackers = trackers

# Show available series
series = contact_meta.series_names
print(f"  Available data series: {len(series)}")
for s in series:
    print(f"    - {s}")

contact_viewport.save_snapshot(
    file_path="020-contact-trackers.png", settings=get_example_snapshot_settings()
)

# %%
# Set display options
# --------------------
# Configure active series and display options for the contact viewport.
contact_opts.active_series = ["Max. Normal Stiffness"]
print(f"\n  Active series set to: {contact_opts.active_series}")

with contact_viewport.update_display_options() as contact_opts:
    contact_opts.show_legend = True
    contact_opts.show_table = True
    contact_opts.split_direction = "horizontal"
    print("  Legend enabled, table enabled, split direction: horizontal")

print("\nViewport configuration complete!")
print(f"Workspace '{workspace.name}' is ready with tracker views configured.")

rx.stop()
