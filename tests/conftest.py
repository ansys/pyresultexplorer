import logging
import subprocess
import sys

import pytest
from playwright.sync_api import BrowserContext, expect

from ansys.result_explorer.core.client import Client

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
def web_url(request, server_url) -> str:
    web = request.config.getoption("--web-url")

    url = f"{web}?result_provider_name=Local&result_provider_url={server_url}"
    return url


INIT_SCRIPT = """
let config = {'enableScripting':true};
window.localStorage.setItem('config', JSON.stringify(config));
"""


@pytest.fixture
def web_session(web_url: str, context: BrowserContext):
    log.debug("Starting context for web session fixture")
    context.grant_permissions(["clipboard-read", "clipboard-write"])

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
