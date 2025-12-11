from slugify import slugify

from ansys.result_explorer.core.client import Client

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
    file_path=r"D:\Models\mech-post\beam_2_mat.rst",
)

views = rx.get_views(solution_id=sol.id)
print(views)

view = next((v for v in views.views if "Min/Max" in v.name), None)
assert view is not None

portal_id = rx.assign_view(workspace_id=workspace.id, view_id=view.id)

snapshot_data = rx.take_snapshot(portal_id=portal_id)

with open(slugify(sol_name + " - " + view.name) + ".png", "wb") as image_file:
    image_file.write(snapshot_data)
