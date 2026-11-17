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
- **Hot spot inspection** from the viewport metadata.
- **Hot spot filters** in the viewport settings: maximum number, separation
  distance, and value range.
- **Hot spot edits** through an editable copy in the viewport annotations.

"""

# %%
# Import dependencies
import time
from collections.abc import Callable

from ansys.result_explorer.core import (
    AnnotationPlacement,
    Field,
    HotSpotDefinition,
    HotSpotKind,
    Location,
    PlotDefinition,
    PlotViewportMetadata,
    ResolvedAnnotation,
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


def hot_spots_of(viewport: Viewport) -> list[ResolvedAnnotation]:
    """Return the hot spots shown in a plot viewport."""
    metadata = viewport.metadata
    return metadata.hot_spots if isinstance(metadata, PlotViewportMetadata) else []


def wait_for_hot_spots(
    viewport: Viewport,
    condition: Callable[[list[ResolvedAnnotation]], bool] = bool,
    timeout: float = 30.0,
) -> Viewport:
    """Return the viewport once its hot spots meet ``condition``."""
    deadline = time.monotonic() + timeout
    while True:
        viewport = next(v for v in rx.get_workspace(workspace.id).viewports if v.id == viewport.id)
        if condition(hot_spots_of(viewport)) or time.monotonic() > deadline:
            return viewport
        time.sleep(1)


def print_hot_spots(viewport: Viewport) -> None:
    """Print the value and location of each hot spot."""
    for hot_spot in hot_spots_of(viewport):
        result = hot_spot.result
        target = hot_spot.anchor.target
        value = f"{result.value:.4g} {result.unit}" if result else "N/A"
        node = target.id if target else "-"
        print(f"  node {node}: {value} at {hot_spot.mesh_location}")


# %%
# Inspect the hot spots
# ---------------------
# Hot spots are read-only annotations with the resolved result value and
# location.
viewport = wait_for_hot_spots(viewport)
print(f"{len(hot_spots_of(viewport))} hot spots:")
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
print(f"{len(hot_spots_of(viewport))} hot spots after clearing the filters")

# %%
# Edit a hot spot
# ---------------
# Hot spots in the metadata are read-only. Add one to the viewport
# annotations to edit its presentation: the note, the visibility, the card
# placement, and the properties shown on the card. Its location and value
# always come from the data.
highest = hot_spots_of(viewport)[0]
try:
    highest.note = "Highest stress"
except AttributeError as error:
    print(error)

edit = viewport.settings.annotations.add_hot_spot(highest)
with viewport.update_settings() as settings:
    annotation = settings.annotations[edit.id]
    annotation.note = "Highest stress"
    annotation.property_visibility.result_name = True
    annotation.placement = AnnotationPlacement.screen_pinned
    annotation.card_screen_location = (1.0, 0.25)

viewport = wait_for_hot_spots(
    viewport, lambda hot_spots: any(h.note == "Highest stress" for h in hot_spots)
)
edited = next(h for h in hot_spots_of(viewport) if h.id == highest.id)
print(f"{edited.note!r}: {edited.result}")
viewport.save_snapshot(
    file_path="015-hotspots-edited.png", settings=get_example_snapshot_settings()
)

# %%
# Hide the other hot spots by editing them too.
for hot_spot in hot_spots_of(viewport)[1:]:
    viewport.settings.annotations.add_hot_spot(hot_spot).visibility = False

viewport = wait_for_hot_spots(viewport, lambda hot_spots: sum(h.visibility for h in hot_spots) == 1)
viewport.save_snapshot(
    file_path="015-hotspots-highest.png", settings=get_example_snapshot_settings()
)

# %%
# Removing the edited copies restores the original hot spots.
viewport.settings.annotations.clear()

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
