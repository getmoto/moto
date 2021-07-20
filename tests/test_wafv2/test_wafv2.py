from __future__ import unicode_literals
import json
import pytest

import sure  # noqa\
import boto3
from botocore.exceptions import ClientError
from moto import mock_wafv2
from test_helper_functions import CREATE_WEB_ACL_BODY, LIST_WEB_ACL_BODY


@mock_wafv2
def test_create_web_acl():

    conn = boto3.client("wafv2", region_name="us-east-1")
    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    web_acl = res["Summary"]
    assert web_acl.get("Name") == "John"
    assert web_acl.get("ARN").startswith("arn:aws:wafv2:us-east-1:123456789012:regional/webacl/John/")
    # Duplicate name - should raise error
    with pytest.raises(ClientError):
        conn.create_web_acl(**CREATE_WEB_ACL_BODY("John", "REGIONAL"))
    res = conn.create_web_acl(**CREATE_WEB_ACL_BODY("Carl", "CLOUDFRONT"))
    web_acl = res["Summary"]
    assert web_acl.get("ARN").startswith("arn:aws:wafv2:global:123456789012:global/webacl/Carl/")


@mock_wafv2
def test_list_web_acl():

    conn = boto3.client("wafv2", region_name="us-east-1")
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Daphne", "REGIONAL"))
    conn.create_web_acl(**CREATE_WEB_ACL_BODY("Penelope", "CLOUDFRONT"))
    res = conn.list_web_acls(**LIST_WEB_ACL_BODY("REGIONAL"))
    web_acls = res["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Daphne"

    res = conn.list_web_acls(**LIST_WEB_ACL_BODY("CLOUDFRONT"))
    web_acls = res["WebACLs"]
    assert len(web_acls) == 1
    assert web_acls[0]["Name"] == "Penelope"

test_create_web_acl()
test_list_web_acl()
