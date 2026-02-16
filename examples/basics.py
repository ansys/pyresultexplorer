import os

import matplotlib.image as img
import matplotlib.pyplot as plt
from slugify import slugify

from ansys.result_explorer.core.client import Client
from ansys.result_explorer.core.models import ViewportDirection

## rx = Client.connect_with_token("<insert_your_token_here>")
rx = Client(grpc_port=50000, session_id=None)

workspaces = rx.list_workspaces()
print("Existing workspaces:")
for ws in workspaces:
    print(f" - {ws}")

workspace = rx.create_workspace(name="PyRX Workspace")

workspaces = rx.list_workspaces()
print("Existing workspaces after creation:")
for ws in workspaces:
    print(f" - {ws}")

# list viewports in the workspace
viewports = workspace.viewports
print("Viewports in workspace:")
for vp in viewports:
    print(f" - {vp}")

sol_name = "PyRX Solution"
sol = rx.create_solution(
    result_provider_name="Local",
    name=sol_name,
    file_path=r"D:\Models\mech-post\cylinder_plate\d3plot",
)
print(f"Created solution:\n{sol}")

solutions = rx.list_solutions()
print("Existing solutions:")
for sol in solutions:
    print(f" - {sol.name}")

views = sol.views
print("Views in solution:")
for v in views:
    print(f" - {v}")

view = next((v for v in views if "Displacement" in v.name), None)
assert view is not None

print(f"Opening view: {view.name} in the workspace.")
viewport = workspace.assign_view(view=view, wait=True)
print(f"Assigned viewport: {viewport}")

# print("Taking snapshot...")
snapshot_data = viewport.take_snapshot()

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

# set sync options for the workspace
print("Setting workspace sync options...")
workspace.set_sync(camera=True, time_freq=True, legend=True)

# set viewport to fullscreen
print("Setting viewport to fullscreen...")
workspace.set_fullscreen_viewport(viewport=top_left_viewport)

# exit fullscreen
print("Exiting fullscreen...")
workspace.exit_fullscreen()

# modify view metadata
print("Modifying view metadata...")
meta = viewport.metadata
meta.show_mesh_edges = not meta.show_mesh_edges
meta.show_min_max_labels = True
viewport.modify_view_metadata(
    metadata=meta,
)

# take new snapshot
snapshot_data = top_left_viewport.take_snapshot()

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
workspace.delete_viewport(viewport=bottom_right_viewport)

# delete the solution
print("Deleting the solution...")
rx.delete_solution(solution=sol)
