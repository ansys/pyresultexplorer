"""
This example demonstrates how to work with tracker viewports in Result Explorer, including:
- Connecting to the PyResultExplorer service
- Creating a solution from a transient contact analysis result file
- Finding convergence trackers and contact trackers views
- Creating a workspace with a 2x1 (vertical) layout
- Reading and displaying tracker viewport metadata properties
- Configuring active series for contact trackers
- Toggling display options (legend, table, split direction)

Make sure to update the TOKEN variable with an appropriate value before running the example.
"""

import os

from ansys.result_explorer.core import (
    Client,
    ContactTrackersViewportMetadata,
    ConvergenceTrackersViewportMetadata,
)
from ansys.result_explorer.core.models import ViewType

# Path to cp_trans test data (contact + transient analysis)
FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "data", "cp_trans", "file.rst")
)

# Replace this with your connection token
TOKEN = "<YOUR_TOKEN_HERE>"  # noqa E501

rx = Client.connect_with_token(TOKEN)

# Create a solution from the transient contact analysis
sol = rx.create_solution(
    name="Contact Transient Analysis",
    result_provider_name="Local",
    file_path=FILE_PATH,
)
print(f"Created solution: {sol.name}")
print(f"  Elements: {sol.n_elements}, Nodes: {sol.n_nodes}")

# Find convergence trackers and contact trackers views
views = sol.views
convergence_view = next(
    (v for v in views if v.type == ViewType.VIEW_TYPE_CONVERGENCE_TRACKERS), None
)
contact_view = next((v for v in views if v.type == ViewType.VIEW_TYPE_CONTACT_TRACKERS), None)

assert convergence_view is not None, "Convergence trackers view not found in solution"
assert contact_view is not None, "Contact trackers view not found in solution"

print(f"Found convergence trackers view: {convergence_view.name}")
print(f"Found contact trackers view: {contact_view.name}")

# Create a workspace with a 2x1 grid layout
workspace = rx.create_workspace(name="Tracker Viewports", rows=2, cols=1)
print(f"Created workspace with {len(workspace.viewport_ids)} viewports (2x1 grid)")

# Assign convergence trackers view to top viewport
conv_viewport = workspace.viewports[0]
conv_viewport.set_view(convergence_view, wait=True)

# Configure convergence trackers metadata
conv_meta: ConvergenceTrackersViewportMetadata = conv_viewport.metadata
print("\nConfiguring convergence trackers viewport:")
print(f"  Selected tracker: {conv_meta.selected_tracker_name}")


# Assign contact trackers view to bottom viewport
contact_viewport = workspace.viewports[1]
contact_viewport.set_view(contact_view, wait=True)

# Configure contact trackers metadata
contact_meta: ContactTrackersViewportMetadata = contact_viewport.metadata
print("\nConfiguring contact trackers viewport:")

# Show available trackers
trackers = contact_meta.contact_tracker_names
print(f"  Available contact trackers: {len(trackers)}")
for tracker in trackers:
    print(f"    - {tracker}")

# Configure active trackers
contact_meta.active_contact_trackers = trackers

# Show available series
series = contact_meta.series_names
print(f"  Available data series: {len(series)}")
for s in series:
    print(f"    - {s}")

# Configure active series
contact_meta.active_series = ["Max. Normal Stiffness"]
contact_viewport.set_metadata(contact_meta)
print(f"\n  Active series set to: {contact_meta.active_series}")

# Configure display options
contact_meta.show_legend = True
contact_meta.show_table = True
contact_meta.split_direction = "horizontal"
contact_viewport.set_metadata(contact_meta)
print("  Legend enabled, table enabled, split direction: horizontal")

print("\nViewport configuration complete!")
print(f"Workspace '{workspace.name}' is ready with tracker views configured.")
