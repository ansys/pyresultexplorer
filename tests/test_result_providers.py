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

import logging

import pytest

from ansys.result_explorer.core import ResultExplorerError, models

log = logging.getLogger(__name__)


@pytest.mark.skip(reason="Needs to be debugged - currently failing")
def test_result_providers(rx):
    # list result providers
    rps = rx.list_result_providers()
    assert isinstance(rps, list)

    for rp in rps:
        assert isinstance(rp, models.ResultProvider)
        assert rp.name != ""
        assert rp.url != ""
        assert rp.build_info.dpf_client_version != ""
    original_count = len(rps)

    # create a new (non-existent) result provider
    name = "Test RP"
    url = "http://mytest:1234"

    new_rp = rx.create_result_provider(name=name, url=url)
    assert new_rp.name == name
    assert new_rp.url == url
    assert not new_rp.build_info.build_date

    rps = rx.list_result_providers()
    assert len(rps) == original_count + 1

    # delete the created result provider
    rx.delete_result_provider(new_rp)

    rps = rx.list_result_providers()
    assert len(rps) == original_count

    # delete non-existent result provider should raise error
    with pytest.raises(ResultExplorerError) as exc_info:
        rx.delete_result_provider("non-existent-rp")
    assert "non-existent-rp" in str(exc_info.value)
