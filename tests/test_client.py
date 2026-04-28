import base64
import json
from unittest.mock import MagicMock

import grpc
import pytest

from ansys.result_explorer.core import __version__
from ansys.result_explorer.core.client import Client, ResultExplorerError


def test_pkg_version():
    import importlib.metadata as importlib_metadata

    # Read from the pyproject.toml
    # major, minor, patch
    read_version = importlib_metadata.version("ansys-result-explorer-core")

    assert __version__ == read_version


def test_api_import():
    from ansys.api.result_explorer.v0.workspace_pb2_grpc import WorkspaceServiceStub  # noqa


def test_grpc_error_not_found():
    """Test ResultExplorerError.from_grpc_error with NOT_FOUND status."""
    mock_error = MagicMock()
    mock_error.code.return_value = grpc.StatusCode.NOT_FOUND
    mock_error.details.return_value = "resource missing"

    result = ResultExplorerError.from_grpc_error(mock_error)
    assert "Resource not found" in str(result)


def test_connect_with_token_missing_host():
    """Test token validation for missing host."""
    token = base64.b64encode(json.dumps({"grpcPort": 5000, "sessionId": "123"}).encode()).decode()
    with pytest.raises(ValueError, match="missing 'host'"):
        Client.connect_with_token(token)


def test_connect_with_token_missing_grpc_port():
    """Test token validation for missing grpcPort."""
    token = base64.b64encode(
        json.dumps({"host": "localhost", "sessionId": "123"}).encode()
    ).decode()
    with pytest.raises(ValueError, match="missing 'grpcPort'"):
        Client.connect_with_token(token)


def test_connect_with_token_missing_session_id():
    """Test token validation for missing sessionId."""
    token = base64.b64encode(json.dumps({"host": "localhost", "grpcPort": 5000}).encode()).decode()
    with pytest.raises(ValueError, match="missing 'sessionId'"):
        Client.connect_with_token(token)
