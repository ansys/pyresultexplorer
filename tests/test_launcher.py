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

"""Tests for the launcher module."""

import os
import socket
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from ansys.result_explorer.core import Client
from ansys.result_explorer.core.launch import (
    RX_DESKTOP_ENV_VAR,
    RX_SERVER_ENV_VAR,
    BrowserType,
    ResultExplorerInstance,
    ResultExplorerServerProcess,
    ResultExplorerWebSession,
    ServerLaunchConfig,
    WebLaunchConfig,
    _find_free_port,
    _find_result_explorer,
    _get_viz_server_executable,
    _install_playwright_browsers,
    _wait_for_server,
    launch_result_explorer,
)


class TestGetVizServerExecutable:
    """Tests for _get_viz_server_executable helper function."""

    def test_returns_none_for_nonexistent_path(self):
        """Should return None if base path doesn't exist."""
        nonexistent = Path("/nonexistent/path/12345")
        result = _get_viz_server_executable(nonexistent)
        assert result is None

    def test_returns_none_if_executable_not_found(self, tmp_path):
        """Should return None if viz-server executable is not in the path."""
        result = _get_viz_server_executable(tmp_path)
        assert result is None

    def test_returns_executable_path_on_windows(self, tmp_path):
        """Should return path to viz-server.exe on Windows."""
        exe_path = tmp_path / "viz-server.exe"
        exe_path.touch()

        with patch("ansys.result_explorer.core.launch.os.name", "nt"):
            result = _get_viz_server_executable(tmp_path)
            assert result == exe_path

    def test_returns_executable_path_on_unix(self, tmp_path):
        """Should return path to viz-server on Unix."""
        exe_path = tmp_path / "viz-server"
        exe_path.touch()

        with patch("ansys.result_explorer.core.launch.os.name", "posix"):
            result = _get_viz_server_executable(tmp_path)
            assert result == exe_path


class TestFindResultExplorer:
    """Tests for _find_result_explorer helper function."""

    def test_raises_file_not_found_when_no_env_vars_set(self):
        """Should raise FileNotFoundError if no environment variables are set."""
        with patch.dict(os.environ, clear=True):
            with pytest.raises(FileNotFoundError) as exc_info:
                _find_result_explorer()
            assert "ANSYS_RESULT_EXPLORER_SERVER" in str(exc_info.value)
            assert "ANSYS_RESULT_EXPLORER_DESKTOP" in str(exc_info.value)

    def test_finds_from_server_env_var(self, tmp_path):
        """Should find executable from ANSYS_RESULT_EXPLORER_SERVER."""
        # Create both Windows and Unix executables; the right one will be found
        (tmp_path / "viz-server.exe").touch()
        (tmp_path / "viz-server").touch()

        with patch.dict(os.environ, {RX_SERVER_ENV_VAR: str(tmp_path)}, clear=True):
            result = _find_result_explorer()
            # Should find the appropriate executable for this platform
            assert result is not None
            assert result.parent == tmp_path

    def test_finds_from_desktop_env_var(self, tmp_path):
        """Should find executable from ANSYS_RESULT_EXPLORER_DESKTOP."""
        # Create the expected path structure with both Windows and Unix executables
        server_dir = tmp_path / "resources" / "app" / "dist" / "viz-server"
        server_dir.mkdir(parents=True)
        (server_dir / "viz-server.exe").touch()
        (server_dir / "viz-server").touch()

        with patch.dict(os.environ, {RX_DESKTOP_ENV_VAR: str(tmp_path)}, clear=True):
            result = _find_result_explorer()
            # Should find the appropriate executable for this platform
            assert result is not None
            assert result.parent == server_dir

    def test_prefers_server_env_var_over_desktop(self, tmp_path):
        """Should prefer ANSYS_RESULT_EXPLORER_SERVER over ANSYS_RESULT_EXPLORER_DESKTOP."""
        server_dir = tmp_path / "server"
        desktop_dir = tmp_path / "desktop"
        server_dir.mkdir()
        desktop_dir.mkdir(parents=True)

        # Create both Windows and Unix executables in server dir
        (server_dir / "viz-server.exe").touch()
        (server_dir / "viz-server").touch()

        # Create both Windows and Unix executables in desktop dir
        desktop_server_dir = desktop_dir / "resources" / "app" / "dist" / "viz-server"
        desktop_server_dir.mkdir(parents=True)
        (desktop_server_dir / "viz-server.exe").touch()
        (desktop_server_dir / "viz-server").touch()

        with patch.dict(
            os.environ,
            {RX_SERVER_ENV_VAR: str(server_dir), RX_DESKTOP_ENV_VAR: str(desktop_dir)},
            clear=True,
        ):
            result = _find_result_explorer()
            # Should find the executable in the server dir (preferred over desktop)
            assert result is not None
            assert result.parent == server_dir


