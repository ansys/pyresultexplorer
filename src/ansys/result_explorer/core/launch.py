"""Utilities for launching Result Explorer server and web UI.

This module provides classes and functions to launch a Result Explorer instance,
including the server process and web UI. The server can be launched with various
configurations, and the web UI can be opened in either the system's default browser
or a Playwright browser instance.

Examples
--------

Launch Result Explorer with default settings and open in system browser:

    >>> from ansys.result_explorer.core import (
    ...     launch_result_explorer, ServerLaunchConfig, WebLaunchConfig
    ... )
    >>> server_config = ServerLaunchConfig(port=5100, ssl=False, auth=False)
    >>> web_config = WebLaunchConfig(browser_type='default')
    >>> instance = launch_result_explorer(server_config, web_config)
    >>> # Use the instance...
    >>> instance.stop()

Launch with Playwright in windowed mode:

    >>> server_config = ServerLaunchConfig(port=5100)
    >>> web_config = WebLaunchConfig(browser_type='playwright')
    >>> instance = launch_result_explorer(server_config, web_config)
    >>> # Access the Playwright page for automation
    >>> page = instance.web_session.playwright_page
    >>> instance.stop()

Launch with Playwright in headless mode:

    >>> server_config = ServerLaunchConfig(port=5100, num_threads=4)
    >>> web_config = WebLaunchConfig(browser_type='playwright-headless')
    >>> instance = launch_result_explorer(server_config, web_config)
    >>> instance.stop()

Use context manager for automatic cleanup:

    >>> with launch_result_explorer(server_config, web_config) as instance:
    ...     # Use the instance
    ...     url = instance.web_url
    ...     # Cleanup happens automatically

Connect to the gRPC API after launching:

    >>> from ansys.result_explorer.core import Client, launch_result_explorer
    >>> instance = launch_result_explorer(ServerLaunchConfig(), WebLaunchConfig())
    >>> # Get connection details from the instance
    >>> client = Client(
    ...     session_id="default",
    ...     host=instance.grpc_host,
    ...     grpc_port=instance.grpc_port,
    ...     insecure=True
    ... )
    >>> # Use the client...
    >>> instance.stop()

Environment Variables
---------------------
ANSYS_RESULT_EXPLORER_SERVER : str
    Path to the Result Explorer installation directory. The server executable
    will be looked up at {ANSYS_RESULT_EXPLORER_SERVER}/viz-server.exe (Windows)
    or {ANSYS_RESULT_EXPLORER_SERVER}/viz-server (Unix-like).
"""

import os
import socket
import subprocess
import time
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from .logger import log

if TYPE_CHECKING:
    from .client import Client

RX_SERVER_ENV_VAR = "ANSYS_RESULT_EXPLORER_SERVER"
DEFAULT_GRPC_PORT = 50000
DEFAULT_WEB_PORT = 5100


def _find_result_explorer() -> Path:
    """Find the Result Explorer server executable.

    Looks for the executable in the path specified by ANSYS_RESULT_EXPLORER_SERVER
    environment variable.

    Returns
    -------
    Path
        Path to the Result Explorer server executable.

    Raises
    ------
    FileNotFoundError
        If Result Explorer installation is not found.
    """
    if RX_SERVER_ENV_VAR in os.environ:
        install_path = Path(os.environ[RX_SERVER_ENV_VAR])
        if install_path.exists():
            if os.name == "nt":
                exe_path = install_path / "viz-server.exe"
            else:
                exe_path = install_path / "viz-server"
            if exe_path.exists():
                return exe_path
    raise FileNotFoundError(
        f"Result Explorer installation not found. Please set the '{RX_SERVER_ENV_VAR}' "
        "environment variable to point to the installation directory."
    )


