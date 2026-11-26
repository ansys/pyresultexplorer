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
.. _hot_spots_example:

Detect and inspect hot spots
============================

This example shows how to find the locations of the highest stresses with
hot spots:

- **Hot spot detection** enabled in the plot definition.
- **Hot spot inspection** with ``viewport.hot_spots``.
- **Hot spot filters** in the viewport settings: maximum number, separation
  distance, and value range.
- **Hot spot edits** of the note, the visibility, and the card.

"""

# %%
# Import dependencies
import time
from collections.abc import Callable

from ansys.result_explorer.core import (
    AnnotationPlacement,
    Field,
    HotSpot,
    HotSpotDefinition,
    HotSpotKind,
    Location,
    PlotDefinition,
    ResultFieldName,
    ResultType,
    Viewport,
    launch_result_explorer,
)
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)

# %%
# Launch Result Explorer and load data
# ------------------------------------
# Start a Result Explorer instance and create a solution.
rx = launch_result_explorer()

rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)
sol = rx.create_solution(name="Hot Spots Example Solution", file_path=rst_path)
print(f"Solution created: {sol}")

workspace = rx.create_workspace(name="Hot Spots Example Workspace")

# %%
# Create a plot with hot spot detection
# -------------------------------------
# The hot spot definition makes the server detect the highest values of the
# equivalent stress. ``num_hotspots`` limits the number of candidates per set.
plot = sol.create_plot(
    PlotDefinition(
        result_type=ResultType.stress,
        location=Location.nodal,
        name="Equivalent stress hot spots",
        fields=[Field(name=ResultFieldName.equivalent_von_mises_stress)],
        hot_spot_definition=HotSpotDefinition(kind=HotSpotKind.maximum, num_hotspots=5),
    )
)
print(plot.definition.hot_spot_definition)

viewport = workspace.assign_view(view=plot, wait=True)

# %%
# Define helpers to read hot spots
# --------------------------------
# Result Explorer lists the hot spots shown in the scene after rendering.
# This helper fetches the viewport again until a condition on its hot spots
# is met.


def wait_for_hot_spots(
    viewport: Viewport,
    condition: Callable[[list[HotSpot]], bool] = bool,
    timeout: float = 30.0,
) -> Viewport:
    """Return the viewport once its hot spots meet ``condition``."""
    deadline = time.monotonic() + timeout
    while True:
        viewport = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == viewport.id)
        if condition(viewport.hot_spots) or time.monotonic() > deadline:
            return viewport
        time.sleep(1)


def print_hot_spots(viewport: Viewport) -> None:
    """Print the value and location of each hot spot."""
    for hot_spot in viewport.hot_spots:
        result = hot_spot.result
        target = hot_spot.anchor.target
        value = f"{result.value:.4g} {result.unit}" if result else "N/A"
        node = target.id if target else "-"
        print(f"  node {node}: {value} at {hot_spot.mesh_location}")


# %%
# Inspect the hot spots
# ---------------------
# Each hot spot gives its result value and location, read from the data.
viewport = wait_for_hot_spots(viewport)
print(f"{len(viewport.hot_spots)} hot spots:")
print_hot_spots(viewport)
viewport.save_snapshot(
    file_path="015-hotspots-detected.png", settings=get_example_snapshot_settings()
)

# %%
# Filter the hot spots
# --------------------
# The viewport settings filter the detected hot spots without running the
# detection again. Keep the three highest values, at least 5 mm apart.
with viewport.update_settings() as settings:
    settings.hot_spots_max_number = 3
    settings.hot_spots_separation_distance = 0.005

viewport = wait_for_hot_spots(viewport, lambda hot_spots: 0 < len(hot_spots) <= 3)
print("Three highest hot spots, 5 mm apart:")
print_hot_spots(viewport)

# %%
# Restrict the hot spots to a value range. A ``None`` bound is open.
viewport.settings.hot_spots_threshold_range = (None, 2.1e8)
viewport = wait_for_hot_spots(
    viewport, lambda hot_spots: all(h.result and h.result.value <= 2.1e8 for h in hot_spots)
)
print("Hot spots below 210 MPa:")
print_hot_spots(viewport)

# %%
# Clear the filters to show all the detected hot spots again.
with viewport.update_settings() as settings:
    settings.hot_spots_max_number = None
    settings.hot_spots_separation_distance = None
    settings.hot_spots_threshold_range = None

viewport = wait_for_hot_spots(viewport, lambda hot_spots: len(hot_spots) == 5)
print(f"{len(viewport.hot_spots)} hot spots after clearing the filters")

# %%
# Edit a hot spot
# ---------------
# The presentation of a hot spot is editable: the note, the visibility, the
# card placement, and the properties shown on the card. Its location and
# value always come from the data. Batch the edits to apply them in a single
# call.
highest = viewport.hot_spots[0]
with viewport.update_settings():
    highest.note = "Highest stress"
    highest.property_visibility.result_name = True
    highest.placement = AnnotationPlacement.screen_pinned
    highest.card_screen_location = (1.0, 0.25)

print(f"{highest.note!r}, edited: {highest.is_edited}, result: {highest.result}")
viewport.save_snapshot(
    file_path="015-hotspots-edited.png", settings=get_example_snapshot_settings()
)

# %%
# Hide the other hot spots.
with viewport.update_settings():
    for hot_spot in viewport.hot_spots[1:]:
        hot_spot.visibility = False

viewport.save_snapshot(
    file_path="015-hotspots-highest.png", settings=get_example_snapshot_settings()
)

# %%
# Reset the hot spots to restore their original presentation.
for hot_spot in viewport.hot_spots:
    hot_spot.reset()

# %%
# Detect the lowest values
# ------------------------
# Update the hot spot definition of the plot to detect the lowest values.
# The open viewport reloads the plot data with the new hot spots.
definition = plot.definition
definition.hot_spot_definition = HotSpotDefinition(kind=HotSpotKind.minimum, num_hotspots=3)
plot = sol.update_plot(definition)

highest_value = highest.result.value if highest.result else 0.0
viewport = wait_for_hot_spots(
    viewport,
    lambda hot_spots: (
        bool(hot_spots)
        and all(h.result and h.result.value < 0.01 * highest_value for h in hot_spots)
    ),
)
print("Lowest values:")
print_hot_spots(viewport)

rx.stop()
