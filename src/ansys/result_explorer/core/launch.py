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

"""Utilities for launching Result Explorer server and web UI.

This module provides classes and functions to launch a Result Explorer instance,
including the server process and web UI. The server can be launched with various
configurations, and the web UI can be opened in either the system's default browser
or a Playwright browser instance.
"""

import os
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from .logger import log

if TYPE_CHECKING:
    from .client import Client

RX_SERVER_ENV_VAR = "ANSYS_RESULT_EXPLORER_SERVER"
RX_DESKTOP_ENV_VAR = "ANSYS_RESULT_EXPLORER_DESKTOP"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_GRPC_PORT = 50000
DEFAULT_WEB_PORT = 5100


class _PlaywrightManager:
    """Singleton manager for Playwright instance.

    Ensures that sync_playwright is started only once and reused across multiple
    browser sessions. This prevents conflicts when multiple sessions are created
    in the same process or in async contexts.

    Can reuse an externally-managed Playwright instance (e.g., from pytest-playwright)
    or manage its own instance.
    """

    _instance = None
    _lock = threading.Lock()
    _ref_count = 0

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._playwright = None
                    cls._instance._is_external = False
        return cls._instance

    def set_external_playwright(self, playwright):
        """Set an externally-managed Playwright instance.

        Use this when pytest-playwright or another manager is already running
        a Playwright instance. Our singleton will reuse it instead of starting
        its own.

        Parameters
        ----------
        playwright
            The Playwright instance to use.

        """
        with self._lock:
            self._playwright = playwright
            self._is_external = True
            self._ref_count = 0
            log.debug("Using externally-managed Playwright instance (e.g., from pytest-playwright)")

    def get_playwright(self):
        """Get the Playwright instance, starting it if necessary.

        Returns
        -------
        playwright.sync_api.Playwright
            The Playwright instance.

        """
        with self._lock:
            if self._playwright is None:
                from playwright.sync_api import sync_playwright  # noqa: PLC0415

                log.debug("Starting Playwright instance (singleton)")
                self._playwright = sync_playwright().start()
                self._is_external = False
                self._ref_count = 0
            self._ref_count += 1
            log.debug(f"Playwright ref count: {self._ref_count}")
            return self._playwright

    def release_playwright(self):
        """Release a reference to the Playwright instance.

        Stops the instance when the reference count reaches zero (if self-managed).
        Externally-managed instances are not stopped.
        """
        with self._lock:
            if self._playwright is not None:
                self._ref_count -= 1
                log.debug(f"Playwright ref count: {self._ref_count}")
                if self._ref_count <= 0 and not self._is_external:
                    log.debug("Stopping Playwright instance (singleton)")
                    self._playwright.stop()
                    self._playwright = None
                    self._ref_count = 0
                elif self._ref_count <= 0:
                    log.debug("Not stopping externally-managed Playwright instance")


class BrowserType(StrEnum):
    """Enumeration of supported browser types for web UI launch."""

    def __init__(self, value: str):
        """Initialize browser type enum."""

    SYSTEM_DEFAULT = "system-default"
    PLAYWRIGHT_CHROMIUM = "playwright-chromium"
    PLAYWRIGHT_CHROMIUM_HEADLESS = "playwright-chromium-headless"


def _get_viz_server_executable(base_path: Path) -> Path | None:
    """Get viz-server executable from a base path if it exists."""
    if not base_path.exists():
        return None

    exe_name = "viz-server.exe" if os.name == "nt" else "viz-server"
    exe_path = base_path / exe_name
    return exe_path if exe_path.exists() else None


