import os
import time

import matplotlib.image as img
import matplotlib.pyplot as plt
from slugify import slugify

from ansys.result_explorer.core.client import Client

## rx = Client.connect_with_token("<insert_your_token_here>")
rx = Client(grpc_port=50000, http_port=8000, session_id="4914f80b-bc99-4c1c-bfcb-b924b286c73a")

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
    viewport_id=workspace.viewport_ids[0], solution_id=sol.id, view_id=view.id
)

print("Waiting for the view to load...")
time.sleep(1)  # review in the web repo

print("Taking snapshot...")
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
