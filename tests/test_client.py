# Copyright (C) 2026 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


def test_default_result_provider(rx):
    """Test default result provider getter and setter."""
    # Verify default result provider is set
    assert rx.default_result_provider == "Local"

    # Try to set an invalid result provider
    with pytest.raises(ValueError, match="Result provider 'NonExistent' not found"):
        rx.default_result_provider = "NonExistent"


def test_list_result_providers(rx):
    """Test listing available result providers."""
    providers = rx.list_result_providers()
    assert len(providers) > 0
    assert any(p.name == "Local" for p in providers)
    # Verify provider structure
    for provider in providers:
        assert hasattr(provider, "name")
        assert hasattr(provider, "solution_ids")


def test_get_result_provider(rx):
    """Test getting a specific result provider."""
    providers = rx.list_result_providers()
    provider = providers[0]
    fetched = rx.get_result_provider(provider.name)
    assert fetched.name == provider.name


def test_result_provider_name_normalization(rx, multiple_connections_solution):
    """Test result provider parameter normalization."""

    providers = rx.list_result_providers()
    provider = providers[0]

    # Test with string name (exercises string path)
    solutions_by_name = rx.list_solutions(result_provider=provider.name)
    assert isinstance(solutions_by_name, list)

    # Test with provider object (exercises object path)
    solutions_by_obj = rx.list_solutions(result_provider=provider)
    assert isinstance(solutions_by_obj, list)

    # Test with None (exercises default path)
    solutions_default = rx.list_solutions(result_provider=None)
    assert isinstance(solutions_default, list)
