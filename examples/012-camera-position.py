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
.. _camera_position_example:

Control camera position and orientation
========================================

This example demonstrates camera position functionality in PyResultExplorer:

- **Axis-aligned camera positions** (top, bottom, front, back, left, right, isometric).
- **Camera rotation** around world axes (X, Y, Z).
- **Combined transformations** by chaining rotation operations.
- **Viewport-level camera control** for visualization management.

This example showcases various camera positioning and rotation techniques to
navigate and view results from different angles.
"""

# %%
# Import dependencies
from ansys.result_explorer.core import launch_result_explorer
from ansys.result_explorer.core.examples import (
    ExampleKeys,
    get_example_file,
    get_example_snapshot_settings,
)
from ansys.result_explorer.core.objects import CameraPosition

# %%
# Launch Result Explorer and load data
# ------------------------------------
# Start a Result Explorer instance and create a workspace with a solution.
rx = launch_result_explorer()

rst_path = get_example_file(ExampleKeys.RST_MULTIPLE_CONNECTIONS)

print("Creating workspace...")
workspace = rx.create_workspace(name="Camera Example Workspace")

print("Creating solution...")
sol = rx.create_solution(
    name="Camera Example Solution",
    file_path=rst_path,
)
print(f"Solution created: {sol}")

# %%
# Assign a view to a viewport
# ----------------------------
# Pick a 3-D view and assign it to the workspace viewport.
views = sol.plot_views
view = next((v for v in views if "Displacement" in v.name), None) or views[0]
print(f"Using view: {view.name}")

print("Assigning view to viewport...")
viewport = workspace.assign_view(view=view, wait=True)
viewport.display_options.show_mesh_edges = True
print(f"Viewport ready: {viewport}")
viewport.save_snapshot(
    file_path="012-camera-position-initial.png", settings=get_example_snapshot_settings()
)

# %%
# Preserve initial camera state
# ------------------------------
# Read the initial camera state to preserve zoom and translation when
# applying preset orientations.
initial_cam = viewport.display_options.camera_position
initial_zoom = initial_cam.zoom if initial_cam is not None else 1.0
initial_translation = initial_cam.translation if initial_cam is not None else (0.0, 0.0, 0.0)
print(f"Initial zoom={initial_zoom}, translation={initial_translation}")


def apply_camera(label: str, cam: CameraPosition) -> None:
    """Apply a camera position and print the result."""
    print(f"\n--- {label} ---")
    cam = cam.with_zoom(initial_zoom).with_translation(*initial_translation)
    opts = viewport.display_options
    opts.camera_position = cam
    viewport.save_snapshot(
        file_path=f"012-camera-position-{label.replace(' ', '-').lower()}.png",
        settings=get_example_snapshot_settings(),
    )


# %%
# Apply axis-aligned preset views
# --------------------------------
# Set the camera to standard axis-aligned orientations.
apply_camera("Top view", CameraPosition.top())
apply_camera("Bottom view", CameraPosition.bottom())
apply_camera("Front view", CameraPosition.front())
apply_camera("Back view", CameraPosition.back())
apply_camera("Left view", CameraPosition.left())
apply_camera("Right view", CameraPosition.right_view())
apply_camera("Isometric view", CameraPosition.isometric())

# %%
# Apply rotations around world axes
# -----------------------------------
# Rotate the camera from an isometric base around each world axis.
iso = CameraPosition.isometric()

apply_camera("Isometric + 30° around X", iso.rotate_x(30))
apply_camera("Isometric + 45° around Y", iso.rotate_y(45))
apply_camera("Isometric + 60° around Z", iso.rotate_z(60))

# %%
# Combine multiple rotations
# ----------------------------
# Chain multiple rotations to create complex camera orientations.
apply_camera(
    "Isometric + 15° X + 30° Y + 45° Z",
    iso.rotate_x(15).rotate_y(30).rotate_z(45),
)

rx.stop()
