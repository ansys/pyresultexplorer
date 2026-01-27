import logging
import uuid

from playwright.sync_api import BrowserContext, expect

from ansys.result_explorer.core.client import Client

log = logging.getLogger(__name__)


def test_session_id(web_url: str, context: BrowserContext):
    # test that we can connect with a client provided session id
    # without the need to enable scripting in the web UI settings

    session_id = str(uuid.uuid4())

    web_url_with_session_id = f"{web_url}&session_id={session_id}"

    page = context.new_page()
    page.goto(web_url_with_session_id)

    expect(page).to_have_title("Ansys Result Explorer")

    page.get_by_role("button", name="Scripting").click()
    page.get_by_label("Connection Token").click()

    connection_token = page.evaluate("navigator.clipboard.readText()")

    rx = Client.connect_with_token(connection_token)
    assert rx._session_id == session_id

    assert len(rx.list_workspaces()) > 0  # verify we can make calls


def test_invalid_session_id(web_url: str, context: BrowserContext):
    # test that we can connect with a client provided session id
    # without the need to enable scripting in the web UI settings

    session_id = "invalid-session-id"

    web_url_with_session_id = f"{web_url}&session_id={session_id}"

    page = context.new_page()
    page.goto(web_url_with_session_id)

    expect(page).to_have_title("Ansys Result Explorer")

    page.get_by_role("button", name="Scripting").click()
    page.get_by_label("Connection Token").click()

    connection_token = page.evaluate("navigator.clipboard.readText()")

    rx = Client.connect_with_token(connection_token)
    assert rx._session_id != session_id
