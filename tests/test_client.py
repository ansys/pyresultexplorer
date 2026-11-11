# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
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
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_connection_token_with_path_ca_cert(tmp_path: Path) -> None:
    ca_cert_path = tmp_path / "ca.pem"
    ca_cert_path.write_text("dummy")
    with patch.object(Client, "_check_compatibility"):
        client = Client(session_id="session", ca_cert_path=ca_cert_path)

    payload = json.loads(base64.b64decode(client.connection_token))

    assert payload["ca_cert_path"] == str(ca_cert_path)


@pytest.mark.filterwarnings(
    "ignore::ansys.result_explorer.core.exceptions.UnsecureConnectionWarning"
)
@pytest.mark.parametrize(
    ("insecure", "with_ca_cert"),
    [(True, False), (True, True), (False, True), (False, False)],
    ids=["insecure", "insecure-ignores-ca-cert", "ca-cert", "system-ca"],
)
def test_connection_token_round_trip_preserves_security(
    tmp_path: Path, insecure: bool, with_ca_cert: bool
) -> None:
    ca_cert_path = tmp_path / "ca.pem"
    ca_cert_path.write_text("dummy")
    with patch.object(Client, "_check_compatibility"):
        client = Client(
            session_id="session",
            ca_cert_path=ca_cert_path if with_ca_cert else None,
            insecure=insecure,
        )

    with patch.object(Client, "__init__", return_value=None, autospec=True) as init:
        Client.connect_with_token(client.connection_token)

    assert init.call_args.kwargs["insecure"] is insecure


def test_default_result_provider(rx):
    """Test default result provider getter and setter."""
    # Verify default result provider is set
    assert rx.default_result_provider == "Local"

    # Try to set an invalid result provider
    with pytest.raises(ValueError, match="Result provider 'NonExistent' not found"):
        rx.default_result_provider = "NonExistent"
