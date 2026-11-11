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

from typing import Any
from urllib.parse import urlsplit

import pytest

from ansys.result_explorer.core.models import ConnectionToken, HpsData

CAMEL_PAYLOAD = {
    "grpcBaseUrl": "https://example.com:50000",
    "hpsData": {"grpcResourceName": "resource"},
    "sessionId": "session",
    "caCertPath": "ca.pem",
}
SNAKE_PAYLOAD = {
    "grpc_base_url": "https://example.com:50000",
    "hps_data": {"grpc_resource_name": "resource"},
    "session_id": "session",
    "ca_cert_path": "ca.pem",
}
URL = "grpcBaseUrl|grpc_base_url"
SESSION_ID = "sessionId|session_id"
HPS_DATA = "hpsData|hps_data"
RESOURCE_NAME = "grpcResourceName|grpc_resource_name"
CA_CERT_PATH = "caCertPath|ca_cert_path"
VALID = {"grpcBaseUrl": "https://example.com:50000", "sessionId": "session"}


def _url_parts(token: ConnectionToken) -> tuple[str, str | None, int | None]:
    url = urlsplit(str(token.grpc_base_url))
    return url.scheme, url.hostname, url.port


@pytest.mark.parametrize(
    "payload",
    [{"grpcResourceName": "resource"}, {"grpc_resource_name": "resource"}],
    ids=["camel", "snake"],
)
def test_hps_data_create(payload: dict[str, Any]) -> None:
    assert HpsData.create(payload).grpc_resource_name == "resource"


def test_hps_data_create_ignores_unknown_keys() -> None:
    hps_data = HpsData.create({"grpcResourceName": "resource", "unknown": 1})

    assert hps_data.grpc_resource_name == "resource"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="missing"),
        pytest.param({"grpcResourceName": None}, id="null"),
        pytest.param({"grpcResourceName": 1}, id="int"),
    ],
)
def test_hps_data_create_rejects_invalid_resource_name(payload: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=RESOURCE_NAME):
        HpsData.create(payload)


@pytest.mark.parametrize("payload", [CAMEL_PAYLOAD, SNAKE_PAYLOAD], ids=["camel", "snake"])
def test_connection_token_create_parses_all_fields(payload: dict[str, Any]) -> None:
    token = ConnectionToken.create(payload)

    assert _url_parts(token) == ("https", "example.com", 50000)
    assert token.hps_data == HpsData.create({"grpcResourceName": "resource"})
    assert token.session_id == "session"
    assert token.ca_cert_path == "ca.pem"


@pytest.mark.parametrize(
    "payload",
    [VALID, {**VALID, "hpsData": None, "caCertPath": None}],
    ids=["omitted", "null"],
)
def test_connection_token_create_optional_fields_default_to_none(
    payload: dict[str, Any],
) -> None:
    token = ConnectionToken.create(payload)

    assert token.hps_data is None
    assert token.ca_cert_path is None


def test_connection_token_create_ignores_unknown_keys() -> None:
    token = ConnectionToken.create({**VALID, "unknown": "value"})

    assert token == ConnectionToken.create(VALID)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://example.com:5000", ("http", "example.com", 5000)),
        ("https://example.com:5000", ("https", "example.com", 5000)),
        ("http://127.0.0.1:5000", ("http", "127.0.0.1", 5000)),
        ("http://[::1]:5000", ("http", "::1", 5000)),
        ("http://example.com:5000/some/path", ("http", "example.com", 5000)),
        ("http://example.com:5000/", ("http", "example.com", 5000)),
        ("HTTP://Example.COM:5000", ("http", "example.com", 5000)),
    ],
    ids=["http", "https", "ipv4", "ipv6", "with-path", "trailing-slash", "uppercase"],
)
def test_connection_token_create_parses_url(url: str, expected: tuple[str, str, int]) -> None:
    token = ConnectionToken.create({**VALID, "grpcBaseUrl": url})

    assert _url_parts(token) == expected


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        pytest.param({"sessionId": "s"}, URL, id="missing-url"),
        pytest.param(
            {"grpcBaseUrl": "https://example.com:50000"}, SESSION_ID, id="missing-session-id"
        ),
        pytest.param({**VALID, "sessionId": None}, SESSION_ID, id="null-session-id"),
        pytest.param({**VALID, "sessionId": 123}, SESSION_ID, id="int-session-id"),
        pytest.param({**VALID, "grpcBaseUrl": None}, URL, id="null-url"),
        pytest.param({**VALID, "grpcBaseUrl": 5}, URL, id="int-url"),
        pytest.param({**VALID, "grpcBaseUrl": "ftp://example.com:21"}, URL, id="ftp-scheme"),
        pytest.param({**VALID, "grpcBaseUrl": "grpc://example.com:21"}, URL, id="grpc-scheme"),
        pytest.param({**VALID, "grpcBaseUrl": "example.com:5000"}, URL, id="no-scheme"),
        pytest.param({**VALID, "grpcBaseUrl": "http://:5000"}, URL, id="no-host"),
        pytest.param({**VALID, "grpcBaseUrl": "https://example.com"}, URL, id="no-port"),
        pytest.param({**VALID, "grpcBaseUrl": "http://example.com:70000"}, URL, id="port-too-big"),
        pytest.param({**VALID, "grpcBaseUrl": "http://example.com:abc"}, URL, id="port-not-int"),
        pytest.param({**VALID, "hpsData": {}}, RESOURCE_NAME, id="hps-missing-resource-name"),
        pytest.param({**VALID, "hpsData": "resource"}, HPS_DATA, id="hps-not-a-dict"),
        pytest.param({**VALID, "caCertPath": 5}, CA_CERT_PATH, id="int-ca-cert-path"),
        # Legacy token format
        pytest.param({"host": "localhost", "grpcPort": 5000, "sessionId": "s"}, URL, id="legacy"),
    ],
)
def test_connection_token_create_rejects_invalid_payload(
    payload: dict[str, Any], field: str
) -> None:
    with pytest.raises(ValueError, match=field):
        ConnectionToken.create(payload)