def _find_result_explorer() -> Path:
    """Find the Result Explorer server executable.

    Looks for the executable in the path specified by ANSYS_RESULT_EXPLORER_SERVER
    or ANSYS_RESULT_EXPLORER_DESKTOP environment variable.

    For ANSYS_RESULT_EXPLORER_SERVER: points directly to the server installation.
    For ANSYS_RESULT_EXPLORER_DESKTOP: points to the desktop app root, server is at
    resources/app/dist/viz-server relative to that path.

    Returns
    -------
    Path
        Path to the Result Explorer server executable.

    Raises
    ------
    FileNotFoundError
        If Result Explorer installation is not found.

    """
    # Check ANSYS_RESULT_EXPLORER_SERVER first (direct path to server)
    if RX_SERVER_ENV_VAR in os.environ:
        exe_path = _get_viz_server_executable(Path(os.environ[RX_SERVER_ENV_VAR]))
        if exe_path is not None:
            return exe_path

    # Check ANSYS_RESULT_EXPLORER_DESKTOP (desktop app root)
    if RX_DESKTOP_ENV_VAR in os.environ:
        desktop_path = Path(os.environ[RX_DESKTOP_ENV_VAR])
        server_path = desktop_path / "resources" / "app" / "dist" / "viz-server"
        exe_path = _get_viz_server_executable(server_path)
        if exe_path is not None:
            return exe_path

    raise FileNotFoundError(
        f"Result Explorer installation not found. Please set either "
        f"'{RX_SERVER_ENV_VAR}' (points to server directory) or "
        f"'{RX_DESKTOP_ENV_VAR}' (points to desktop app root) environment variable."
    )


def _find_free_port(start_port: int = 5100) -> int:
    """Find an available port starting from start_port."""
    port = start_port
    max_attempts = 100
    for _ in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((DEFAULT_HOST, port))
                sock.close()
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts.")


