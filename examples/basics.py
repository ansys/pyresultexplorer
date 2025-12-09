from ansys.result_explorer.core.client import Client

rx = Client(port=50000)

sol = rx.create_solution(
    result_provider_name="Local",
    name="PyRX Solution",
    file_path=r"D:\Models\mech-post\beam_2_mat.rst",
)

workspaces = rx.list_workspaces()

workspace = rx.create_workspace(name="PyRX Workspace")
