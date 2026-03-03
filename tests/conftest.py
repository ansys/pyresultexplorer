import logging
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, expect

from ansys.result_explorer.core import Client, Solution

log = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption(
        "--server-url",
        default="http://localhost:5100",
        help="Server url.",
    )
    parser.addoption(
        "--web-url",
        default="http://localhost:8000",
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


@pytest.fixture(scope="session")
def server_url(request):
    return request.config.getoption("--server-url")


@pytest.fixture(scope="session")
def connection_token(request):
    return request.config.getoption("--connection-token")


@pytest.fixture(scope="session")
def web_url(request, server_url) -> str:
    web = request.config.getoption("--web-url")

    url = f"{web}?result_provider_name=Local&result_provider_url={server_url}"
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
def web_session(web_url: str, request):
    connection_token = request.config.getoption("--connection-token")
    if connection_token is not None:
        log.info("Using provided connection token")
        return connection_token

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

    return connection_token


@pytest.fixture
def rx(web_session):
    return Client.connect_with_token(web_session)


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
def multiple_connections_solution(rx, rst_multiple_connections) -> Generator[Solution, None, None]:
    sol = rx.create_solution(
        name="Test Solution",
        result_provider_name="Local",
        file_path=rst_multiple_connections,
    )
    assert sol.n_elements == 246
    assert sol.n_nodes == 844

    yield sol

    rx.delete_solution(sol)