class TestFindFreePort:
    """Tests for _find_free_port helper function."""

    def test_returns_available_port(self):
        """Should return an available port."""
        port = _find_free_port()
        assert isinstance(port, int)
        assert port >= 5100

        # Verify the port is actually available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))

    def test_finds_alternative_port_if_default_taken(self):
        """Should find alternative port if default is taken."""
        # Find a free port first
        free_port = _find_free_port(start_port=15000)

        # Occupy that port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", free_port))
            port = _find_free_port(start_port=free_port)
            assert port != free_port

    def test_raises_runtime_error_after_max_attempts(self):
        """Should raise RuntimeError if no port found after max attempts."""
        # This is a bit tricky to test, so we'll mock the socket behavior
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.__enter__ = Mock(return_value=mock_socket)
            mock_socket.__exit__ = Mock(return_value=False)
            mock_socket.bind.side_effect = OSError("Address already in use")
            mock_socket_class.return_value = mock_socket

            with pytest.raises(RuntimeError) as exc_info:
                _find_free_port()
            assert "Could not find an available port" in str(exc_info.value)


class TestWaitForServer:
    """Tests for _wait_for_server helper function."""

    def test_returns_true_when_server_responds(self):
        """Should return True when server responds successfully."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = _wait_for_server("http://localhost:5100", timeout=1.0)
            assert result is True

    def test_returns_false_on_timeout(self):
        """Should return False if server doesn't respond within timeout."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.ConnectionError()
            with patch("time.sleep"):  # Mock sleep to avoid actual waiting
                result = _wait_for_server("http://localhost:5100", timeout=0.1, poll_interval=0.05)
                assert result is False

    def test_retries_until_server_responds(self):
        """Should retry polling until server responds."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200

            # First two calls fail, third succeeds
            mock_get.side_effect = [
                requests.ConnectionError(),
                requests.ConnectionError(),
                mock_response,
            ]

            with patch("time.sleep"):  # Mock sleep to avoid actual waiting
                result = _wait_for_server("http://localhost:5100", timeout=10.0, poll_interval=0.1)
                assert result is True

    def test_respects_verify_ssl_parameter(self):
        """Should pass verify parameter to requests.get for SSL verification."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            _wait_for_server("https://localhost:5100", verify_ssl=False, timeout=1.0)
            mock_get.assert_called()
            assert mock_get.call_args[1]["verify"] is False


