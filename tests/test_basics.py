from ansys.result_explorer.core import __version__


def test_pkg_version():
    import importlib.metadata as importlib_metadata

    # Read from the pyproject.toml
    # major, minor, patch
    read_version = importlib_metadata.version("ansys-result-explorer-core")

    assert __version__ == read_version


def test_grpc_import():
    try:
        import grpc  # noqa: F401
    except ImportError as e:
        raise ImportError("The grpc module is not installed.") from e


def test_api_import():
    from ansys.api.result_explorer.v0.workspace_pb2_grpc import WorkspaceServiceStub  # noqa


def test_web_connection(rx):
    workspaces = rx.list_workspaces()
    assert workspaces[0].name == "Workspace 1"


def test_create_workspace(rx):
    workspace = rx.create_workspace(name="PyRX Workspace")
    assert workspace.name == "PyRX Workspace"