def _wait_for_server(
    url: str, timeout: float = 30.0, poll_interval: float = 0.2, verify_ssl: bool = False
) -> bool:
    """Wait for the server to be ready to accept connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(url, timeout=1, verify=verify_ssl)
            log.debug(f"Server responded with status code {r.status_code}")
            return True
        except requests.RequestException:
            log.debug(f"Server not ready yet at {url}, retrying in {poll_interval} seconds...")
            time.sleep(poll_interval)
    return False


def _install_playwright_browsers() -> None:
    """Install Playwright browsers (chromium, chromium headless)."""
    try:
        log.info("Installing Playwright browsers (this may take a minute)...")
        kwargs = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
            "text": True,
            "timeout": 300,  # 5 minute timeout
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        result = subprocess.run(  # noqa PLW1510
            [sys.executable, "-m", "playwright", "install", "chromium"],
            **kwargs,
        )
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                [sys.executable, "-m", "playwright", "install", "chromium"],
                stderr=result.stderr,
            )
        log.info("Playwright browsers installed successfully.")
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Playwright browser installation timed out after 5 minutes.") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install Playwright browsers: {e.stderr}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error installing Playwright browsers: {e}") from e


@dataclass
class ServerLaunchConfig:
    """Configuration for Result Explorer server startup.

    Parameters
    ----------
    port : int, optional
        Web server port. If None, an available port will be automatically selected.
    grpc_port : int, optional
        gRPC server port. Default is 50000.
    ssl : bool, optional
        Whether to enable SSL. Default is False (TODO: change for production).
    auth : bool, optional
        Whether to enable authentication. Default is False (TODO: change for production).
    token : str, optional
        Authentication token/password. Only used if auth is enabled.
        If auth is True and token is None, a UUID token will be generated.
    num_threads : int, optional
        Number of DPF threads to use.
    log_level : str, optional
        Log level (profile, debug, info, warning, error).
        Default is None (server default).
    debug_api_responses : bool, optional
        Enable API response debugging.
    strict_checks : bool, optional
        Enable strict checks.

    """

    port: int | None = None
    grpc_port: int = DEFAULT_GRPC_PORT
    ssl: bool = False
    auth: bool = False
    token: str | None = None
    num_threads: int | None = None
    log_level: str | None = None

    def __post_init__(self):
        """Validate and initialize configuration after dataclass initialization."""
        # Ensure SSL is enabled if auth is enabled
        if self.auth and not self.ssl:
            self.ssl = True
            log.debug("SSL enabled automatically because auth is enabled.")

        # Generate a UUID token if auth is enabled but no token provided
        if self.auth and self.token is None:
            self.token = str(uuid.uuid4())
            log.debug("Generated authentication token.")

    def _build_args(self) -> list[str]:
        """Build command-line arguments for the server."""
        args = []

        if not self.ssl:
            args.append("--no-ssl")

        if not self.auth:
            args.append("--no-auth")
        elif self.token:
            args.extend(["--token", self.token])

        port = self.port if self.port is not None else _find_free_port()
        args.extend(["--opt", f"port={port}"])

        if self.num_threads is not None:
            args.extend(["--opt", f"dpf_num_threads={self.num_threads}"])

        if self.log_level is not None:
            args.extend(["--opt", f"log_level={self.log_level}"])

        return args


class ResultExplorerServerProcess:
    """Manages the Result Explorer server subprocess.

    This class handles starting, stopping, and monitoring the Result Explorer
    server process.
    """

    def __init__(self, config: ServerLaunchConfig):
        """Initialize the server process manager."""
        self._config = config
        self._process = None
        self._port = None
        self._grpc_port = config.grpc_port
        self._gateway_http_port = None
        self._gateway_grpc_port = None
        self._ca_cert_path = None

    def start(self) -> None:
        """Start the Result Explorer server.

        Raises
        ------
        RuntimeError
            If the server process is already running or if startup fails.
        FileNotFoundError
            If Result Explorer installation is not found.

        """
        if self._process is not None:
            raise RuntimeError("Server process is already running.")

        exe_path = _find_result_explorer()

        # Determine port early
        self._port = self._config.port or _find_free_port()

        # Temporarily set port in config for _build_args to use
        original_port = self._config.port
        self._config.port = self._port
        args = self._config._build_args()
        self._config.port = original_port

        log.info(f"Starting Result Explorer server: {exe_path}")
        log.debug(f"Server arguments: {args}")

        cmd = [str(exe_path)] + args
        log.info(f"Executing: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"Failed to start server: {e}") from e

        # Wait for server to be ready
        server_url = self.url + "/api/v1"
        log.info(f"Waiting for server to be ready at {server_url}...")
        if not _wait_for_server(server_url):
            self.stop()
            raise RuntimeError(f"Server did not become ready within timeout at {server_url}")
        log.info("Server is ready.")

        # Query /api/v1 to get gateway port information
        self._query_gateway_ports()

        # Wait for gateway HTTP API to be ready
        protocol = "https" if self._config.ssl else "http"
        gateway_url = f"{protocol}://{DEFAULT_HOST}:{self._gateway_http_port}"
        log.debug(f"Waiting for gateway to be ready at {gateway_url}...")
        if not _wait_for_server(gateway_url, timeout=30.0):
            self.stop()
            raise RuntimeError(f"Gateway did not become ready within timeout at {gateway_url}")
        log.debug("Gateway is ready.")

    def stop(self) -> None:
        """Stop the Result Explorer server.

        Sends a graceful shutdown request via HTTP PUT, then terminates the process if needed.
        """
        if self._process is not None:
            log.info("Stopping Result Explorer server...")

            # Try graceful shutdown via API
            if self._port is not None:
                try:
                    shutdown_url = self.url + "/api/v1/shutdown"
                    log.debug(f"Sending shutdown request to {shutdown_url}")
                    requests.put(shutdown_url, timeout=2, verify=False)
                    log.debug("Shutdown request sent, waiting for process to exit...")
                    try:
                        self._process.wait(timeout=5)
                        self._process = None
                        log.info("Server stopped gracefully.")
                        return
                    except subprocess.TimeoutExpired:
                        log.debug("Server did not stop gracefully via API, will terminate process.")
                except Exception as e:
                    log.debug(f"Graceful shutdown request failed: {e}, will terminate process.")

            # Fallback to forceful termination
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                log.warning("Server did not terminate gracefully, killing process...")
                self._process.kill()
                self._process.wait()
            self._process = None
            log.info("Server stopped.")

    @property
    def is_running(self) -> bool:
        """Check if the server process is running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def port(self) -> int:
        """Get the web server port."""
        if self._port is None:
            raise RuntimeError("Server has not been started yet.")
        return self._port

    @property
    def url(self) -> str:
        """Get the server URL."""
        protocol = "https" if self._config.ssl else "http"
        return f"{protocol}://{DEFAULT_HOST}:{self.port}"

    def _query_gateway_ports(self) -> None:
        """Query the /api/v1 endpoint to get gateway port information."""
        api_url = self.url + "/api/v1"
        try:
            response = requests.get(api_url, timeout=5, verify=False)
            response.raise_for_status()
            data = response.json()

            # Extract gateway info from response
            gateway_info = data.get("gateway_info", {})
            self._gateway_http_port = gateway_info.get("http_port")
            self._gateway_grpc_port = gateway_info.get("grpc_port")
            self._ca_cert_path = gateway_info.get("ca_cert_path")

            if self._gateway_http_port is None or self._gateway_grpc_port is None:
                raise RuntimeError("Missing gateway_info in server response")

            log.debug(
                f"Gateway ports from server: HTTP={self._gateway_http_port}, "
                f"gRPC={self._gateway_grpc_port}"
            )
        except Exception as e:
            self.stop()
            raise RuntimeError(f"Failed to query gateway ports from {api_url}: {e}") from e

    @property
    def grpc_port(self) -> int:
        """Get the gateway gRPC port."""
        return self._gateway_grpc_port or self._grpc_port

    @property
    def gateway_http_port(self) -> int | None:
        """Get the gateway HTTP port."""
        return self._gateway_http_port

    @property
    def gateway_grpc_port(self) -> int | None:
        """Get the gateway gRPC port."""
        return self._gateway_grpc_port

    @property
    def ca_cert_path(self) -> str | None:
        """Get the CA certificate path."""
        return self._ca_cert_path

    def __del__(self):
        """Ensure server is stopped when object is destroyed."""
        if self._process is not None and self.is_running:
            self.stop()


