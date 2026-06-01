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

"""Fixtures for testing Ansys Result Explorer.

To run the tests using a headed browser, append the `--headed` flag
to the pytest command, e.g.:

    pytest -vv --headed tests

"""

import logging
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, expect
from snapshot_extensions import ToleranceImageSnapshotExtension

from ansys.result_explorer.core import (
    Client,
    ServerLaunchConfig,
    Solution,
)
from ansys.result_explorer.core.launch import ResultExplorerServerProcess, _PlaywrightManager
from ansys.result_explorer.core.models import SnapshotSettings

log = logging.getLogger(__name__)

# Suppress PIL debug output during image comparison
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)


# Track failed snapshot tests for custom reporting
_failed_snapshots = []


def pytest_addoption(parser):
    parser.addoption(
        "--server-url",
        default=None,
        help="Server url.",
    )
    parser.addoption(
        "--web-url",
        default=None,
        help="Web url.",
    )
    parser.addoption(
        "--is-docker",
        action="store_true",
        default=False,
        help="Indicates if the app is running inside a Docker container.",
    )
    parser.addoption(
        "--connection-token",
        default=None,
        help="Connection token to an existing session.",
    )
    parser.addoption(
        "--launch-native",
        action="store_true",
        default=False,
        help="Indicates if the app should be launched natively.",
    )


