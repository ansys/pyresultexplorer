import logging

import pytest

from ansys.result_explorer.core import ResultExplorerError, models

log = logging.getLogger(__name__)


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

    # create a new result provider
    name = "Test RP"
    url = "http://localhost:5100"
    if rps:
        url = rps[0].url
    new_rp = rx.create_result_provider(name=name, url=url)
    assert new_rp.name == name
    assert new_rp.url == url
    assert new_rp.build_info.build_date != ""

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