@dataclass
class WebLaunchConfig:
    """Configuration for Result Explorer web UI launch.

    Parameters
    ----------
    server_url : str, optional
        URL of the Result Explorer server. If None, assumes server is already running
        or will be launched separately.
    browser_type : BrowserType, optional
        Browser type to use for launching the web UI.
        - SYSTEM_DEFAULT: Use the system's default browser.
        - PLAYWRIGHT_CHROMIUM: Use Playwright with Chromium in windowed mode.
        - PLAYWRIGHT_CHROMIUM_HEADLESS: Use Playwright with Chromium in headless mode.
        Default is SYSTEM_DEFAULT.

    """

    server_url: str | None = None
    browser_type: BrowserType = BrowserType.SYSTEM_DEFAULT

    def __post_init__(self):
        """Validate configuration."""
        if not isinstance(self.browser_type, BrowserType):
            raise ValueError(
                f"browser_type must be a BrowserType enum value, got {self.browser_type}"
            )


class ResultExplorerWebSession:
    """Manages the web UI session.

    This class handles opening and managing the web UI, either in a system browser
    or a Playwright browser instance.
    """

    def __init__(self, config: WebLaunchConfig):
        """Initialize the web session."""
        self._config = config
        self._playwright_browser = None
        self._playwright_context = None
        self._playwright_page = None
        self._playwright_manager = None

        if self._config.server_url is None:
            raise ValueError("server_url must be provided in WebLaunchConfig.")

    def launch(self) -> None:
        """Launch the web UI."""
        if self._config.browser_type == BrowserType.SYSTEM_DEFAULT:
            log.info(f"Opening web UI in system default browser: {self._config.server_url}")
            webbrowser.open(self._config.server_url)
        else:
            self._launch_playwright_browser()

    def _launch_playwright_browser(self) -> None:
        """Launch a Playwright browser instance.

        Raises
        ------
        ImportError
            If Playwright is not installed.
        RuntimeError
            If browser installation fails.

        """
        try:
            from playwright.sync_api import sync_playwright  # noqa
        except ImportError as err:
            raise ImportError(
                "Playwright is not installed. Please install it with "
                "'pip install ansys-result-explorer-core[playwright]' and run "
                "'playwright install' to install the necessary browsers."
            ) from err

        headless = self._config.browser_type == BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS
        log.info(f"Launching Playwright browser (headless={headless}): {self._config.server_url}")

        # Get the singleton Playwright instance
        self._playwright_manager = _PlaywrightManager()
        playwright = self._playwright_manager.get_playwright()

        # First attempt: try launching normally
        needs_install = False
        try:
            self._playwright_browser = playwright.chromium.launch(headless=headless)
        except Exception as e:
            error_msg = str(e).lower()
            if "executable" in error_msg or "chromium" in error_msg or "not found" in error_msg:
                needs_install = True
            else:
                raise

        # Install and retry if needed
        if needs_install:
            log.info("Chromium browser not found, installing...")
            _install_playwright_browsers()
            self._playwright_browser = playwright.chromium.launch(headless=headless)
            log.info("Browser launched successfully after installation.")

        self._playwright_context = self._playwright_browser.new_context(
            # Ignore HTTPS errors for self-signed certificates (e.g., when SSL is enabled for auth)
            ignore_https_errors=True
        )
        self._playwright_page = self._playwright_context.new_page()
        self._playwright_page.goto(self._config.server_url)

    def close(self) -> None:
        """Close the web session."""
        if self._playwright_page is not None:
            self._playwright_page.close()
            self._playwright_page = None
        if self._playwright_context is not None:
            self._playwright_context.close()
            self._playwright_context = None
        if self._playwright_browser is not None:
            self._playwright_browser.close()
            self._playwright_browser = None
        if self._playwright_manager is not None:
            self._playwright_manager.release_playwright()
            self._playwright_manager = None

    @property
    def playwright_page(self):
        """Get the Playwright page object for advanced interaction."""
        return self._playwright_page

    def __del__(self):
        """Ensure web session is closed when object is destroyed."""
        self.close()


