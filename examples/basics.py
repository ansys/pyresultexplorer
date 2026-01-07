import os
import time

import matplotlib.image as img
import matplotlib.pyplot as plt
from slugify import slugify

from ansys.result_explorer.core.client import Client

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

views = rx.get_views(solution_id=sol.id)
print(views)

view = next((v for v in views.views if "Displacement" in v.name), None)
assert view is not None

print(f"Opening view: {view.name} in the workspace.")
portal_id = rx.assign_view(workspace_id=workspace.id, view_id=view.id)

print("Waiting for the view to load...")
time.sleep(1)  # review in the web repo

print("Taking snapshot...")
snapshot_data = rx.take_snapshot(portal_id=portal_id)

print("Saving snapshot to file...")
file_name = slugify(sol_name + " - " + view.name) + ".png"
with open(file_name, "wb") as image_file:
    image_file.write(snapshot_data)

print(f"Snapshot saved to: {os.path.abspath(file_name)}")

print("Displaying snapshot...")
im = img.imread(file_name)
plt.imshow(im)
plt.show()
