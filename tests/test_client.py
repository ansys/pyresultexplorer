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
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import grpc
import pytest

from ansys.result_explorer.core import __version__, models
from ansys.result_explorer.core.client import Client, ResultExplorerError


@pytest.mark.parametrize("filename", ["nested/session.rxs", "session", "session.txt"])
def test_save_session_stream(tmp_path: Path, filename: str) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    client._workspace_stub = MagicMock()
    client._workspace_stub.List.return_value.workspaces = [
        models.Workspace(id="existing-workspace")
    ]
    destination = tmp_path / filename
    expected = destination if destination.suffix == ".rxs" else Path(str(destination) + ".rxs")

    def chunks() -> Iterator[models.SessionChunk]:
        yield models.SessionChunk(data=b"PK\x03\x04\xff")
        assert not expected.exists()
        yield models.SessionChunk(data=b"\x00session archive")

    client._app_stub.SaveSessionStream.return_value = chunks()
    client.save_session(str(destination))

    assert expected.read_bytes() == b"PK\x03\x04\xff\x00session archive"
    client._app_stub.SaveSessionStream.assert_called_once_with(
        models.SaveSessionRequest(
            workspace_ids=["existing-workspace"],
            include_cached_data=True,
            only_cache_visible_views=False,
            compression_level=1,
            precision=models.GraphicsPrecision.GRAPHICS_PRECISION_FULL,
        )
    )
    client._app_stub.SaveSession.assert_not_called()
    assert list(expected.parent.iterdir()) == [expected]


@pytest.mark.parametrize("include_cached_data", [True, False])
@pytest.mark.parametrize("only_cache_visible_views", [True, False])
@pytest.mark.parametrize("workspace_ids", [None, ["workspace-1", "workspace-2"]])
def test_save_session_stream_options(
    tmp_path: Path,
    include_cached_data: bool,
    only_cache_visible_views: bool,
    workspace_ids: list[str] | None,
) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    client._workspace_stub = MagicMock()
    client._workspace_stub.List.return_value.workspaces = [
        models.Workspace(id="existing-workspace")
    ]
    client._app_stub.SaveSessionStream.return_value = iter([models.SessionChunk(data=b"archive")])

    client.save_session(
        tmp_path / "session.rxs",
        workspace_ids=workspace_ids,
        include_cached_data=include_cached_data,
        only_cache_visible_views=only_cache_visible_views,
        compression_level=6,
        precision=models.GraphicsPrecision.GRAPHICS_PRECISION_LOW,
    )

    client._app_stub.SaveSessionStream.assert_called_once_with(
        models.SaveSessionRequest(
            workspace_ids=["existing-workspace"] if workspace_ids is None else workspace_ids,
            include_cached_data=include_cached_data,
            only_cache_visible_views=only_cache_visible_views,
            compression_level=6,
            precision=models.GraphicsPrecision.GRAPHICS_PRECISION_LOW,
        )
    )
    if workspace_ids is None:
        client._workspace_stub.List.assert_called_once_with(models.Empty())
    else:
        client._workspace_stub.List.assert_not_called()


def test_save_session_rejects_empty_workspace_ids(tmp_path: Path) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    client._workspace_stub = MagicMock()
    destination = tmp_path / "session.rxs"
    destination.write_bytes(b"existing session")

    with pytest.raises(ValueError, match="workspace_ids must not be empty"):
        client.save_session(destination, workspace_ids=[])

    client._app_stub.SaveSessionStream.assert_not_called()
    client._workspace_stub.List.assert_not_called()
    assert destination.read_bytes() == b"existing session"
    assert list(tmp_path.iterdir()) == [destination]


def test_save_session_stream_failure_preserves_destination(tmp_path: Path) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    client._workspace_stub = MagicMock()
    destination = tmp_path / "session.rxs"
    destination.write_bytes(b"existing session")
    failure = grpc.RpcError()
    failure.code = lambda: grpc.StatusCode.UNAVAILABLE
    failure.details = lambda: "Connection lost"

    def chunks() -> Iterator[models.SessionChunk]:
        yield models.SessionChunk(data=b"partial archive")
        raise failure

    client._app_stub.SaveSessionStream.return_value = chunks()
    with pytest.raises(ResultExplorerError):
        client.save_session(destination)

    assert destination.read_bytes() == b"existing session"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.parametrize(
    "data", [b'{"app_state": {}}', b"PK\x03\x04\xff" * 120000], ids=["json", "zip"]
)
@pytest.mark.parametrize("read_only", [None, False, True], ids=["default", "writable", "read-only"])
def test_open_session_stream(tmp_path: Path, data: bytes, read_only: bool | None) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    destination = tmp_path / "session.rxs"
    destination.write_bytes(data)

    def consume(requests: Iterator[models.OpenSessionRequest]) -> models.Empty:
        options = next(requests)
        assert options.WhichOneof("payload") == "options"
        assert options.options == models.SessionImportOptions(
            read_only=False if read_only is None else read_only
        )
        received = bytearray()
        for request in requests:
            assert request.WhichOneof("payload") == "data"
            assert len(request.data) <= 256 * 1024
            received.extend(request.data)
        assert bytes(received) == data
        return models.Empty()

    client._app_stub.OpenSessionStream.side_effect = consume
    if read_only is None:
        client.open_session(destination)
    else:
        client.open_session(destination, read_only=read_only)

    client._app_stub.OpenSessionStream.assert_called_once()
    client._app_stub.OpenSession.assert_not_called()


def test_open_session_stream_rejects_invalid_extension(tmp_path: Path) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    with pytest.raises(ValueError, match="extension"):
        client.open_session(tmp_path / "session.txt")
    client._app_stub.OpenSessionStream.assert_not_called()


def test_open_session_stream_reports_rpc_failure(tmp_path: Path) -> None:
    client = Client.__new__(Client)
    client._app_stub = MagicMock()
    destination = tmp_path / "session.rxs"
    destination.write_bytes(b"archive")
    failure = grpc.RpcError()
    failure.code = lambda: grpc.StatusCode.UNAVAILABLE
    failure.details = lambda: "Connection lost"
    client._app_stub.OpenSessionStream.side_effect = failure

    with pytest.raises(ResultExplorerError):
        client.open_session(destination)
    destination.unlink()


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