class ResultExplorerInstance:
    """High-level interface for managing a Result Explorer instance.

    This class manages both the server process and web UI, providing a convenient
    way to launch a complete Result Explorer instance with a single call.
    """

    def __init__(
        self,
        server_config: ServerLaunchConfig | None = None,
        web_config: WebLaunchConfig | None = None,
    ):
        """Initialize a Result Explorer instance."""
        self._server_config = server_config or ServerLaunchConfig()
        self._web_config = web_config or WebLaunchConfig()
        self._server_process: ResultExplorerServerProcess | None = None
        self._web_session: ResultExplorerWebSession | None = None
        self._session_id = str(uuid.uuid4())

    def launch(self) -> str:
        """Launch the Result Explorer instance.

        Starts the server process and opens the web UI.

        Returns
        -------
        str
            The URL of the web UI.

        Raises
        ------
        RuntimeError
            If the server fails to start.

        """
        # Start server
        self._server_process = ResultExplorerServerProcess(self._server_config)
        self._server_process.start()

        base_url = self._server_process.url
        web_url = f"{base_url}/web"

        # Launch web UI if configured
        if self._web_config is not None:
            result_provider_url = base_url
            params = (
                f"?result_provider_name={self.result_provider_name}"
                f"&result_provider_url={result_provider_url}"
                f"&session_id={self._session_id}"
            )
            web_url_with_params = f"{web_url}{params}"
            self._web_config.server_url = web_url_with_params
            self._web_session = ResultExplorerWebSession(self._web_config)
            self._web_session.launch()

        return web_url

    @property
    def server_process(self) -> ResultExplorerServerProcess | None:
        """Get the server process manager."""
        return self._server_process

    @property
    def web_session(self) -> ResultExplorerWebSession | None:
        """Get the web session manager."""
        return self._web_session

    @property
    def web_url(self) -> str:
        """Get the web UI URL (without query parameters).

        Returns
        -------
        str
            The URL of the web UI.

        Raises
        ------
        RuntimeError
            If the server has not been launched yet.

        """
        if self._server_process is None:
            raise RuntimeError("Server has not been launched yet.")
        return self._server_process.url + "/web"

    @property
    def grpc_port(self) -> int:
        """Get the gRPC port."""
        if self._server_process is None:
            raise RuntimeError("Server has not been launched yet.")
        return self._server_process.grpc_port

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def result_provider_name(self) -> str:
        """Get the result provider name."""
        if self._server_process is None:
            raise RuntimeError("Server has not been launched yet.")
        return f"Local-{self._server_process.port}"

    def stop(self) -> None:
        """Stop the Result Explorer instance.

        Closes the web session and stops the server process.
        """
        if self._web_session is not None:
            self._web_session.close()
            self._web_session = None
        if self._server_process is not None:
            self._server_process.stop()
            self._server_process = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def __del__(self):
        """Ensure instance is stopped when object is destroyed."""
        try:
            self.stop()
        except Exception:
            pass


