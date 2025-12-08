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