def _find_free_port(start_port: int = 5100) -> int:
    """Find an available port starting from start_port.

    Parameters
    ----------
    start_port : int, optional
        Port number to start searching from. Default is 5100.

    Returns
    -------
    int
        An available port number.
    """
    port = start_port
    max_attempts = 100
    for _ in range(max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                sock.close()
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts.")


def _wait_for_server(
    url: str, timeout: float = 30.0, poll_interval: float = 0.2, verify_ssl: bool = False
) -> bool:
    """Wait for the server to be ready to accept connections.

    Parameters
    ----------
    url : str
        Server URL to check.
    timeout : float, optional
        Maximum time to wait in seconds. Default is 30.
    poll_interval : float, optional
        Time between connection attempts in seconds. Default is 0.5.
    verify_ssl : bool, optional
        Whether to verify SSL certificates. Default is False.

    Returns
    -------
    bool
        True if server is ready, False if timeout occurred.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(url, timeout=1, verify=verify_ssl)
            log.info(f"Server responded with status code {r.status_code}")
            return True
        except requests.RequestException:
            log.debug(f"Server not ready yet at {url}, retrying in {poll_interval} seconds...")
            time.sleep(poll_interval)
    return False


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
        Authentication token/password. Only used if SSL is enabled.
    num_threads : int, optional
        Number of DPF threads to use.
    log_level : str, optional
        Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
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
    # Add more server configuration options as needed

    def _build_args(self) -> list[str]:
        """Build command-line arguments for the server.

        Returns
        -------
        list[str]
            List of command-line arguments.
        """
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
        """Initialize the server process manager.

        Parameters
        ----------
        config : ServerLaunchConfig
            Server configuration.
        """
        self._config = config
        self._process = None
        self._port = None
        self._grpc_port = config.grpc_port

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
        protocol = "https" if self._config.ssl else "http"
        server_url = f"{protocol}://127.0.0.1:{self._port}/api/v1"
        log.info(f"Waiting for server to be ready at {server_url}...")
        if not _wait_for_server(server_url):
            self.stop()
            raise RuntimeError(f"Server did not become ready within timeout at {server_url}")
        log.info("Server is ready.")

    def stop(self) -> None:
        """Stop the Result Explorer server.

        Sends a graceful shutdown request via HTTP PUT, then terminates the process if needed.
        """
        if self._process is not None:
            log.info("Stopping Result Explorer server...")

            # Try graceful shutdown via API
            if self._port is not None:
                try:
                    protocol = "https" if self._config.ssl else "http"
                    shutdown_url = f"{protocol}://127.0.0.1:{self._port}/api/v1/shutdown"
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
        """Check if the server process is running.

        Returns
        -------
        bool
            True if the server is running, False otherwise.
        """
        if self._process is None:
            return False
        return self._process.poll() is None

    @property
    def port(self) -> int:
        """Get the web server port.

        Returns
        -------
        int
            The port number.
        """
        if self._port is None:
            raise RuntimeError("Server has not been started yet.")
        return self._port

    @property
    def grpc_port(self) -> int:
        """Get the gRPC port.

        Returns
        -------
        int
            The gRPC port number.
        """
        return self._grpc_port

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
    browser_type : str, optional
        Browser type: 'default', 'playwright', or 'playwright-headless'.
        'default' uses the system's default browser.
        'playwright' uses Playwright in windowed mode.
        'playwright-headless' uses Playwright in headless mode.
        Default is 'default'.
    """

    server_url: str | None = None
    browser_type: str = "default"

    def __post_init__(self):
        """Validate configuration."""
        valid_browsers = ["default", "playwright", "playwright-headless"]
        if self.browser_type not in valid_browsers:
            raise ValueError(
                f"browser_type must be one of {valid_browsers}, got {self.browser_type}"
            )


class ResultExplorerWebSession:
    """Manages the web UI session.

    This class handles opening and managing the web UI, either in a system browser
    or a Playwright browser instance.
    """

    def __init__(self, config: WebLaunchConfig):
        """Initialize the web session.

        Parameters
        ----------
        config : WebLaunchConfig
            Web launch configuration.

        Raises
        ------
        ValueError
            If configuration is invalid.
        """
        self._config = config
        self._playwright_browser = None
        self._playwright_context = None
        self._playwright_page = None

        if self._config.server_url is None:
            raise ValueError("server_url must be provided in WebLaunchConfig.")

    def launch(self) -> None:
        """Launch the web UI.

        Opens the web UI either in the system's default browser or a Playwright
        browser, depending on the configuration.

        Raises
        ------
        ImportError
            If Playwright is required but not installed.
        """
        if self._config.browser_type == "default":
            log.info(f"Opening web UI in default browser: {self._config.server_url}")
            webbrowser.open(self._config.server_url)
        else:
            self._launch_playwright_browser()

    def _launch_playwright_browser(self) -> None:
        """Launch a Playwright browser instance.

        Raises
        ------
        ImportError
            If Playwright is not installed.
        """
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415
        except ImportError as err:
            raise ImportError(
                "Playwright is not installed. Please install it with "
                "'pip install playwright' and run 'playwright install' "
                "to install the necessary browsers."
            ) from err

        headless = self._config.browser_type == "playwright-headless"
        log.info(f"Launching Playwright browser (headless={headless}): {self._config.server_url}")

        playwright = sync_playwright().start()
        self._playwright_browser = playwright.chromium.launch(headless=headless)
        self._playwright_context = self._playwright_browser.new_context()
        self._playwright_page = self._playwright_context.new_page()
        self._playwright_page.goto(self._config.server_url)

    def close(self) -> None:
        """Close the web session.

        Closes any Playwright browser instances. System browser windows are left open.
        """
        if self._playwright_page is not None:
            self._playwright_context.close()
            self._playwright_page = None
        if self._playwright_context is not None:
            self._playwright_context.close()
            self._playwright_context = None
        if self._playwright_browser is not None:
            self._playwright_browser.close()
            self._playwright_browser = None

    @property
    def playwright_page(self):
        """Get the Playwright page object for advanced interaction.

        Returns
        -------
        playwright.async_api.Page or None
            The Playwright page object if using Playwright, None otherwise.
        """
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
        """Initialize a Result Explorer instance.

        Parameters
        ----------
        server_config : ServerLaunchConfig, optional
            Server configuration. If None, default configuration is used.
        web_config : WebLaunchConfig, optional
            Web UI configuration. If None, default configuration is used.
        """
        self._server_config = server_config or ServerLaunchConfig()
        self._web_config = web_config
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

        protocol = "https" if self._server_config.ssl else "http"
        base_url = f"{protocol}://127.0.0.1:{self._server_process.port}"
        web_url = f"{base_url}/web"

        # Launch web UI if configured
        if self._web_config is not None:
            result_provider_name = f"Local-{self._server_process.port}"
            result_provider_url = base_url
            params = (
                f"?result_provider_name={result_provider_name}"
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
        """Get the server process manager.

        Returns
        -------
        ResultExplorerServerProcess or None
            The server process manager if the server is running, None otherwise.
        """
        return self._server_process

    @property
    def web_session(self) -> ResultExplorerWebSession | None:
        """Get the web session manager.

        Returns
        -------
        ResultExplorerWebSession or None
            The web session manager if the web UI is open, None otherwise.
        """
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
        protocol = "https" if self._server_config.ssl else "http"
        return f"{protocol}://127.0.0.1:{self._server_process.port}/web"

    @property
    def grpc_host(self) -> str:
        """Get the gRPC host.

        Returns
        -------
        str
            The gRPC host address.
        """
        return "localhost"

    @property
    def grpc_port(self) -> int:
        """Get the gRPC port.

        Returns
        -------
        int
            The gRPC port number.

        Raises
        ------
        RuntimeError
            If the server has not been launched yet.
        """
        if self._server_process is None:
            raise RuntimeError("Server has not been launched yet.")
        return self._server_process.grpc_port

    @property
    def session_id(self) -> str:
        """Get the session ID.

        Returns
        -------
        str
            The unique session ID (UUID) for this instance.
        """
        return self._session_id

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
    Launch with default settings and system browser:

    >>> server_config = ServerLaunchConfig(port=5100, ssl=False, auth=False)
    >>> web_config = WebLaunchConfig(browser_type='default')
    >>> client = launch_result_explorer(server_config, web_config)
    >>> # Use the client...
    >>> # Instance is cleaned up automatically when client is destroyed

    Launch with Playwright in headless mode:

    >>> server_config = ServerLaunchConfig(port=5100)
    >>> web_config = WebLaunchConfig(browser_type='playwright-headless')
    >>> client = launch_result_explorer(server_config, web_config)
    >>> # Use the client to interact with Result Explorer
    """
    # Import Client here to avoid circular imports
    from .client import Client as ClientImpl  # noqa: PLC0415

    instance = ResultExplorerInstance(server_config, web_config)
    instance.launch()

    # Create the Client
    client = ClientImpl(
        session_id=instance.session_id,
        host="localhost",
        grpc_port=instance.grpc_port,
        insecure=True,
        instance=instance,
    )

    # Verify the client is ready by making a test gRPC call
    max_retries = 10
    retry_delay = 0.5
    for attempt in range(max_retries):
        try:
            client.app_info()
            log.info("Client connection verified.")
            return client
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