def launch_result_explorer(
    server_config: ServerLaunchConfig | None = None,
    web_config: WebLaunchConfig | None = None,
) -> "Client":
    """Launch a Result Explorer instance and return a configured Client.

    Convenience function to create, launch a Result Explorer instance, and return
    a Client configured with that instance's connection details. The instance
    lifecycle is tied to the client; when the client is destroyed, the instance
    will be stopped.

    Parameters
    ----------
    server_config : ServerLaunchConfig, optional
        Server configuration. If None, default configuration is used.
    web_config : WebLaunchConfig, optional
        Web UI configuration. If None, no web UI is launched.

    Returns
    -------
    Client
        A Client instance configured to connect to the launched server. The
        instance lifecycle is tied to this client.

    Examples
    --------
    Launch with default settings and system default browser:

    >>> server_config = ServerLaunchConfig(port=5100, ssl=False, auth=False)
    >>> web_config = WebLaunchConfig(browser_type=BrowserType.SYSTEM_DEFAULT)
    >>> client = launch_result_explorer(server_config, web_config)
    >>> # Use the client...
    >>> # Instance is cleaned up automatically when client is destroyed

    Launch with Playwright in headless mode:

    >>> server_config = ServerLaunchConfig(port=5100)
    >>> web_config = WebLaunchConfig(browser_type=BrowserType.PLAYWRIGHT_CHROMIUM_HEADLESS)
    >>> client = launch_result_explorer(server_config, web_config)
    >>> # Use the client to interact with Result Explorer

    """
    # Import Client here to avoid circular imports
    from .client import Client as ClientImpl  # noqa: PLC0415

    instance = ResultExplorerInstance(server_config, web_config)
    instance.launch()

    # Give the web UI time to connect to the gateway via WebSocket if applicable
    if instance.web_session is not None:
        log.debug("Waiting for web UI to establish gateway connection...")
        time.sleep(2.0)

    # Create the Client
    ca_cert_path = instance._server_process.ca_cert_path
    client = ClientImpl(
        session_id=instance.session_id,
        host="localhost",
        grpc_port=instance.grpc_port,
        ca_cert_path=ca_cert_path,
        insecure=ca_cert_path is None,
        instance=instance,
    )

    client.default_result_provider = instance.result_provider_name

    # Verify the client is ready by making a test gRPC call
    max_retries = 15
    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
            client.app_info()
            log.info("Client connection verified.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                msg = (
                    f"Client not ready yet (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {retry_delay}s..."
                )
                log.debug(msg)
                time.sleep(retry_delay)
            else:
                log.error(f"Client failed to connect after {max_retries} attempts: {e}")
                client.stop()
                raise RuntimeError(f"Client failed to establish connection: {e}") from e

    # Authenticate the result provider if auth is enabled
    if instance._server_config.auth and instance._server_config.token:
        log.debug("Authenticating result provider...")
        try:
            client.authenticate_result_provider(
                instance._server_config.token, result_provider=instance.result_provider_name
            )
            log.debug("Result provider authenticated successfully.")
        except Exception as e:
            log.error(f"Failed to authenticate result provider: {e}")
            client.stop()
            raise

    return client
