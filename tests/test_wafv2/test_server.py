from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_wafv2

"""
Test the different server responses
"""


@mock_wafv2
def test_wafv2_list():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()
    headers = {"X-Amz-Target": "AWSWAF_20190729.ListWebACLs"}
    res = test_client.get("/", headers=headers)
    actual_webacls = res.json["WebACLs"]
    assert len(actual_webacls) == 2
    assert "first-mock-webacl-" in actual_webacls[0]["Name"]
    assert "Mock WebACL named first-mock-webacl-" in actual_webacls[0]["Description"]
    assert "second-mock-webacl-" in actual_webacls[1]["Name"]
    assert "Mock WebACL named second-mock-webacl-" in actual_webacls[1]["Description"]