class TestInstallPlaywrightBrowsers:
    """Tests for _install_playwright_browsers helper function."""

    def test_calls_playwright_install_command(self):
        """Should call playwright install command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            _install_playwright_browsers()

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "playwright" in call_args
            assert "install" in call_args
            assert "chromium" in call_args

    def test_raises_runtime_error_on_timeout(self):
        """Should raise RuntimeError if installation times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)

            with pytest.raises(RuntimeError) as exc_info:
                _install_playwright_browsers()
            assert "timed out" in str(exc_info.value).lower()

    def test_raises_runtime_error_on_non_zero_exit(self):
        """Should raise RuntimeError if subprocess returns non-zero exit code."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="Installation failed")

            with pytest.raises(RuntimeError):
                _install_playwright_browsers()


class TestServerLaunchConfig:
    """Tests for ServerLaunchConfig dataclass."""

    def test_build_args_no_ssl(self):
        """Should include --no-ssl when ssl is False and auth is False."""
        config = ServerLaunchConfig(ssl=False, auth=False)
        args = config._build_args()
        assert "--no-ssl" in args

    def test_build_args_ssl_with_auth(self):
        """Should not include --no-ssl when ssl is False and auth is True."""
        config = ServerLaunchConfig(ssl=False, auth=True)
        args = config._build_args()
        assert "--no-ssl" not in args

    def test_build_args_no_auth(self):
        """Should include --no-auth when auth is False."""
        config = ServerLaunchConfig(auth=False)
        args = config._build_args()
        assert "--no-auth" in args

    def test_build_args_with_token(self):
        """Should include token when auth is True and token is provided."""
        config = ServerLaunchConfig(auth=True, token="secret123")
        args = config._build_args()
        assert "--token" in args
        assert "secret123" in args

    def test_build_args_with_port(self):
        """Should include port in opt arguments."""
        config = ServerLaunchConfig(port=5200)
        args = config._build_args()
        assert "--opt" in args
        assert "port=5200" in args

    def test_build_args_with_num_threads(self):
        """Should include dpf_num_threads in opt arguments."""
        config = ServerLaunchConfig(num_threads=4)
        args = config._build_args()
        assert "--opt" in args
        assert "dpf_num_threads=4" in args

    def test_build_args_with_log_level(self):
        """Should include log_level in opt arguments."""
        config = ServerLaunchConfig(log_level="debug")
        args = config._build_args()
        assert "--opt" in args
        assert "log_level=debug" in args

    def test_build_args_finds_free_port_if_none_specified(self):
        """Should find a free port if port is None."""
        config = ServerLaunchConfig(port=None)
        args = config._build_args()
        # Extract port from args
        opt_index = args.index("--opt") if "--opt" in args else -1
        assert opt_index != -1
        port_arg = args[opt_index + 1]
        assert "port=" in port_arg


class TestWebLaunchConfig:
    """Tests for WebLaunchConfig dataclass."""

    def test_validates_browser_type(self):
        """Should validate browser_type on initialization."""
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            WebLaunchConfig(server_url="http://localhost:5100", browser_type="invalid")  # type: ignore
        assert "browser_type must be a BrowserType enum value" in str(exc_info.value)


class TestResultExplorerServerProcess:
    """Tests for ResultExplorerServerProcess class."""

    def test_raises_if_already_running(self):
        """Should raise RuntimeError if trying to start twice."""
        config = ServerLaunchConfig()
        process = ResultExplorerServerProcess(config)
        process._process = Mock()  # Simulate running process

        with pytest.raises(RuntimeError) as exc_info:
            with patch("ansys.result_explorer.core.launch._find_result_explorer"):
                process.start()
        assert "already running" in str(exc_info.value)

    def test_is_running_property(self):
        """Should correctly report if process is running."""
        config = ServerLaunchConfig()
        process = ResultExplorerServerProcess(config)

        assert process.is_running is False

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        process._process = mock_process
        assert process.is_running is True

        mock_process.poll.return_value = 0  # Process has exited
        assert process.is_running is False

    def test_port_property_raises_if_not_started(self):
        """Should raise RuntimeError if accessing port before start."""
        config = ServerLaunchConfig()
        process = ResultExplorerServerProcess(config)

        with pytest.raises(RuntimeError) as exc_info:
            _ = process.port
        assert "not been started" in str(exc_info.value)


class TestResultExplorerWebSession:
    """Tests for ResultExplorerWebSession class."""

    def test_initialization_requires_server_url(self):
        """Should raise ValueError if server_url is None."""
        config = WebLaunchConfig(server_url=None)
        with pytest.raises(ValueError) as exc_info:  # noqa: PT011
            ResultExplorerWebSession(config)
        assert "server_url must be provided" in str(exc_info.value)


class TestResultExplorerInstance:
    """Tests for ResultExplorerInstance high-level class."""

    def test_grpc_port_raises_if_not_launched(self):
        """Should raise RuntimeError if accessing gRPC port before launch."""
        instance = ResultExplorerInstance()
        with pytest.raises(RuntimeError) as exc_info:
            _ = instance.grpc_port
        assert "not been launched" in str(exc_info.value)

    def test_web_url_raises_if_not_launched(self):
        """Should raise RuntimeError if accessing web_url before launch."""
        instance = ResultExplorerInstance()
        with pytest.raises(RuntimeError) as exc_info:
            _ = instance.web_url
        assert "not been launched" in str(exc_info.value)

    def test_stop_method(self):
        """Should stop server and web session."""
        instance = ResultExplorerInstance()
        mock_server = Mock()
        mock_web = Mock()
        instance._server_process = mock_server
        instance._web_session = mock_web

        instance.stop()

        mock_web.close.assert_called_once()
        mock_server.stop.assert_called_once()


class TestServerLaunchIntegration:
    """Integration tests that actually launch a real server (no mocking)."""

    @pytest.fixture
    def skip_if_no_native_launch(self, request):
        """Skip test if --launch-native is not set."""
        if not request.config.getoption("--launch-native"):
            pytest.skip("Requires --launch-native flag to run real server")

    def test_server_process_lifecycle(self, skip_if_no_native_launch):
        """Test actual server startup, running status, and graceful shutdown."""
        config = ServerLaunchConfig(num_threads=2, ssl=False, auth=False)
        process = ResultExplorerServerProcess(config)

        # Server should not be running initially
        assert process.is_running is False

        # Start the server
        process.start()
        assert process.is_running is True
        assert process.port > 0
        assert process.url.startswith("http://127.0.0.1:")
        assert process.gateway_http_port > 0
        assert process.gateway_grpc_port > 0

        # Verify server responds to requests
        api_url = f"{process.url}/api/v1"
        response = requests.get(api_url, timeout=5, verify=False)
        assert response.status_code == 200
        data = response.json()
        assert "gateway_info" in data

        # Stop the server gracefully
        process.stop()
        assert process.is_running is False

        # Give process time to fully terminate
        time.sleep(0.5)

    def test_server_process_context_manager(self, skip_if_no_native_launch):
        """Test that ResultExplorerInstance works as context manager with real server."""
        config = ServerLaunchConfig(num_threads=2, ssl=False)

        with ResultExplorerInstance(server_config=config) as instance:
            instance.launch()

            assert instance.server_process is not None
            assert instance.server_process.is_running is True
            url = instance.server_process.url

            # Server should respond
            api_url = f"{url}/api/v1"
            response = requests.get(api_url, timeout=5, verify=False)
            assert response.status_code == 200

            # Save reference before context exit
            server_process = instance.server_process

        # After exiting context, server should be stopped and cleaned up
        assert server_process.is_running is False
        assert instance.server_process is None

    def test_multiple_concurrent_servers(self, skip_if_no_native_launch):
        """Test that we can launch multiple server instances with different ports."""
        config1 = ServerLaunchConfig(num_threads=1, ssl=False)
        config2 = ServerLaunchConfig(num_threads=1, ssl=False)

        process1 = ResultExplorerServerProcess(config1)
        process2 = ResultExplorerServerProcess(config2)

        try:
            process1.start()
            process2.start()

            # Verify both are running on different ports
            assert process1.is_running is True
            assert process2.is_running is True
            assert process1.port != process2.port

            # Both should respond
            response1 = requests.get(f"{process1.url}/api/v1", timeout=5, verify=False)
            response2 = requests.get(f"{process2.url}/api/v1", timeout=5, verify=False)
            assert response1.status_code == 200
            assert response2.status_code == 200
        finally:
            process1.stop()
            process2.stop()
            time.sleep(0.5)

    @pytest.mark.parametrize("auth", [False, True])
    def test_full_application_with_client(self, skip_if_no_native_launch, auth):
        """Test the full application lifecycle."""

        server_config = ServerLaunchConfig(num_threads=2, ssl=False, auth=auth)
        if auth:
            assert server_config.token is not None
            assert server_config.ssl is True
        web_config = WebLaunchConfig(browser_type=BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS)

        # Launch the full application
        client = launch_result_explorer(server_config, web_config)

        # Verify client is connected
        assert client is not None
        assert client.instance is not None
        assert "/web" in client.web_url
        assert client.web_session is not None

        # Test app info retrieval
        app_info = client.app_info
        assert app_info is not None
        assert app_info.version != ""

        # Get app settings
        settings = client.app_settings()
        assert settings is not None

        # Create a workspace
        workspace = client.create_workspace("Integration Test Workspace")
        assert workspace is not None
        assert workspace.name == "Integration Test Workspace"

        # List workspaces
        workspaces = client.list_workspaces()
        assert len(workspaces) > 0
        assert any(w.name == "Integration Test Workspace" for w in workspaces)

        # List result providers
        providers = client.list_result_providers()
        assert isinstance(providers, list)

        # Save and restore session
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".rxs", delete=False) as f:
            session_path = Path(f.name)

        try:
            client.save_session(session_path)
            assert session_path.exists()
            assert session_path.stat().st_size > 0
        finally:
            session_path.unlink()

        client.stop()

    def test_full_application_launch_twice(self, skip_if_no_native_launch):
        """Test launching the full application twice concurrently.

        This verifies that the Playwright singleton correctly handles multiple
        concurrent browser instances without conflicts.
        """
        server_config = ServerLaunchConfig(num_threads=2, ssl=False)
        web_config = WebLaunchConfig(browser_type=BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS)

        # First launch
        client1 = launch_result_explorer(server_config, web_config)

        # Second launch while first is still running
        client2 = launch_result_explorer(server_config, web_config)

        # Both should work concurrently
        app_info1 = client1.app_info
        assert app_info1 is not None
        assert app_info1.version != ""

        app_info2 = client2.app_info
        assert app_info2 is not None
        assert app_info2.version != ""

        # Create resources in each client
        workspace1 = client1.create_workspace("Workspace from Client 1")
        assert workspace1 is not None

        workspace2 = client2.create_workspace("Workspace from Client 2")
        assert workspace2 is not None

        # Verify both can list resources
        workspaces1 = client1.list_workspaces()
        assert any(w.name == "Workspace from Client 1" for w in workspaces1)

        workspaces2 = client2.list_workspaces()
        assert any(w.name == "Workspace from Client 2" for w in workspaces2)

        # Stop both clients at the end
        client1.stop()
        client2.stop()

    def test_connection_token_reconnect(self, skip_if_no_native_launch):

        server_config = ServerLaunchConfig(num_threads=2, ssl=False)
        web_config = WebLaunchConfig(browser_type=BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS)

        client1 = launch_result_explorer(server_config, web_config)

        assert client1.connection_token is not None

        client2 = Client.connect_with_token(client1.connection_token)

        assert client2.connection_token == client1.connection_token

        num_ws = len(client1.list_workspaces())
        assert num_ws > 0
        client1.create_workspace("Workspace for Reconnect Test")
        assert len(client2.list_workspaces()) == num_ws + 1

        client1.stop()
