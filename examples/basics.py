import os

import matplotlib.image as img
import matplotlib.pyplot as plt
from slugify import slugify

from ansys.result_explorer.core.client import Client
from ansys.result_explorer.core.models import ViewportDirection

## rx = Client.connect_with_token("<insert_your_token_here>")
rx = Client(grpc_port=50000, http_port=8000, session_id=None)

workspaces = rx.list_workspaces()
print(workspaces)

workspace = rx.create_workspace(name="PyRX Workspace")

workspaces = rx.list_workspaces()
print(workspaces)

sol_name = "PyRX Solution"
sol = rx.create_solution(
    result_provider_name="Local",
    name=sol_name,
    file_path=r"D:\Models\mech-post\cylinder_plate\d3plot",
)
print(f"Created solution '{sol.name}' with ID: {sol.id}")

solutions = rx.list_solutions()
# print(solutions)

views = sol.views
print(views)

view = next((v for v in views if "Displacement" in v.name), None)
assert view is not None

print(f"Opening view: {view.name} in the workspace.")
viewport = rx.assign_view(
    viewport_id=workspace.viewport_ids[0], solution_id=sol.id, view_id=view.id, wait=True
)
print(viewport)

viewports = rx.list_viewports(workspace_id=workspace.id)
print(viewports)

# print("Taking snapshot...")
snapshot_data = rx.take_snapshot(viewport_id=viewport.id)

print("Saving snapshot to file...")
file_name = slugify(sol_name + " - " + view.name) + ".png"
with open(file_name, "wb") as image_file:
    image_file.write(snapshot_data)

print(f"Snapshot saved to: {os.path.abspath(file_name)}")

print("Displaying snapshot...")
im = img.imread(file_name)
plt.imshow(im)
plt.show()

# Turn the layout into a 2x2 grid by adding more viewports
print("Creating 2 x 2 grid layout...")
top_left_viewport = viewport
bottom_left_viewport = rx.create_viewport(
    workspace_id=workspace.id,
    viewport_id=top_left_viewport.id,
    direction=ViewportDirection.VIEWPORT_DIRECTION_BOTTOM,
)

top_right_viewport = rx.create_viewport(
    workspace_id=workspace.id,
    viewport_id=top_left_viewport.id,
    direction=ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)

bottom_right_viewport = rx.create_viewport(
    workspace_id=workspace.id,
    viewport_id=bottom_left_viewport.id,
    direction=ViewportDirection.VIEWPORT_DIRECTION_RIGHT,
)

# set sync options for the workspace
print("Setting workspace sync options...")
rx.set_workspace_sync(workspace_id=workspace.id, camera=True, time_freq=True, legend=True)

# set viewport to fullscreen
print("Setting viewport to fullscreen...")
rx.set_fullscreen_viewport(workspace_id=workspace.id, viewport_id=top_left_viewport.id)

# exit fullscreen
print("Exiting fullscreen...")
rx.exit_fullscreen(workspace_id=workspace.id)

# modify view metadata
print("Modifying view metadata...")
meta = viewport.metadata
meta["showMeshEdges"] = not meta["showMeshEdges"]
meta["showMinMaxLabels"] = True
rx.modify_view_metadata(
    viewport_id=top_left_viewport.id,
    metadata=meta,
)

# take new snapshot
snapshot_data = rx.take_snapshot(viewport_id=top_left_viewport.id)

print("Saving snapshot to file...")
file_name = slugify(sol_name + " - " + view.name) + "-modified.png"
with open(file_name, "wb") as image_file:
    image_file.write(snapshot_data)

print(f"Snapshot saved to: {os.path.abspath(file_name)}")

print("Displaying snapshot...")
im = img.imread(file_name)
plt.imshow(im)
plt.show()

# delete the bottom right viewport
print("Deleting bottom right viewport...")
rx.delete_viewport(viewport_id=bottom_right_viewport.id)

# delete the solution
print("Deleting the solution...")
rx.delete_solution(solution_id=sol.id)
