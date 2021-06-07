from __future__ import unicode_literals

import sure  # noqa

import moto.server as server
from moto import mock_wafv2
from moto.wafv2 import GLOBAL_REGION
from moto.wafv2.models import US_EAST_1_REGION

"""
Test the different server responses
"""
HEADERS = {
    "X-Amz-Target": "AWSWAF_20190729.ListWebACLs",
    "Content-Type": "application/json",
}


@mock_wafv2
def test_wafv2_list_regional():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()
    res = test_client.post("/", headers=HEADERS, json={"Scope": "REGIONAL"})
    actual_webacls = res.json["WebACLs"]
    assert len(actual_webacls) == 2
    validate_name_and_description(GLOBAL_REGION, actual_webacls)


@mock_wafv2
def test_wafv2_list_cloudfront():
    backend = server.create_backend_app("wafv2")
    test_client = backend.test_client()
    res = test_client.post("/", headers=HEADERS, json={"Scope": "CLOUDFRONT"})
    actual_webacls = res.json["WebACLs"]
    assert len(actual_webacls) == 2
    validate_name_and_description(US_EAST_1_REGION, actual_webacls)


def create_expected_name(first_or_second, region):
    return "{0}-mock-webacl-for-{1}".format(first_or_second, region)


def validate_name_and_description(region, actual_webacls):
    first_name = create_expected_name("first", region)
    second_name = create_expected_name("second", region)
    assert first_name in actual_webacls[0]["Name"]
    assert second_name in actual_webacls[1]["Name"]
    assert (
        "Mock WebACL named {0}".format(first_name) in actual_webacls[0]["Description"]
    )
    assert (
        "Mock WebACL named {0}".format(second_name) in actual_webacls[1]["Description"]
    )
