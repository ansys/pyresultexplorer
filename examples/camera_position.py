"""
This example exercises camera position functionality of the PyResultExplorer API:
- Connecting to the PyResultExplorer service
- Creating a workspace and solution from a result file
- Setting axis-aligned camera positions (top, bottom, front, back, left, right, isometric)
- Reading back the current camera position
- Rotating the camera around each world axis
- Combining rotations

Make sure to update the TOKEN variable with an appropriate value before running.
"""

import os
import time

from ansys.result_explorer.core.client import Client
from ansys.result_explorer.core.objects.viewport import CameraPosition

FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "data", "multiple_connections.rst")
)
TOKEN = "<insert here>"  # noqa E501

# ---------------------------------------------------------------------------
# Connect and set up a workspace / solution
# ---------------------------------------------------------------------------
print("Connecting...")
rx = Client.connect_with_token(TOKEN)

print("Creating workspace...")
workspace = rx.create_workspace(name="Camera Example Workspace")

print("Creating solution...")
sol = rx.create_solution(
    result_provider="Local",
    name="Camera Example Solution",
    file_path=FILE_PATH,
)
print(f"Solution created: {sol}")

# Pick a 3-D view (Displacement preferred, fall back to first available)
views = sol.views
view = next((v for v in views if "Displacement" in v.name), None) or views[0]
print(f"Using view: {view.name}")

print("Assigning view to viewport...")
viewport = workspace.assign_view(view=view, wait=True)
print(f"Viewport ready: {viewport}")
time.sleep(1)

# Read the initial camera set by the app so we can preserve its zoom and
# translation when applying our own preset orientations.
initial_cam = viewport.metadata.camera_position
initial_zoom = initial_cam.zoom if initial_cam is not None else 1.0
initial_translation = initial_cam.translation if initial_cam is not None else (0.0, 0.0, 0.0)
print(f"Initial zoom={initial_zoom}, translation={initial_translation}")


# Helper: apply a camera position and print the result.
# Zoom and translation from the app's initial camera are preserved so that
# the model stays in view when only the orientation changes.
def apply_camera(label: str, cam: CameraPosition) -> None:
    print(f"\n--- {label} ---")
    cam = cam.with_zoom(initial_zoom).with_translation(*initial_translation)
    meta = viewport.metadata
    meta.camera_position = cam
    viewport.set_metadata(meta)

    time.sleep(1)


# ---------------------------------------------------------------------------
# Axis-aligned preset views
# ---------------------------------------------------------------------------
apply_camera("Top view", CameraPosition.top())
apply_camera("Bottom view", CameraPosition.bottom())
apply_camera("Front view", CameraPosition.front())
apply_camera("Back view", CameraPosition.back())
apply_camera("Left view", CameraPosition.left())
apply_camera("Right view", CameraPosition.right_view())
apply_camera("Isometric view", CameraPosition.isometric())

# ---------------------------------------------------------------------------
# Rotations from the isometric base
# ---------------------------------------------------------------------------
iso = CameraPosition.isometric()

apply_camera("Isometric + 30° around X", iso.rotate_x(30))
apply_camera("Isometric + 45° around Y", iso.rotate_y(45))
apply_camera("Isometric + 60° around Z", iso.rotate_z(60))

# Chained rotations
apply_camera(
    "Isometric + 15° X + 30° Y + 45° Z",
    iso.rotate_x(15).rotate_y(30).rotate_z(45),
)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
print("\nCleaning up...")
rx.delete_solution(solution=sol)
rx.delete_workspace(workspace=workspace)
print("Done.")