def pytest_runtest_logreport(report):
    """Track failed snapshot tests for cleaner reporting."""
    if report.failed and hasattr(report, "longrepr"):
        # Check if this is a snapshot assertion failure
        longrepr_str = str(report.longrepr) if report.longrepr else ""

        if "snapshot" in longrepr_str.lower() and "assert" in longrepr_str.lower():
            # Find diff files for this test
            test_dir = Path(report.fspath).parent
            diffs_dir = test_dir / "__snapshots__" / "diffs"

            if diffs_dir.exists():
                diff_files = list(diffs_dir.glob("*.diff.png"))
                if diff_files:
                    # Get the most recently modified one (created during this test)
                    recent_diff = max(diff_files, key=lambda p: p.stat().st_mtime)
                    _failed_snapshots.append(
                        {
                            "test": report.nodeid,
                            "diff": str(recent_diff),  # Store as string for compatibility
                        }
                    )


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary for failed image snapshots."""
    if _failed_snapshots:
        terminalreporter.section("Image Snapshot Failures", sep="=")
        for entry in _failed_snapshots:
            test_name = entry["test"].split("::")[-1]
            diff_path = Path(entry["diff"])
            # Ensure absolute path
            if not diff_path.is_absolute():
                diff_path = Path(config.rootdir) / diff_path
            try:
                diff_rel = diff_path.relative_to(Path(config.rootdir))
            except ValueError:
                # If relative_to fails, just use the path as-is
                diff_rel = diff_path
            # Format: test_name -> diff_path
            terminalreporter.write_line(
                f"  {test_name:<50} -> {diff_rel}",
                bold=True,
                yellow=True,
            )
        terminalreporter.write_line("")


@pytest.fixture
def snapshot(snapshot):
    return snapshot.use_extension(ToleranceImageSnapshotExtension)


@pytest.fixture(scope="session", autouse=True)
def install_browser():
    """Ensure Playwright browsers are installed for the test session."""
    log.info("Installing Playwright browsers...")
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        capture_output=True,
        text=True,
    )
    log.info(r.stdout)
    log.info(r.stderr)


@pytest.fixture(scope="session", autouse=True)
def configure_playwright_singleton(request):
    """Configure the Playwright singleton to reuse pytest-playwright's instance.

    If pytest-playwright is running (has a `playwright` fixture), we tell our
    singleton to reuse that instance instead of starting its own. This prevents
    the "using Playwright Sync API inside the asyncio loop" error.
    """
    try:
        # Try to get the playwright fixture from pytest-playwright
        playwright = request.getfixturevalue("playwright")
        manager = _PlaywrightManager()
        manager.set_external_playwright(playwright)
        log.info("Playwright singleton configured to use pytest-playwright instance")
    except Exception as e:
        log.debug(f"pytest-playwright not available or error: {e}")
        # pytest-playwright not in use, singleton will manage its own instance
        pass


@pytest.fixture(scope="session")
def rx_server():
    server_config = ServerLaunchConfig(num_threads=2)

    server_process = ResultExplorerServerProcess(server_config)
    server_process.start()

    yield server_process.url

    server_process.stop()


@pytest.fixture(scope="session")
def server_url(request):
    launch_native = request.config.getoption("--launch-native")
    if launch_native:
        return request.getfixturevalue("rx_server")

    return request.config.getoption("--server-url")


@pytest.fixture(scope="session")
def connection_token(request):
    return request.config.getoption("--connection-token")


@pytest.fixture(scope="session")
def web_url(request, server_url) -> str:
    web = request.config.getoption("--web-url")

    launch_native = request.config.getoption("--launch-native")
    if launch_native:
        server_url = request.getfixturevalue("rx_server")
        web = f"{server_url}/web"

    url = f"{web}?result_provider_name=Local&result_provider_url={server_url}"
    log.info(f"Using web URL: {url}")
    return url


@pytest.fixture(scope="session")
def is_docker(request):
    value = request.config.getoption("--is-docker")
    log.info(f"Is Docker: {value}")
    return value


INIT_SCRIPT = """
let config = {'enableScripting':true};
window.localStorage.setItem('config', JSON.stringify(config));
"""


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "permissions": ["clipboard-read", "clipboard-write"],
        "ignore_https_errors": True,
    }


@pytest.fixture
def rx(web_url: str, request) -> Client:
    connection_token = request.config.getoption("--connection-token")
    if connection_token is not None:
        log.info("Using provided connection token")
        return Client.connect_with_token(connection_token)

    context: BrowserContext = request.getfixturevalue("context")
    log.debug("Starting context for web session fixture")

    page = context.new_page()
    page.add_init_script(INIT_SCRIPT)
    page.goto(web_url)

    expect(page).to_have_title("Ansys Result Explorer")

    page.get_by_role("button", name="Scripting").click()
    page.get_by_label("Connection Token").click()

    connection_token = page.evaluate("navigator.clipboard.readText()")
    log.debug("Obtained connection token from web page")

    return Client.connect_with_token(connection_token)


@pytest.fixture(scope="session")
def data_directory(is_docker):
    if is_docker:
        return "/data"
    return os.path.abspath(os.path.join("tests", "data"))


def _get_result_path(data_directory, filename, docker: bool):
    path = Path(data_directory) / filename
    if docker:
        return path.as_posix()
    return str(path)


@pytest.fixture(scope="session")
def rst_multiple_connections(data_directory, is_docker) -> str:
    return _get_result_path(data_directory, "multiple_connections.rst", is_docker)


@pytest.fixture
def snapshot_settings() -> SnapshotSettings:
    """Provide clean snapshot settings suitable for testing.

    Returns settings with no timestamp, logo, legend, or solution name for
    reproducible, clean snapshot images.
    """
    return SnapshotSettings(
        show_time_stamp=False,
        show_logo=False,
        show_legend=False,
        show_solution_name=False,
        show_result_picker=False,
        transparent_background=False,
        background_color="#FFFFFF",
        height=300,
        width=300,
    )


@pytest.fixture
def multiple_connections_solution(rx, rst_multiple_connections) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Test Solution",
        file_path=rst_multiple_connections,
    )
    assert sol.n_elements == 246
    assert sol.n_nodes == 844

    yield sol

    rx.delete_solution(sol)


@pytest.fixture(scope="session")
def rst_cp_transient(data_directory, is_docker) -> str:
    return _get_result_path(data_directory, os.path.join("cp_trans", "file.rst"), is_docker)


@pytest.fixture
def cp_transient_solution(rx, rst_cp_transient) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Test Solution - CP Transient",
        file_path=rst_cp_transient,
    )
    assert sol.n_elements == 122
    assert sol.n_nodes == 406

    yield sol

    rx.delete_solution(sol)
